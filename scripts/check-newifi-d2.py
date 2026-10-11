#!/usr/bin/env python3
"""Fail closed on a wrong profile, missing dependencies, cores or oversized image."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


DEVICE = "d-team_newifi-d2"
BOARD = "d-team,newifi-d2"
PROFILE = f"TARGET_ramips_mt7621_DEVICE_{DEVICE}"
LIMIT = 32448 * 1024
REQUIRED = {
    "apk-mbedtls", "base-files", "busybox", "dropbear", "netifd", "uci", "ubus", "logd",
    "mtd", "fstools", "firewall4", "nftables-json", "dnsmasq-full", "ppp",
    "ppp-mod-pppoe", "odhcp6c", "odhcpd-ipv6only", "wpad-basic-mbedtls",
    "wifi-scripts", "kmod-mt7603", "kmod-mt76x2", "kmod-usb3",
    "kmod-usb-ledtrig-usbport", "luci-light", "luci-base", "luci-compat",
    "luci-lib-ipkg", "luci-app-firewall", "luci-i18n-base-zh-cn",
    "luci-i18n-firewall-zh-cn", "uhttpd", "uhttpd-mod-ubus", "rpcd",
    "luci-app-openclash", "bash", "curl", "ca-bundle", "ip-full", "ruby",
    "ruby-yaml", "kmod-tun", "unzip", "kmod-inet-diag", "kmod-nft-tproxy",
    "kmod-nft-socket",
}
CONFLICTING = {"dnsmasq", "dnsmasq-dhcpv6", "firewall", "nftables-nojson"}
DISABLED = {
    "TARGET_MULTI_PROFILE", "TARGET_ALL_PROFILES", "TARGET_PER_DEVICE_ROOTFS",
    "ALL", "ALL_NONSHARED", "ALL_KMODS", "BUILDBOT", "IB", "IB_STANDALONE",
    "SDK", "MAKE_TOOLCHAIN", "TARGET_ROOTFS_INITRAMFS", "TARGET_ROOTFS_CPIOGZ",
    "TARGET_ROOTFS_TARGZ", "TARGET_ROOTFS_EXT4FS", "TARGET_ROOTFS_JFFS2",
    "TARGET_ROOTFS_JFFS2_NAND", "TARGET_ROOTFS_UBIFS", "TARGET_ROOTFS_EROFS",
    "PACKAGE_dnsmasq_full_ipset",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def command(*args):
    return subprocess.check_output(args, text=True).strip()


def read_config(path):
    return dict(re.findall(r"^CONFIG_([^=\s]+)=(.*)$", path.read_text(), re.M))


def unwanted(name):
    if name == "luci-app-openclash":
        return False
    return bool(re.search(
        r"mihomo|clash|sing-box|xray|v2ray|(^|-)docker|^containerd$|^runc$|"
        r"^luci-app-(passwall|ssr|shadowsocks|homeproxy|fchomo|nikki|nekobox|vssr)",
        name, re.I,
    ))


def package_records(path):
    records = {}
    current = None
    for line in path.read_text().splitlines():
        if line.startswith("Package: "):
            current = {}
            records[line.removeprefix("Package: ")] = current
        elif current is not None and re.match(r"^(Version|Depends|Provides|Conflicts|Build-Depends):", line):
            field, value = line.split(":", 1)
            current[field] = value.strip()
        elif line == "@@":
            current = None
    return records


def enabled(expression, config):
    """Evaluate the boolean guards emitted by OpenWrt package metadata."""
    tokens = re.findall(r"&&|\|\||!|\(|\)|[A-Za-z0-9_.+-]+", expression)
    require("".join(tokens) == expression, f"Unsupported dependency guard: {expression}")
    index = 0

    def atom():
        nonlocal index
        require(index < len(tokens), f"Incomplete dependency guard: {expression}")
        token = tokens[index]
        index += 1
        if token == "!":
            return not atom()
        if token == "(":
            value = either()
            require(index < len(tokens) and tokens[index] == ")", f"Unclosed guard: {expression}")
            index += 1
            return value
        return config.get(token) in ("y", "m")

    def both():
        nonlocal index
        value = atom()
        while index < len(tokens) and tokens[index] == "&&":
            index += 1
            right = atom()
            value = value and right
        return value

    def either():
        nonlocal index
        value = both()
        while index < len(tokens) and tokens[index] == "||":
            index += 1
            right = both()
            value = value or right
        return value

    result = either()
    require(index == len(tokens), f"Invalid dependency guard: {expression}")
    return result


def dependency_names(value, config):
    for token in value.split():
        token = token.lstrip("+")
        if token.startswith("@"):
            continue  # Kconfig checks feature constraints, including architecture.
        if ":" in token:
            guard, token = token.split(":", 1)
            if not enabled(guard, config):
                continue
        match = re.match(r"^[A-Za-z0-9_][A-Za-z0-9_.+-]*", token)
        if match:
            yield match[0]


def check_packages(names):
    require(REQUIRED <= names, f"Missing required packages: {sorted(REQUIRED - names)}")
    require(not (CONFLICTING & names), f"Conflicting packages: {sorted(CONFLICTING & names)}")
    forbidden = sorted(name for name in names if unwanted(name))
    require(not forbidden, f"Unrelated applications or proxy cores: {forbidden}")


def check_config(tree):
    config = read_config(tree / ".config")
    for symbol in {"TARGET_ramips", "TARGET_ramips_mt7621", PROFILE,
                   "TARGET_ROOTFS_SQUASHFS", "IPV6", "LUCI_LANG_zh_Hans",
                   "PACKAGE_dnsmasq_full_dhcp", "PACKAGE_dnsmasq_full_dhcpv6",
                   "PACKAGE_dnsmasq_full_dnssec", "PACKAGE_dnsmasq_full_nftset",
                   "DOWNLOAD_CHECK_CERTIFICATE", "SIGNED_PACKAGES", "SIGNATURE_CHECK", "USE_APK"}:
        require(config.get(symbol) == "y", f"Required CONFIG_{symbol}=y is absent")
    for symbol in DISABLED:
        require(config.get(symbol) not in ("y", "m"), f"CONFIG_{symbol} must be disabled")
    profiles = sorted(key for key, value in config.items()
                      if "_DEVICE_" in key and key.startswith("TARGET_")
                      and value in ("y", "m"))
    require(profiles == [PROFILE], f"Expected exactly one target profile, got: {profiles}")
    require(config.get("TARGET_PROFILE") == f'"DEVICE_{DEVICE}"', "Wrong TARGET_PROFILE")
    require(config.get("TARGET_ARCH_PACKAGES") == '"mipsel_24kc"', "Wrong target architecture")

    records = package_records(tree / "tmp/.packageinfo")
    names = {name for name in records if config.get(f"PACKAGE_{name}") == "y"}
    build_names = {key.removeprefix("PACKAGE_") for key, value in config.items()
                   if key.startswith("PACKAGE_") and value in ("y", "m")}
    check_packages(names)
    require(not any(unwanted(name) for name in build_names), "A proxy core/unrelated application would be built")
    modules = {name for name in records if config.get(f"PACKAGE_{name}") == "m"}
    require(not modules, f"Unnecessary separately-built packages: {sorted(modules)}")
    providers = set(names)
    for name in names:
        providers.update(token.lstrip("@") for token in records[name].get("Provides", "").split())
    checked = 0
    for name in sorted(names):
        for dependency in dependency_names(records[name].get("Depends", ""), config):
            require(dependency in providers, f"{name} is missing runtime dependency {dependency}")
            checked += 1
        conflicts = set(dependency_names(records[name].get("Conflicts", ""), config))
        require(not (conflicts & names), f"{name} conflicts with {sorted(conflicts & names)}")

    device_mk = (tree / "target/linux/ramips/image/mt7621.mk").read_text()
    definition = re.search(r"^define Device/d-team_newifi-d2\n(.*?)^endef", device_mk, re.M | re.S)
    require(definition is not None, "Device definition missing")
    require(re.search(r"IMAGE_SIZE\s*:=\s*32448k\b", definition[1]), "Device image limit changed")
    for driver in ("kmod-mt7603", "kmod-mt76x2", "kmod-usb3"):
        require(driver in definition[1], f"Device definition lost {driver}")
    dts = (tree / "target/linux/ramips/dts/mt7621_d-team_newifi-d2.dts").read_text()
    require("reg = <0x50000 0x1fb0000>;" in dts, "Firmware partition layout changed")
    for label in ("lan1", "lan2", "lan3", "lan4", "wan"):
        require(f'label = "{label}";' in dts, f"Device tree lost port {label}")
    require(not command("git", "-C", str(tree), "diff", "--", "target/linux/ramips", "include"),
            "Target/partition/image-check/kernel compatibility definitions were modified")
    return {
        "status": "passed", "target": "ramips/mt7621", "selected_profiles": profiles,
        "architecture": "mipsel_24kc", "image_limit_bytes": LIMIT,
        "firewall": "firewall4/nftables", "dns": "dnsmasq-full (DHCP, DHCPv6, DNSSEC, nftset)",
        "dependency_edges_checked": checked, "openclash_dependencies": records["luci-app-openclash"],
        "selected_packages": sorted(names), "required_packages": sorted(REQUIRED),
        "core_packages": [], "config_sha256": digest(tree / ".config"),
        "hardware_validation": "not performed",
    }


def provenance(repo, build):
    pins = dict(line.split("=", 1) for line in
                (repo / "devices/newifi-d2-openclash/sources.env").read_text().splitlines()
                if line and not line.startswith("#"))
    result = {"kwrt": {"commit": command("git", "-C", str(repo), "rev-parse", "HEAD"),
                       "origin": command("git", "-C", str(repo), "remote", "get-url", "origin"),
                       "uncommitted_changes": bool(command("git", "-C", str(repo), "status", "--porcelain"))}}
    for name, location, prefix in (
        ("openwrt", build / "openwrt", "OPENWRT"),
        ("packages", build / "openwrt/feeds/packages", "PACKAGES"),
        ("luci", build / "openwrt/feeds/luci", "LUCI"),
        ("openclash", build / "openclash-feed", "OPENCLASH"),
    ):
        commit = command("git", "-C", str(location), "rev-parse", "HEAD")
        require(commit == pins[f"{prefix}_COMMIT"], f"{name} differs from pinned commit")
        result[name] = {"url": pins[f"{prefix}_URL"], "commit": commit}
        if name != "openclash":
            require(not command("git", "-C", str(location), "status", "--porcelain", "--untracked-files=no"),
                    f"Unexpected tracked source edits in {name}")
    package = build / "openclash-feed/luci-app-openclash"
    makefile = (package / "Makefile").read_text()
    for field in ("VERSION", "RELEASE"):
        require(re.search(rf"^PKG_{field}:={re.escape(pins[f'OPENCLASH_{field}'])}$", makefile, re.M),
                f"Unexpected OpenClash {field.lower()}")
    require("PKG_BUILD_DEPENDS:=luci-base/host" in makefile, "Missing po2lmo host dependency")
    recipes = "\n".join(re.findall(
        r"^define (?:Build/(?:Prepare|Configure|Compile)|Package/[^\n ]+/install)\n(.*?)^endef",
        makefile, re.M | re.S))
    require(not re.search(r"^PKG_SOURCE[^\n]*=|^define Download/", makefile, re.M) and
            not re.search(r"\b(wget|curl|mihomo)\b", recipes, re.I),
            "Plugin build would fetch a source/core payload")
    require(command("git", "-C", str(build / "openclash-feed"), "diff", "--numstat") ==
            "1\t0\tluci-app-openclash/Makefile", "Unexpected OpenClash source edits")
    # Inspect only objects already present locally; do not fetch missing feed blobs.
    stored_blobs = {line.split()[0] for line in command(
        "git", "-C", str(build / "openclash-feed"), "cat-file", "--batch-all-objects",
        "--batch-check=%(objectname) %(objecttype)").splitlines() if line.endswith(" blob")}
    blob_paths = {}
    plugin_blobs = set()
    for entry in command("git", "-C", str(build / "openclash-feed"), "ls-tree", "-r", "HEAD").splitlines():
        details, path = entry.split("\t", 1)
        oid = details.split()[2]
        blob_paths.setdefault(oid, []).append(path)
        if path.startswith("luci-app-openclash/"):
            plugin_blobs.add(oid)
    # Identical files in other packages can share an object ID with this plugin.
    fetched_outside_plugin = [path for oid in stored_blobs - plugin_blobs for path in blob_paths.get(oid, [])]
    require(not fetched_outside_plugin, f"Unnecessary feed blobs fetched: {fetched_outside_plugin}")
    root = package / "root"
    check_core_files(root)
    config = (root / "etc/config/openclash").read_text()
    require("option enable '0'" in config and "option small_flash_memory '0'" in config,
            "Plugin defaults would enable the service or alter the requested storage mode")
    require(not list((root / "etc/openclash/config").glob("*")), "Preinstalled proxy configuration")
    result["openclash"].update({
        "version": f"{pins['OPENCLASH_VERSION']}-{pins['OPENCLASH_RELEASE']}",
        "apk_version": package_records(build / "openwrt/tmp/.packageinfo")["luci-app-openclash"]["Version"],
        "path": "luci-app-openclash", "core_included": False,
        "feed_blobs_fetched_outside_plugin": fetched_outside_plugin,
        "local_patch_sha256": digest(repo / "devices/newifi-d2-openclash/patches/openclash-host-build.patch"),
    })
    result["workflow"] = {"run_id": os.getenv("GITHUB_RUN_ID"), "ref": os.getenv("GITHUB_REF")}
    return result


def check_core_files(root):
    core_names = {"mihomo", "clash", "clash_meta", "clash_tun"}
    for path in root.rglob("*"):
        require(path.name not in core_names, f"Preinstalled core path: {path}")
        if path.is_file() and not path.is_symlink():
            with path.open("rb") as stream:
                magic = stream.read(4)
                if magic == b"\x7fELF":
                    payload = magic + stream.read()
                    require(b"mihomo" not in payload.lower(), f"Mihomo ELF payload: {path}")
            relative = path.relative_to(root)
            require(not str(relative).startswith(("etc/openclash/core/", "tmp/etc/openclash/core/")),
                    f"Bundled file in core directory: {path}")


def check_artifact(tree):
    check_config(tree)
    target = tree / "bin/targets/ramips/mt7621"
    images = list(tree.glob("bin/targets/**/*.bin"))
    require(len(images) == 1 and images[0].parent == target and
            images[0].name.endswith(f"{DEVICE}-squashfs-sysupgrade.bin"),
            f"Expected exactly one Newifi D2 sysupgrade image, got {images}")
    image = images[0]
    size = image.stat().st_size
    require(0 < size <= LIMIT, f"Final image exceeds {LIMIT} bytes: {size}")
    profiles = json.loads((target / "profiles.json").read_text())
    require(profiles["target"] == "ramips/mt7621", "Wrong profiles.json target")
    require(set(profiles["profiles"]) == {DEVICE}, "Other devices in profiles.json")
    profile = profiles["profiles"][DEVICE]
    require(BOARD in profile["supported_devices"], "Wrong supported device")
    require(profile["file_size_limits"]["image"] == LIMIT, "Image limit changed in metadata")
    require(len(profile["images"]) == 1, "Unexpected additional device images")
    entry = profile["images"][0]
    require(entry["name"] == image.name and entry["type"] == "sysupgrade" and
            entry["filesystem"] == "squashfs", "Wrong firmware type/filesystem")
    sha256 = digest(image)
    require(entry["sha256"] == sha256 and entry["size"] == size, "Image checksum/size metadata mismatch")
    metadata_path = target / "newifi-d2-fwtool.json"
    subprocess.run([str(tree / "staging_dir/host/bin/fwtool"), "-i", str(metadata_path), str(image)], check=True)
    metadata = json.loads(metadata_path.read_text())
    require(BOARD in metadata.get("new_supported_devices", metadata.get("supported_devices", [])),
            "Firmware's embedded device metadata does not match Newifi D2")
    require(metadata["version"]["target"] == "ramips/mt7621", "Wrong embedded firmware target")
    manifests = list(target.glob("*.manifest"))
    require(len(manifests) == 1, f"Expected one final package manifest, got {manifests}")
    versions = dict(line.split(" - ", 1) for line in manifests[0].read_text().splitlines() if line)
    names = set(versions)
    check_packages(names)
    expected_version = package_records(tree / "tmp/.packageinfo")["luci-app-openclash"]["Version"]
    require(versions["luci-app-openclash"] == expected_version, "Wrong OpenClash version in final manifest")
    roots = list(tree.glob("staging_dir/target-*/root-ramips"))
    require(len(roots) == 1, f"Expected one assembled rootfs, got {roots}")
    root = roots[0]
    check_core_files(root)
    installed_db = root / "lib/apk/db/installed"
    require(installed_db.is_file(), "Missing final APK package database")
    installed = {}
    for paragraph in installed_db.read_text().split("\n\n"):
        fields = dict(line.split(":", 1) for line in paragraph.splitlines() if ":" in line)
        if "P" in fields:
            installed[fields["P"]] = fields["V"]
    require(versions == installed, "Final manifest and assembled rootfs package database versions differ")
    require("option enable '0'" in (root / "etc/config/openclash").read_text(), "Proxy enabled by default")
    require(not list((root / "etc/openclash/config").glob("*")), "Preinstalled proxy configuration")
    startup = (root / "etc/uci-defaults/zz-newifi-d2-openclash").read_text()
    require("/etc/init.d/openclash disable" in startup and "set openclash.config.enable='0'" in startup,
            "Missing default-disabled policy")
    require(not re.search(r"\b(wget|curl)\b|openclash_core\.sh", startup), "Automatic first-boot core download")
    return {
        "status": "passed", "device": DEVICE, "image": image.name, "sha256": sha256,
        "image_size_bytes": size, "image_limit_bytes": LIMIT, "flash_capacity_bytes": 32 * 1024 * 1024,
        "image_headroom_bytes": LIMIT - size, "writable_overlay_estimate_bytes": None,
        "overlay_note": "Image headroom is not measured writable JFFS2 space; eraseblock alignment, filesystem overhead and first-boot writes require measurement on the router.",
        "embedded_metadata": metadata, "package_count": len(names),
        "openclash_version": versions["luci-app-openclash"], "core_packages": [],
        "core_files": [], "default_service_enabled": False, "hardware_validation": "not performed",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("config", "artifact", "provenance"))
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    output = args.paths[-1]
    try:
        if args.mode == "provenance":
            require(len(args.paths) == 3, "provenance requires REPO BUILD_ROOT OUTPUT")
            result = provenance(*args.paths[:2])
        else:
            require(len(args.paths) == 2, "config/artifact requires OPENWRT_DIR OUTPUT")
            checker = check_config if args.mode == "config" else check_artifact
            result = checker(args.paths[0])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(f"{args.mode}: passed; report: {output}")
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False, indent=2) + "\n")
        parser.exit(1, f"{args.mode}: FAILED: {error}\n")


if __name__ == "__main__":
    main()
