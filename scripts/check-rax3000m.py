#!/usr/bin/env python3
"""Validate this candidate without claiming compatibility with an unknown router."""

import argparse
import gzip
import hashlib
import io
import json
import lzma
import os
from pathlib import Path
import re
import struct
import subprocess
import tarfile
import zlib


DEVICE = "cmcc_rax3000m-emmc"
BOARD = "cmcc,rax3000m-emmc"
UNIFIED_BOARD = "cmcc,rax3000m"
PROFILE = f"TARGET_mediatek_filogic_DEVICE_{DEVICE}"
ARCH = "aarch64_cortex-a53"
ROOT_PARTSIZE = 448
BUILD_LIMIT = None  # The existing Kwrt profile specifies no fixed IMAGE_SIZE.
PROFILE_DIR = "devices/rax3000m-emmc-openclash"
DEFAULTS = "etc/uci-defaults/zz-rax3000m-openclash"
REQUIRED = {
    "apk-mbedtls", "base-files", "busybox", "dropbear", "netifd", "uci", "ubus", "logd",
    "fstools", "block-mount", "uboot-envtools", "e2fsprogs", "f2fsck", "mkf2fs", "losetup", "kmod-mmc", "kmod-fs-f2fs",
    "firewall4", "nftables-json", "dnsmasq-full", "ppp", "ppp-mod-pppoe",
    "odhcp6c", "odhcpd-ipv6only", "wpad-basic-mbedtls", "wifi-scripts",
    "kmod-mt7915e", "kmod-mt7981-firmware", "mt7981-wo-firmware", "kmod-usb3",
    "kmod-usb-storage", "kmod-fs-vfat",
    "luci-light", "luci-ssl", "luci-base", "luci-compat", "luci-lib-ipkg",
    "luci-app-firewall", "luci-app-package-manager", "luci-i18n-base-zh-cn",
    "luci-i18n-firewall-zh-cn", "luci-i18n-package-manager-zh-cn",
    "uhttpd", "uhttpd-mod-ubus", "rpcd", "px5g-mbedtls", "ca-certificates",
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
    "PACKAGE_dnsmasq_full_ipset", "PACKAGE_blockd", "FEED_openclash",
}
BUILTIN_DRIVERS = {
    "MMC", "MMC_BLOCK", "MMC_MTK", "EXT4_FS", "F2FS_FS", "BLK_DEV_LOOP",
    "NET_DSA", "NET_DSA_MT7530", "NET_DSA_AN8855", "MEDIATEK_WATCHDOG",
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


def pins(repo):
    return dict(line.split("=", 1) for line in (repo / PROFILE_DIR / "sources.env").read_text().splitlines()
                if line and not line.startswith("#"))


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
            continue
        if ":" in token:
            guard, token = token.split(":", 1)
            if not enabled(guard, config):
                continue
        match = re.match(r"^[A-Za-z0-9_][A-Za-z0-9_.+-]*", token)
        if match:
            yield match[0]


def unwanted(name):
    if name in {"luci-app-openclash", "luci-app-firewall", "luci-app-package-manager"}:
        return False
    return name.startswith("luci-app-") or bool(re.search(
        r"mihomo|clash|sing-box|xray|v2ray|docker|^containerd$|^runc$|nlbwmon|"
        r"^ttyd$|^btop$|turboacc|smartdns|mosdns|adguard", name, re.I))


def check_packages(names):
    require(REQUIRED <= names, f"Missing base services, drivers or dependencies: {sorted(REQUIRED - names)}")
    require(not (CONFLICTING & names), f"Conflicting packages: {sorted(CONFLICTING & names)}")
    forbidden = sorted(name for name in names if unwanted(name))
    require(not forbidden, f"Excluded applications or proxy cores: {forbidden}")


def check_config(tree):
    config = read_config(tree / ".config")
    for symbol in {"TARGET_mediatek", "TARGET_mediatek_filogic", PROFILE,
                   "TARGET_ROOTFS_SQUASHFS", "IPV6", "LUCI_LANG_zh_Hans",
                   "PACKAGE_dnsmasq_full_dhcp", "PACKAGE_dnsmasq_full_dhcpv6",
                   "PACKAGE_dnsmasq_full_dnssec", "PACKAGE_dnsmasq_full_nftset",
                   "DOWNLOAD_CHECK_CERTIFICATE", "SIGNED_PACKAGES", "SIGNATURE_CHECK", "USE_APK"}:
        require(config.get(symbol) == "y", f"Required CONFIG_{symbol}=y is absent")
    for symbol in DISABLED:
        require(config.get(symbol) not in ("y", "m"), f"CONFIG_{symbol} must be disabled")
    profiles = sorted(key for key, value in config.items()
                      if key.startswith("TARGET_") and "_DEVICE_" in key and value in ("y", "m"))
    require(profiles == [PROFILE], f"Expected one target profile, got: {profiles}")
    require(config.get("TARGET_PROFILE") == f'"DEVICE_{DEVICE}"', "Wrong TARGET_PROFILE")
    require(config.get("TARGET_ARCH_PACKAGES") == f'"{ARCH}"', "Wrong package architecture")
    require(config.get("TARGET_ROOTFS_PARTSIZE") == str(ROOT_PARTSIZE), "Build size setting changed")
    busybox_prefix = "BUSYBOX_CONFIG_" if config.get("BUSYBOX_CUSTOM") == "y" else "BUSYBOX_DEFAULT_"
    require(config.get(busybox_prefix + "NTPD") == "y", "Missing base NTP client")
    require(config.get("VERSION_NUMBER") == '"25.12.5"' and
            config.get("VERSION_CODE") == '"f0a60eee2fe0"', "Incorrect source release/revision label")
    require(config.get("VERSION_REPO") == '"https://downloads.openwrt.org/releases/25.12.5"',
            "Unexpected distribution repository")
    records = package_records(tree / "tmp/.packageinfo")
    names = {name for name in records if config.get(f"PACKAGE_{name}") == "y"}
    check_packages(names)
    build_names = {key.removeprefix("PACKAGE_") for key, value in config.items()
                   if key.startswith("PACKAGE_") and value in ("y", "m")}
    require(not any(unwanted(name) for name in build_names), "Excluded application/core selected for build")
    modules = {name for name in records if config.get(f"PACKAGE_{name}") == "m"}
    require(not modules, f"Unnecessary standalone packages: {sorted(modules)}")
    providers = set(names)
    for name in names:
        providers.update(token.lstrip("@") for token in records[name].get("Provides", "").split())
    checked = 0
    for name in sorted(names):
        for dependency in dependency_names(records[name].get("Depends", ""), config):
            require(dependency in providers, f"{name} lacks runtime dependency {dependency}")
            checked += 1
        conflicts = set(dependency_names(records[name].get("Conflicts", ""), config))
        require(not (conflicts & names), f"{name} conflicts with {sorted(conflicts & names)}")
    device_mk = (tree / "target/linux/mediatek/image/filogic.mk").read_text()
    definition = re.search(r"^define Device/cmcc_rax3000m\n(.*?)^endef", device_mk, re.M | re.S)
    require(definition is not None, "Missing official device definition")
    for value in ("mt7981b-cmcc-rax3000m-emmc", "mt7981b-cmcc-rax3000m-nand",
                  "sysupgrade.itb", "external-static-with-rootfs", "kmod-usb3", "kmod-mt7915e"):
        require(value in definition[1], f"Official unified profile lost {value}")
    dts = (tree / "target/linux/mediatek/dts/mt7981b-cmcc-rax3000m.dts").read_text()
    overlay = (tree / "target/linux/mediatek/dts/mt7981b-cmcc-rax3000m-emmc.dtso").read_text()
    require('compatible = "cmcc,rax3000m"' in dts and 'root=/dev/fit0 rootwait' in dts,
            "Device identity or FIT root changed")
    for value in ('partname = "production";', 'partname = "factory";', 'rootdisk = <&emmc_rootdisk>;',
                  'status = "okay";', 'nvmem-cell-names = "eeprom";'):
        require(value in overlay, f"Official eMMC/calibration support lost {value}")
    for label in ("lan1", "lan2", "lan3"):
        require(f'label = "{label}";' in dts, f"Missing LAN port {label}")
    legacy = re.search(r"^define Device/cmcc_rax3000m-emmc\n(.*?)^endef", device_mk, re.M | re.S)
    require(legacy is not None and "sysupgrade-tar | append-metadata" in legacy[1] and
            "IMAGE_SIZE" not in legacy[1] and "ARTIFACTS" not in legacy[1], "Wrong Kwrt eMMC image recipe")
    leaf = (tree / "target/linux/mediatek/dts/mt7981b-cmcc-rax3000m-emmc-kwrt.dts").read_text()
    for value in ('#include "mt7981b-cmcc-rax3000m.dts"', 'compatible = "cmcc,rax3000m-emmc"',
                  '/delete-property/ bootargs-override;', 'root=PARTLABEL=rootfs rootwait',
                  'partname = "factory";', 'nvmem-cell-names = "eeprom";'):
        require(value in leaf, f"Missing native Kwrt eMMC support: {value}")
    kernel_config = read_config(tree / "target/linux/mediatek/filogic/config-6.12")
    for symbol in BUILTIN_DRIVERS:
        require(kernel_config.get(symbol) == "y", f"Missing built-in CONFIG_{symbol}")
    check_device_patch(tree)
    return {
        "status": "passed", "target": "mediatek/filogic", "selected_profiles": profiles,
        "architecture": ARCH, "build_image_limit_bytes": BUILD_LIMIT,
        "actual_router_partition_limit_bytes": None, "partition_compatibility": "pending router evidence",
        "firewall": "firewall4/nftables", "dns": "dnsmasq-full with DHCP/DHCPv6/DNSSEC/nftset",
        "dependency_edges_checked": checked, "openclash_dependencies": records["luci-app-openclash"],
        "selected_packages": sorted(names), "required_packages": sorted(REQUIRED),
        "builtin_drivers": sorted(BUILTIN_DRIVERS), "core_packages": [],
        "config_sha256": digest(tree / ".config"), "hardware_validation": "not performed",
    }


def check_device_patch(tree):
    folder = Path(__file__).resolve().parents[1] / PROFILE_DIR / "patches"
    reviewed = "\n".join((folder / name).read_text().strip() for name in (
        "apk-package-signing.patch", "kwrt-emmc-layout.patch"))
    require(command("git", "-C", str(tree), "diff", "HEAD", "--no-ext-diff", "--binary", "--unified=0") ==
            reviewed, "OpenWrt changes differ from the reviewed device and APK-signing patches")


def check_core_files(root):
    elf_count = 0
    for path in root.rglob("*"):
        relative = str(path.relative_to(root))
        require(path.name not in {"mihomo", "clash", "clash_meta", "clash_tun"}, f"Bundled core: {relative}")
        if not path.is_file() or path.is_symlink():
            continue
        require(not relative.startswith(("etc/openclash/core/", "tmp/etc/openclash/core/")),
                f"Bundled core directory payload: {relative}")
        with path.open("rb") as stream:
            header = stream.read(20)
            if header[:4] != b"\x7fELF":
                continue
            payload = header + stream.read()
        require(b"mihomo" not in payload.lower(), f"Mihomo ELF payload: {relative}")
        # Hardware firmware may target an internal processor instead of the host CPU.
        if not relative.startswith("lib/firmware/"):
            require(len(header) == 20 and header[4:6] == b"\x02\x01" and
                    struct.unpack_from("<H", header, 18)[0] == 183, f"Wrong ELF architecture: {relative}")
            elf_count += 1
    return elf_count


def provenance(repo, build):
    lock = pins(repo)
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
        require(commit == lock[f"{prefix}_COMMIT"], f"{name} differs from pinned commit")
        result[name] = {"url": lock[f"{prefix}_URL"], "commit": commit}
        if name == "openwrt":
            check_device_patch(location)
        elif name != "openclash":
            require(not command("git", "-C", str(location), "status", "--porcelain", "--untracked-files=no"),
                    f"Unexpected tracked source changes: {name}")
    release_feeds = (build / "openwrt/feeds.conf.default").read_text()
    require(lock["PACKAGES_COMMIT"] in release_feeds and lock["LUCI_COMMIT"] in release_feeds,
            "Feeds do not match the official stable release")
    package = build / "openclash-feed/luci-app-openclash"
    makefile = (package / "Makefile").read_text()
    for field in ("VERSION", "RELEASE"):
        require(re.search(rf"^PKG_{field}:={re.escape(lock[f'OPENCLASH_{field}'])}$", makefile, re.M),
                f"Unexpected OpenClash {field.lower()}")
    require("PKG_BUILD_DEPENDS:=luci-base/host" in makefile, "Missing po2lmo host dependency")
    recipes = "\n".join(re.findall(
        r"^define (?:Build/(?:Prepare|Configure|Compile)|Package/[^\n ]+/install)\n(.*?)^endef",
        makefile, re.M | re.S))
    require(not re.search(r"^PKG_SOURCE[^\n]*=|^define Download/", makefile, re.M) and
            not re.search(r"\b(wget|curl|mihomo)\b", recipes, re.I), "Plugin build would fetch a core")
    require(command("git", "-C", str(build / "openclash-feed"), "diff", "--numstat") ==
            "1\t0\tluci-app-openclash/Makefile\n4\t4\tluci-app-openclash/root/usr/share/openclash/openclash_update.sh",
            "Unexpected OpenClash source changes")
    stored = {line.split()[0] for line in command(
        "git", "-C", str(build / "openclash-feed"), "cat-file", "--batch-all-objects",
        "--batch-check=%(objectname) %(objecttype)").splitlines() if line.endswith(" blob")}
    plugin_blobs = set()
    for entry in command("git", "-C", str(build / "openclash-feed"), "ls-tree", "-r", "HEAD").splitlines():
        details, path = entry.split("\t", 1)
        if path.startswith("luci-app-openclash/"):
            plugin_blobs.add(details.split()[2])
    require(not (stored - plugin_blobs), "Fetched blobs outside the OpenClash plugin")
    root = package / "root"
    check_core_files(root)
    updater = (root / "usr/share/openclash/openclash_update.sh").read_text()
    require("--allow-untrusted" not in updater and "--force-overwrite" not in updater,
            "Plugin APK updater bypasses signature/conflict checks")
    require("option enable '0'" in (root / "etc/config/openclash").read_text() and
            "option small_flash_memory '0'" in (root / "etc/config/openclash").read_text(),
            "Plugin service or small-flash defaults changed")
    require(not list((root / "etc/openclash/config").glob("*")), "Preconfigured proxy nodes/subscription")
    result["openwrt"].update({"tag": lock["OPENWRT_TAG"], "version": lock["OPENWRT_VERSION"],
                            "device_patch_sha256": digest(repo / PROFILE_DIR / "patches/kwrt-emmc-layout.patch"),
                            "apk_signing_patch_sha256": digest(repo / PROFILE_DIR / "patches/apk-package-signing.patch")})
    result["openclash"].update({
        "version": f"{lock['OPENCLASH_VERSION']}-{lock['OPENCLASH_RELEASE']}",
        "apk_version": package_records(build / "openwrt/tmp/.packageinfo")["luci-app-openclash"]["Version"],
        "upstream_tag": lock["OPENCLASH_UPSTREAM_TAG"], "upstream_commit": lock["OPENCLASH_UPSTREAM_COMMIT"],
        "core_included": False, "feed_blobs_fetched_outside_plugin": [],
        "host_dependency_patch_sha256": digest(repo / PROFILE_DIR / "patches/openclash-host-build.patch"),
        "apk_verification_patch_sha256": digest(repo / PROFILE_DIR / "patches/openclash-apk-verification.patch"),
    })
    result["workflow"] = {"run_id": os.getenv("GITHUB_RUN_ID"), "ref": os.getenv("GITHUB_REF")}
    return result


def parse_fdt(data):
    require(len(data) >= 40, "Truncated FDT header")
    magic, total, off_struct, off_strings, _, version, _, _, string_size, struct_size = struct.unpack_from(">10I", data)
    require(magic == 0xD00DFEED and version >= 17, "Invalid FIT/FDT header")
    require(40 <= total <= len(data) and off_struct + struct_size <= total and
            off_strings + string_size <= total, "FDT tables exceed bounds")
    strings = data[off_strings:off_strings + string_size]
    end = off_struct + struct_size
    offset = off_struct
    nodes, stack = {}, []
    while offset + 4 <= end:
        token = struct.unpack_from(">I", data, offset)[0]
        offset += 4
        if token == 1:
            stop = data.find(b"\0", offset, end)
            require(stop >= 0, "Unterminated FDT node")
            stack.append(data[offset:stop].decode())
            path = "/" + "/".join(stack[1:])
            require(path not in nodes, "Duplicate FDT node")
            nodes[path] = {}
            offset = (stop + 4) & ~3
        elif token == 2:
            require(stack, "Unbalanced FDT nodes")
            stack.pop()
        elif token == 3:
            require(stack and offset + 8 <= end, "Invalid FDT property")
            size, name_offset = struct.unpack_from(">II", data, offset)
            offset += 8
            stop = strings.find(b"\0", name_offset)
            require(stop >= name_offset and offset + size <= end, "FDT property exceeds bounds")
            name = strings[name_offset:stop].decode()
            node = nodes["/" + "/".join(stack[1:])]
            require(name not in node, "Duplicate FDT property")
            node[name] = data[offset:offset + size]
            offset = (offset + size + 3) & ~3
        elif token == 4:
            continue
        elif token == 9:
            require(not stack, "Unclosed FDT node")
            return nodes, total
        else:
            raise ValueError(f"Unknown FDT token: {token}")
    raise ValueError("Missing FDT end token")


def fdt_strings(value):
    require(value.endswith(b"\0"), "Malformed FDT string")
    return value[:-1].decode().split("\0")


def check_fit(data):
    nodes, total = parse_fdt(data)
    images = {path: props for path, props in nodes.items() if re.fullmatch(r"/images/[^/]+", path)}
    require(images, "FIT has no images")
    payloads, checks = {}, []
    for path, props in images.items():
        require(fdt_strings(props["arch"]) == ["arm64"], f"Wrong FIT architecture: {path}")
        require("data-position" in props and "data-offset" not in props and "data" not in props,
                f"Expected official external-static payload: {path}")
        require(len(props["data-position"]) == 4 and len(props["data-size"]) == 4, "Invalid FIT data fields")
        offset, size = struct.unpack(">I", props["data-position"])[0], struct.unpack(">I", props["data-size"])[0]
        require(total <= offset and 0 < size <= len(data) - offset, f"FIT payload exceeds image: {path}")
        payload = data[offset:offset + size]
        algorithms = []
        for hash_path, fields in nodes.items():
            if not re.fullmatch(re.escape(path) + r"/hash[^/]*", hash_path):
                continue
            algorithm = fdt_strings(fields["algo"])[0]
            if algorithm == "crc32":
                expected = struct.pack(">I", zlib.crc32(payload))
            else:
                require(algorithm in {"sha1", "sha256"}, f"Unsupported FIT hash: {algorithm}")
                expected = hashlib.new(algorithm, payload).digest()
            require(fields["value"] == expected, f"FIT {algorithm} checksum mismatch: {path}")
            algorithms.append(algorithm)
        require("crc32" in algorithms and any(a in algorithms for a in ("sha1", "sha256")),
                f"Missing native FIT payload checks: {path}")
        payloads[path] = payload
        checks.append({"node": path, "offset": offset, "size": size, "hashes": algorithms})
    for storage in ("emmc", "nand"):
        name = f"mt7981b-cmcc-rax3000m-{storage}"
        overlay = f"/images/fdt-{name}"
        require(fdt_strings(nodes[f"/configurations/{name}"]["fdt"]) == [f"fdt-{name}"],
                f"Missing {storage} overlay configuration")
        overlay_nodes, _ = parse_fdt(payloads[overlay])
        require(UNIFIED_BOARD in fdt_strings(overlay_nodes["/"]["compatible"]), "Overlay identity differs")
        if storage == "emmc":
            require(any(p.get("partname") == b"production\0" for p in overlay_nodes.values()),
                    "eMMC overlay lacks the production root partition")
            require(any(p.get("partname") == b"factory\0" for p in overlay_nodes.values()),
                    "eMMC overlay lacks local calibration storage")
    default = fdt_strings(nodes["/configurations"]["default"])[0]
    config = nodes[f"/configurations/{default}"]
    kernel = payloads["/images/" + fdt_strings(config["kernel"])[0]]
    require(kernel[:2] == b"\x1f\x8b", "FIT kernel is not gzip compressed")
    decoded_kernel = gzip.decompress(kernel)
    require(len(decoded_kernel) >= 64 and decoded_kernel[56:60] == b"ARM\x64",
            "FIT kernel lacks the ARM64 Linux Image header")
    base, _ = parse_fdt(payloads["/images/" + fdt_strings(config["fdt"])[0]])
    require(UNIFIED_BOARD in fdt_strings(base["/"]["compatible"]), "FIT device tree is for another model")
    require(base["/chosen"].get("bootargs-override") == b"root=/dev/fit0 rootwait\0", "FIT root changed")
    root = payloads["/images/" + next(v for v in fdt_strings(config["loadables"]) if v.startswith("rootfs"))]
    require(root[:4] == b"hsqs" and len(root) >= 96, "Missing squashfs rootfs")
    require(struct.unpack_from("<H", root, 28)[0] == 4, "Wrong squashfs version")
    root_used = struct.unpack_from("<Q", root, 40)[0]
    require(96 <= root_used <= len(root), "Squashfs exceeds FIT rootfs payload")
    return {"status": "passed", "payloads": checks, "squashfs_bytes_used": root_used,
            "uncompressed_linux_image_bytes": len(decoded_kernel),
            "default_configuration": default, "emmc_overlay": "mt7981b-cmcc-rax3000m-emmc",
            "uboot_overlay_selection": "pending device evidence"}


def installed_records(root):
    database = root / "lib/apk/db/installed"
    require(database.is_file(), "Missing installed APK database in final build_dir rootfs")
    records = {}
    for paragraph in database.read_text().split("\n\n"):
        fields = dict(line.split(":", 1) for line in paragraph.splitlines() if ":" in line)
        if "P" in fields:
            require(fields["P"] not in records, "Duplicate installed package")
            records[fields["P"]] = fields
    require(records, "Empty installed APK database")
    return records


def check_tar(data):
    """Inspect a real native Kwrt sysupgrade TAR without executing its contents."""
    folder = "sysupgrade-" + DEVICE
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        members = archive.getmembers()
        expected = [folder, folder + "/CONTROL", folder + "/kernel", folder + "/root"]
        require([m.name.rstrip("/") for m in members] == expected, "Unexpected sysupgrade TAR members")
        require(members[0].isdir() and all(m.isfile() for m in members[1:]),
                "Links or special files in sysupgrade TAR")
        require(all(0 < m.size <= 128 * 1024 * 1024 for m in members[1:]), "Invalid TAR payload size")
        require(archive.extractfile(members[1]).read() == f"BOARD={DEVICE}\n".encode(), "Wrong TAR board")
        kernel = archive.extractfile(members[2]).read()
        root = archive.extractfile(members[3]).read()
    nodes, total = parse_fdt(kernel)
    require(total == len(kernel), "Unexpected trailing bytes in kernel FIT")
    images = {p: props for p, props in nodes.items() if re.fullmatch(r"/images/[^/]+", p)}
    require(len(images) == 2, "Expected an embedded kernel and device tree in FIT")
    payloads, hashes = {}, []
    for path, props in images.items():
        require(fdt_strings(props["arch"]) == ["arm64"], "Wrong eMMC FIT architecture")
        require("data" in props and "data-position" not in props and "data-offset" not in props,
                "Expected an embedded eMMC FIT payload")
        payload = props["data"]
        algorithms = []
        for hp, fields in nodes.items():
            if not re.fullmatch(re.escape(path) + r"/hash[^/]*", hp):
                continue
            algorithm = fdt_strings(fields["algo"])[0]
            require(algorithm in {"crc32", "sha1", "sha256"}, "Unsupported FIT checksum")
            expected = struct.pack(">I", zlib.crc32(payload)) if algorithm == "crc32" else hashlib.new(algorithm, payload).digest()
            require(fields["value"] == expected, f"eMMC FIT {algorithm} checksum mismatch: {path}")
            algorithms.append(algorithm)
        require("crc32" in algorithms and any(a in algorithms for a in ("sha1", "sha256")), "Missing FIT hashes")
        payloads[path] = payload
        hashes.append({"node": path, "payload_bytes": len(payload), "hashes": algorithms})
    default = fdt_strings(nodes["/configurations"]["default"])[0]
    cfg = nodes["/configurations/" + default]
    kernel_path = "/images/" + fdt_strings(cfg["kernel"])[0]
    require(fdt_strings(images[kernel_path]["compression"]) == ["lzma"], "Wrong eMMC kernel compression")
    decoder = lzma.LZMADecompressor(memlimit=64 * 1024 * 1024)
    decoded = decoder.decompress(payloads[kernel_path], max_length=128 * 1024 * 1024)
    require(decoder.eof and len(decoded) >= 64 and decoded[56:60] == b"ARM\x64", "Invalid ARM64 kernel")
    base, _ = parse_fdt(payloads["/images/" + fdt_strings(cfg["fdt"])[0]])
    require(fdt_strings(base["/"]["compatible"])[0] == BOARD, "Wrong eMMC device tree identity")
    require(base["/chosen"].get("bootargs") == b"root=PARTLABEL=rootfs rootwait\0" and
            "bootargs-override" not in base["/chosen"] and "rootdisk" not in base["/chosen"],
            "Wrong eMMC root/boot arguments")
    require(any(p.get("partname") == b"factory\0" for p in base.values()), "Missing local factory support")
    require(any("mmc@" in p and props.get("status") == b"okay\0" for p, props in base.items()),
            "Missing active eMMC controller")
    require(not any(p.get("partname") == b"production\0" for p in base.values()), "Unexpected production layout")
    require(root[:4] == b"hsqs" and len(root) >= 96, "Missing TAR squashfs root")
    require(struct.unpack_from("<H", root, 28)[0] == 4, "Wrong squashfs version")
    used = struct.unpack_from("<Q", root, 40)[0]
    require(96 <= used <= len(root), "Squashfs exceeds TAR root payload")
    end = (len(root) + 65535) // 65536 * 65536
    require(end == (used + 65535) // 65536 * 65536, "Rootdisk and upgrade overlay offsets differ")
    return {"status": "passed", "kernel_bytes": len(kernel), "root_payload_bytes": len(root),
            "squashfs_bytes_used": used, "overlay_offset_bytes": end,
            "minimum_root_partition_bytes": end + 4096,
            "minimum_note": "Only allows the native 4 KiB reset marker; writable space and backup capacity still require actual GPT evidence.",
            "fit_payloads": hashes, "uncompressed_linux_image_bytes": len(decoded),
            "board": BOARD, "root": "PARTLABEL=rootfs", "partition_layout": "unchanged; not embedded"}


def check_apk_sources(root):
    sources, active = {}, []
    for path in sorted((root / "etc/apk").glob("repositories*")):
        candidates = sorted(path.glob("*")) if path.is_dir() else [path]
        for file in candidates:
            if not file.is_file():
                continue
            text = file.read_text()
            relative = str(file.relative_to(root))
            sources[relative] = text
            for number, line in enumerate(text.splitlines(), 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                urls = re.findall(r"https?://\S+", line)
                require(len(urls) == 1, f"Invalid active APK feed in {relative}:{number}")
                url = urls[0]
                require(url.startswith("https://downloads.openwrt.org/releases/25.12.5/"),
                        f"Unexpected active APK feed in {relative}:{number}; expected official release 25.12.5")
                require("mediatek/filogic" in url or ARCH in url,
                        f"Wrong APK feed target/architecture in {relative}:{number}")
                require("/openclash/" not in url, f"Nonexistent OpenClash APK repository in {relative}:{number}")
                active.append(url)
    require(active, "Missing active software repositories")
    return {"software_repositories": sources, "active_software_repositories": active}


def check_rootfs(root, versions):
    records = installed_records(root)
    require({p: v["V"] for p, v in records.items()} == versions, "APK database and final manifest differ")
    check_packages(set(records))
    elf_count = check_core_files(root)
    config = (root / "etc/config/openclash").read_text()
    require("option enable '0'" in config and "option small_flash_memory '0'" in config, "Unsafe proxy defaults")
    require(not list((root / "etc/openclash/config").glob("*")), "Bundled subscription/proxy configuration")
    startup = (root / DEFAULTS).read_text()
    for value in ("/etc/init.d/openclash disable", "set openclash.config.enable='0'",
                  "set openclash.config.small_flash_memory='0'", "flow_offloading='0'", "flow_offloading_hw='0'",
                  "anon_mount='0'", "anon_swap='0'", "auto_mount='0'", "auto_swap='0'"):
        require(value in startup, f"Missing safe default: {value}")
    require(not re.search(r"\b(wget|curl|sgdisk|sfdisk|parted|fw_setenv)\b|openclash_core\.sh", startup),
            "Unexpected downloader, partition or bootloader operation in defaults")
    require(os.access(root / DEFAULTS, os.X_OK), "Defaults script is not executable")
    for name in ("base.zh-cn.lmo", "firewall.zh-cn.lmo", "package-manager.zh-cn.lmo", "openclash.zh-cn.lmo"):
        require((root / "usr/lib/lua/luci/i18n" / name).stat().st_size > 0, f"Missing Chinese translation: {name}")
    for module in ("mt7915e.ko", "tun.ko", "nft_tproxy.ko", "nft_socket.ko", "usb-storage.ko", "vfat.ko"):
        require(any((root / "lib/modules").rglob(module)), f"Missing kernel module: {module}")
    require((root / "sbin/block").is_file(), "Missing basic USB/block-device management tool")
    kernel = records["kernel"]["V"]
    edges = 0
    for name, fields in records.items():
        for dependency in fields.get("D", "").split():
            if dependency.startswith("kernel="):
                require(dependency == f"kernel={kernel}", f"Kernel ABI mismatch: {name}: {dependency}")
                edges += 1
    require(edges > 0, "No kernel ABI dependencies checked")
    repository_report = check_apk_sources(root)
    public_keys = [p for p in (root / "etc/apk/keys").glob("*") if p.is_file()]
    require(public_keys, "No trusted APK public keys installed")
    return {"elf_files_checked": elf_count, "kernel_package_version": kernel,
            "kernel_abi_dependencies_checked": edges, **repository_report,
            "apk_trusted_public_keys_count": len(public_keys),
            "official_remote_kmod_abi": "not established; use packages built for this exact kernel ABI"}


def check_artifact(tree):
    check_config(tree)
    target = tree / "bin/targets/mediatek/filogic"
    images = [p for p in tree.glob("bin/targets/**/*sysupgrade*") if p.is_file() and not p.name.endswith(".json")]
    require(len(images) == 1 and images[0].parent == target and
            images[0].name.endswith(f"{DEVICE}-squashfs-sysupgrade.bin"), f"Unexpected upgrade images: {images}")
    image = images[0]
    size, sha256 = image.stat().st_size, digest(image)
    require(size > 0, "Empty image")
    profiles = json.loads((target / "profiles.json").read_text())
    require(profiles["target"] == "mediatek/filogic" and set(profiles["profiles"]) == {DEVICE}, "Wrong profiles")
    profile = profiles["profiles"][DEVICE]
    require(BOARD in profile["supported_devices"], "Wrong device identity")
    require(profile.get("file_size_limits", {}).get("image") in (None, 0), "Unexpected fixed partition assumption")
    entries = [i for i in profile["images"] if i["type"] == "sysupgrade"]
    require(len(entries) == 1 and entries[0]["name"] == image.name and
            entries[0]["filesystem"] == "squashfs", "Wrong upgrade image format")
    require(entries[0]["sha256"] == sha256 and entries[0]["size"] == size, "Image metadata checksum/size differs")
    tar = check_tar(image.read_bytes())
    metadata_path = target / "rax3000m-fwtool.json"
    subprocess.run([str(tree / "staging_dir/host/bin/fwtool"), "-i", str(metadata_path), str(image)], check=True)
    metadata = json.loads(metadata_path.read_text())
    require(BOARD in metadata.get("new_supported_devices", metadata.get("supported_devices", [])), "Wrong embedded model")
    require(metadata["version"]["target"] == "mediatek/filogic" and metadata["version"]["version"] == "25.12.5",
            "Wrong embedded target/version")
    manifests = list(target.glob("*.manifest"))
    require(len(manifests) == 1, "Expected one final manifest")
    versions = dict(line.split(" - ", 1) for line in manifests[0].read_text().splitlines() if line)
    require(versions["luci-app-openclash"] == package_records(tree / "tmp/.packageinfo")["luci-app-openclash"]["Version"],
            "OpenClash package version differs")
    roots = list(tree.glob("build_dir/target-*/root-mediatek"))
    require(len(roots) == 1, f"Expected one final rootfs in build_dir: {roots}")
    root_report = check_rootfs(roots[0], versions)
    kernels = list(tree.glob("build_dir/target-*/linux-mediatek_filogic/linux-*/.config"))
    require(len(kernels) == 1, "Missing actual kernel configuration")
    kernel_config = read_config(kernels[0])
    for symbol in BUILTIN_DRIVERS:
        require(kernel_config.get(symbol) == "y", f"Compiled kernel lost CONFIG_{symbol}")
    return {
        "status": "passed", "device": DEVICE, "image": image.name, "sha256": sha256,
        "image_size_bytes": size, "build_image_limit_bytes": BUILD_LIMIT,
        "actual_router_partition_limit_bytes": None, "writable_overlay_bytes": None,
        "size_note": "The existing eMMC profile has no fixed IMAGE_SIZE. Actual kernel/rootfs GPT capacities and usable overlay are pending; the image is not cleared for flashing.",
        "tar": tar, "embedded_metadata": metadata, "package_count": len(versions), **root_report,
        "rootfs_path": str(roots[0].relative_to(tree)), "kernel_config_path": str(kernels[0].relative_to(tree)),
        "openclash_version": versions["luci-app-openclash"], "core_files": [],
        "default_service_enabled": False, "small_flash_memory": False,
        "candidate_firmware": True, "safe_to_flash_confirmed": False,
        "router_precheck": "not performed", "boot_partition_compatibility": "pending router evidence",
        "hardware_validation": "not performed", "proxy_runtime_validation": "not performed",
        "excluded_boot_artifacts": [i["name"] for i in profile["images"] if i["type"] != "sysupgrade"],
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
            result = (check_config if args.mode == "config" else check_artifact)(args.paths[0])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(f"{args.mode}: passed; report: {output}")
    except (ValueError, OSError, KeyError, IndexError, UnicodeError, struct.error, zlib.error,
            lzma.LZMAError, tarfile.TarError, subprocess.CalledProcessError) as error:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False, indent=2) + "\n")
        if os.getenv("GITHUB_ACTIONS") == "true":
            message = str(error).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            print(f"::error title=RAX3000M {args.mode} validation::{message}", flush=True)
        parser.exit(1, f"{args.mode}: FAILED: {error}\n")


if __name__ == "__main__":
    main()
