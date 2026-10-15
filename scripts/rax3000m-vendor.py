#!/usr/bin/env python3
"""Map every vendor package and validate a separate 25.12 vendor rebuild."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import tarfile

REPO = Path(__file__).resolve().parents[1]
PROFILE = REPO / "devices/rax3000m-emmc-vendor"
spec = importlib.util.spec_from_file_location("rax_common", REPO / "scripts/check-rax3000m.py")
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
require, digest = common.require, common.digest
CORE = "etc/openclash/core/clash_meta"
DEFAULTS = "etc/uci-defaults/zz-rax3000m-vendor"


def pins():
    return dict(line.split("=", 1) for line in (PROFILE / "sources.env").read_text().splitlines()
                if line and not line.startswith("#"))


def inventory():
    rows = [line.split(" - ", 1) for line in (PROFILE / "vendor-packages.manifest").read_text().splitlines()]
    require(len(rows) == 375 and len(dict(rows)) == 375, "The complete vendor inventory must contain 375 unique packages")
    return rows


def metadata(tree):
    records = {}
    for file in [tree / "tmp/.packageinfo", *sorted(tree.glob("feeds/*.index"))]:
        if not file.is_file():
            continue
        source, current = "", None
        for line in file.read_text().splitlines():
            if line.startswith("Source-Makefile: "):
                source = line.split(": ", 1)[1]
            elif line.startswith("Package: "):
                name = line.split(": ", 1)[1]
                current = records.setdefault(name, {"Package": name, "Source-Makefile": source})
            elif line == "@@":
                current = None
            elif current is not None and ": " in line:
                key, value = line.split(": ", 1)
                current.setdefault(key, value)
    return records


def runtime_name(name, record):
    abi = record.get("ABI-Version", "")
    require(not abi or re.fullmatch(r"[\w.-]+", abi), f"Cannot resolve the actual ABI suffix for {name}")
    return name + ("-" if abi and name[-1].isdigit() else "") + abi


def map_packages(tree):
    records = metadata(tree)
    aliases = {runtime_name(name, record): name for name, record in records.items()
               if not record.get("ABI-Version") or re.fullmatch(r"[\w.-]+", record["ABI-Version"])}
    mapped = []
    for vendor, version in inventory():
        if vendor == "kernel":
            mapped.append({"vendor": vendor, "vendor_version": version, "symbol": None,
                           "runtime": "kernel", "kind": "automatic Linux build; true ABI, never vendor ~1"})
            continue
        name = "apk-mbedtls" if vendor == "opkg" else vendor if vendor in records else aliases.get(vendor)
        require(name in records, f"No supported source mapping for vendor package {vendor}; refusing to drop it")
        record = records[name]
        mapped.append({"vendor": vendor, "vendor_version": version, "symbol": name,
                       "runtime": runtime_name(name, record), "source_version": record.get("Version"),
                       "source": record.get("Source-Makefile"),
                       "kind": "native 25.12 APK replacement" if vendor == "opkg" else
                               "ABI-name mapping" if name != vendor else "same package name"})
    return mapped


def create_config(tree, output):
    mapped = map_packages(tree)
    base = (REPO / "devices/rax3000m-emmc-openclash/config").read_text()
    values = dict(common.read_config(REPO / "devices/rax3000m-emmc-openclash/config"))
    for key in re.findall(r"^# CONFIG_(\S+) is not set$", base, re.M):
        values[key] = None
    for entry in mapped:
        if entry["symbol"]:
            values["PACKAGE_" + entry["symbol"]] = "y"
    for package in ("luci-app-openclash", "openclash-mihomo-core", "luci-nginx", "nginx-ssl",
                    "nginx-mod-luci", "nginx-mod-ubus", "nginx-ssl-util", "openssl-util"):
        values["PACKAGE_" + package] = "y"
    for package in ("opkg", "luci-light", "luci-ssl", "uhttpd", "uhttpd-mod-ubus", "px5g-mbedtls"):
        values["PACKAGE_" + package] = None
    for feed in ("vendor", "openclash", "local"):
        values["FEED_" + feed] = None
    values["EXTRA_IMAGE_NAME"] = '"vendor-openclash-mihomo"'
    prefix = "PACKAGE_luci-app-passwall_"
    # Keep the vendor's clients, with nftables as the single active firewall backend.
    for option in ("Iptables_Transparent_Proxy", "INCLUDE_Hysteria", "INCLUDE_NaiveProxy",
                   "INCLUDE_Shadowsocks_Rust_Client", "INCLUDE_Shadowsocks_Rust_Server",
                   "INCLUDE_ShadowsocksR_Libev_Server", "INCLUDE_Shadow_TLS", "INCLUDE_Xray",
                   "INCLUDE_Xray_Plugin", "INCLUDE_V2ray_Geodata", "INCLUDE_V2ray_Plugin"):
        values[prefix + option] = None
    for option in ("Nftables_Transparent_Proxy", "INCLUDE_Geoview", "INCLUDE_Haproxy",
                   "INCLUDE_ShadowsocksR_Libev_Client", "INCLUDE_Simple_Obfs", "INCLUDE_SingBox"):
        values[prefix + option] = "y"
    output.write_text("# Generated from all 375 vendor packages; see package-map.json.\n" + "".join(
        f"CONFIG_{key}={value}\n" if value is not None else f"# CONFIG_{key} is not set\n"
        for key, value in sorted(values.items())))
    return mapped


def core_check(path):
    lock = pins()
    require(path.is_file() and digest(path) == lock["MIHOMO_BINARY_SHA256"], "Mihomo binary differs from the official pinned release")
    with path.open("rb") as stream:
        header = stream.read(64)
    require(header[:6] == b"\x7fELF\x02\x01" and struct.unpack_from("<H", header, 18)[0] == 183,
            "Mihomo is not little-endian ARM64 ELF")
    return {"version": lock["MIHOMO_VERSION"], "sha256": digest(path), "bytes": path.stat().st_size,
            "source_url": lock["MIHOMO_URL"], "gzip_sha256": lock["MIHOMO_GZIP_SHA256"],
            "architecture": "AArch64", "executed_in_cloud": False}


def package_version_check(tree):
    apk = Path(os.environ.get("OPENWRT_APK", tree / "staging_dir/host/bin/apk"))
    require(apk.is_file() and os.access(apk, os.X_OK), "Build the native APK host tool before version validation")
    config = common.read_config(tree / ".config")
    records = metadata(tree)
    literal, templates, deferred = [], [], []
    for name, record in sorted(records.items()):
        if config.get("PACKAGE_" + name) != "y":
            continue
        version = record.get("Version", "")
        require(bool(version), f"Missing package version for {name}")
        if version == "x":
            # LuCI deliberately omits its computed Git/translation version in DUMP.
            deferred.append({"package": name, "source": record.get("Source-Makefile"), "metadata": version})
        elif "<" in version:
            # Validate the literal suffix, including snapshot dates, using a
            # syntax probe. Never write this probe into package metadata or ABI.
            probe = re.sub(r"<(?:LINUX|LIBGCC|LIBC)_VERSION>", "0", version)
            require("<" not in probe and ">" not in probe, f"Unknown package version placeholder: {name}={version}")
            if probe.endswith("-r"):
                probe += "0"  # DUMP also defers built-in kernel-module revisions.
            templates.append({"package": name, "metadata": version, "syntax_probe": probe})
        else:
            literal.append({"package": name, "version": version})
    checked = {entry["version"] for entry in literal} | {entry["syntax_probe"] for entry in templates}
    require(bool(checked), "No selected package versions were checked")
    invalid = set()
    for version in sorted(checked):
        result = subprocess.run([str(apk), "version", "--check", version], capture_output=True, text=True)
        if result.returncode:
            invalid.add(version)
    bad = [f"{r['package']}={r['version']}" for r in literal if r["version"] in invalid]
    bad += [f"{r['package']}={r['metadata']}" for r in templates if r["syntax_probe"] in invalid]
    require(not invalid, "Native APK rejected package version metadata: " + "; ".join(bad))
    return {"status": "passed", "scope": "metadata syntax preflight; not final versions or kernel ABI",
            "apk_tool": str(apk), "selected_package_count": len(literal) + len(templates) + len(deferred),
            "literal_versions_checked": len(literal), "template_syntax_checked": len(templates),
            "deferred_luci_version_count": len(deferred), "native_version_commands": len(checked),
            "actual_kernel_abi_verified": False, "final_version_validation_pending": bool(templates or deferred),
            "literal_packages": literal, "template_checks": templates, "deferred_luci_versions": deferred}


def check_source_archive(file, source, downloads):
    require(file.is_file() and digest(file) == source["sha256"], f"Source archive missing or hash mismatch: {file.name}")
    with tarfile.open(file) as archive:
        names = archive.getnames()
        roots = {name.split("/", 1)[0] for name in names}
        require(len(roots) == 1, f"Ambiguous source archive root: {file.name}")
        prefix = next(iter(roots)) + "/"
        for required in source.get("required_files", []):
            require(prefix + required in names, f"Missing required source file {required}: {file.name}")
        declared = {}
        if prefix + ".gitmodules" in names:
            # .gitmodules uses Git config syntax. Its tab/space indentation is
            # not INI continuation syntax; parse it with Git itself.
            result = subprocess.run(["git", "config", "--file", "-", "--null", "--get-regexp",
                                     r"^submodule\..*\.(path|url)$"],
                                    input=archive.extractfile(prefix + ".gitmodules").read(), capture_output=True)
            require(result.returncode in (0, 1), f"Invalid Git submodule metadata: {file.name}")
            sections = {}
            for entry in result.stdout.decode().split("\0"):
                if not entry:
                    continue
                key, value = entry.split("\n", 1)
                section, field = key.rsplit(".", 1)
                record = sections.setdefault(section, {})
                require(field not in record, f"Duplicate Git submodule field: {key}")
                record[field] = value
            for record in sections.values():
                require(set(record) == {"path", "url"}, f"Incomplete Git submodule metadata: {file.name}")
                path = record["path"]
                require(path not in declared, f"Duplicate source submodule path: {path}")
                declared[path] = record["url"]
    locked = source.get("submodules", {})
    require(set(declared) == set(locked), f"Unpinned or missing submodule in {file.name}: {sorted(set(declared) ^ set(locked))}")
    children = {}
    for path, child in locked.items():
        require(declared[path] == child["git_url"], f"Submodule URL differs from source lock: {path}")
        children[path] = {"commit": child["commit"], "url": child["url"],
                          **check_source_archive(downloads / child["local_filename"], child, downloads)}
    return {"archive": file.name, "sha256": digest(file), "submodules": children}


def source_archive_check(build):
    locks = json.loads((PROFILE / "source-hashes.json").read_text())
    downloads = build / "openwrt/dl"
    result = {}
    for name in ("fullconenat-nft", "simple-obfs", "tcping"):
        recipe = (build / "vendor-feed" / name / "Makefile").read_text()
        match = re.search(r"^PKG_SOURCE:=([^\n$]+)$", recipe, re.M)
        require(match is not None, f"Cannot locate pinned Git source archive: {name}")
        result[name] = check_source_archive(downloads / match[1], locks[name], downloads)
    return {"status": "passed", "scope": "all three Git-to-archive substitutions and their recursive submodules", "archives": result}


def failure_excerpt(text):
    # FAILED_SLOTS_DIR is a normal compiler definition, not a failed command.
    pattern = r"\berror:|\bFAILED\b|Error [0-9]|^ERROR:|No rule to make"
    errors = [line for line in text.splitlines() if re.search(pattern, line)]
    lines = [line if len(line) <= 400 else line[:180] + " ... " + line[-210:] for line in errors[-14:]]
    while len("\n".join(lines).encode()) > 3000 and len(lines) > 4:
        del lines[3]
    result = "\n".join(lines)
    if len(result.encode()) > 3000:
        raw = result.encode()
        result = raw[:1450].decode(errors="ignore") + "\n...\n" + raw[-1450:].decode(errors="ignore")
    return result


def config_check(tree):
    config = common.read_config(tree / ".config")
    selected = [name for name, value in config.items() if name.startswith("TARGET_mediatek_filogic_DEVICE_") and value == "y"]
    require(selected == [common.PROFILE], f"Unexpected selected device(s): {selected}")
    for key in common.DISABLED | {"PACKAGE_opkg", "FEED_vendor", "FEED_local"}:
        require(config.get(key) not in ("y", "m"), f"Unexpected enabled option {key}")
    require(config.get("TARGET_mediatek") == config.get("TARGET_mediatek_filogic") == "y", "Wrong build target")
    require(config.get("TARGET_ARCH_PACKAGES") == '"aarch64_cortex-a53"', "Wrong target package architecture")
    require(config.get("SIGNED_PACKAGES") == config.get("SIGNATURE_CHECK") == config.get("DOWNLOAD_CHECK_CERTIFICATE") == "y",
            "Package or TLS verification was disabled")
    mapped = map_packages(tree)
    for entry in mapped:
        name = entry["symbol"]
        require(name is None or config.get("PACKAGE_" + name) == "y", f"Vendor package missing after defconfig: {entry['vendor']}")
    for name in ("luci-app-openclash", "openclash-mihomo-core", "dnsmasq-full", "firewall4", "ruby-yaml",
                 "kmod-tun", "kmod-nft-tproxy", "kmod-nft-socket", "nginx-ssl"):
        require(config.get("PACKAGE_" + name) == "y", f"Missing required OpenClash/base package {name}")
    for name in common.CONFLICTING:
        require(config.get("PACKAGE_" + name) not in ("y", "m"), f"Conflicting package {name}")
    records = common.package_records(tree / "tmp/.packageinfo")
    names = {key[8:] for key, value in config.items() if key.startswith("PACKAGE_") and value == "y" and key[8:] in records}
    provided = set(names)
    for name in names:
        provided.update(token.lstrip("@") for token in records[name].get("Provides", "").split())
    require(not any(value == "m" and key.startswith("PACKAGE_") and key[8:] in records for key, value in config.items()),
            "Separate uninstalled modules/packages selected")
    edges = 0
    for name in names:
        for dependency in common.dependency_names(records[name].get("Depends", ""), config):
            require(dependency in provided, f"Missing dependency: {name} -> {dependency}")
            edges += 1
        conflicts = set(common.dependency_names(records[name].get("Conflicts", ""), config))
        require(not (conflicts & names), f"Package conflict: {name} -> {sorted(conflicts & names)}")
    return {"status": "passed", "device": common.DEVICE, "architecture": common.ARCH,
            "vendor_package_count": len(mapped), "selected_package_count": len(names),
            "dependency_edges_checked": edges, "config_sha256": digest(tree / ".config"),
            "package_mapping": mapped, "mihomo_included": True, "small_flash_memory": False,
            "hardware_validation": "pending", "game_latency_fix_verified": False}


def root_check(root, versions, mapped):
    installed = common.installed_records(root)
    require({name: row["V"] for name, row in installed.items()} == versions, "Final manifest and installed database differ")
    for entry in mapped:
        require(entry["runtime"] in versions, f"Vendor equivalent absent in final image: {entry['vendor']}")
    for name in ("luci-app-openclash", "openclash-mihomo-core", "firewall4", "dnsmasq-full", "nginx-ssl"):
        require(name in versions, f"Required package absent from final image: {name}")
    require(not (set(versions) & common.CONFLICTING), "Conflicting DNS/firewall variants installed")
    count = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        relative = str(path.relative_to(root))
        if relative.startswith("etc/openclash/core/"):
            require(relative == CORE, f"Unexpected additional OpenClash core: {relative}")
        with path.open("rb") as stream:
            header = stream.read(20)
        if header[:4] == b"\x7fELF" and not relative.startswith("lib/firmware/"):
            require(header[:6] == b"\x7fELF\x02\x01" and struct.unpack_from("<H", header, 18)[0] == 183,
                    f"Wrong executable architecture: {relative}")
            count += 1
    core = core_check(root / CORE)
    require(os.access(root / CORE, os.X_OK), "Mihomo is not executable")
    text = (root / "etc/config/openclash").read_text()
    require("option enable '0'" in text and "option small_flash_memory '0'" in text, "Unsafe OpenClash defaults")
    require(not list((root / "etc/openclash/config").glob("*")), "Personal proxy configuration bundled")
    defaults = (root / DEFAULTS).read_text()
    require(defaults == (PROFILE / "packages/my-default-settings/defaults").read_text(), "Device defaults differ from reviewed source")
    require(not (root / "etc/uci-defaults/99-default-settings").exists() and not (root / "etc/rc.d/S99cpumark").exists(),
            "Unsafe vendor credentials, benchmark or acceleration defaults were included")
    require(not (root / "etc/hotplug.d/online/50-opkg-restore").exists(), "Automatic legacy package restoration installed")
    for module in ("mt7915e.ko", "tun.ko", "nft_tproxy.ko", "nft_socket.ko", "nft_fullcone.ko", "usb-storage.ko"):
        require(any((root / "lib/modules").rglob(module)), f"Missing required module: {module}")
    require((root / "usr/lib/lua/luci/i18n/openclash.zh-cn.lmo").stat().st_size > 0, "Missing Chinese OpenClash UI")
    nginx = (root / "etc/config/nginx").read_text()
    require("443 ssl" in nginx and "uci_manage_ssl 'self-signed'" in nginx, "Missing native nginx HTTPS configuration")
    kernel, edges = versions["kernel"], 0
    for name, row in installed.items():
        for dep in row.get("D", "").split():
            if dep.startswith("kernel="):
                require(dep == "kernel=" + kernel, f"Kernel ABI mismatch for {name}")
                edges += 1
    require(edges > 0 and "~1-" not in kernel, "Vendor's fake kernel ABI was reused")
    return {"elf_files_checked": count, "kernel_package_version": kernel, "kernel_abi_dependencies_checked": edges,
            "mihomo": core, "default_service_enabled": False, "small_flash_memory": False,
            **repository_check(root)}


def repository_check(root):
    """The explicit store feed is additional; it does not establish kmod ABI compatibility."""
    sources, active = {}, []
    store = "https://istore.istoreos.com/repo-apk/all/compat/packages.adb"
    for path in sorted((root / "etc/apk").glob("repositories*")):
        for file in sorted(path.glob("*")) if path.is_dir() else [path]:
            if not file.is_file():
                continue
            text = file.read_text()
            sources[str(file.relative_to(root))] = text
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                urls = re.findall(r"https?://\S+", line)
                require(len(urls) == 1, f"Invalid active repository line in {file.name}")
                url = urls[0]
                official = (url.startswith("https://downloads.openwrt.org/releases/25.12.5/") and
                            ("mediatek/filogic" in url or common.ARCH in url))
                require(official or url == store, f"Unexpected repository: {url}")
                active.append(url)
    require(any("downloads.openwrt.org/releases/25.12.5/" in url for url in active), "Missing native distribution repositories")
    require((root / "etc/apk/keys/public-key.pem").is_file(), "Missing native package trust key")
    return {"software_repositories": sources, "active_software_repositories": active,
            "third_party_store_repository": store if store in active else None,
            "remote_store_and_kmod_compatibility": "not established; native signatures/architecture/ABI checks remain enforced"}


def artifact_check(tree):
    config = config_check(tree)
    target = tree / "bin/targets/mediatek/filogic"
    images = [p for p in tree.glob("bin/targets/**/*sysupgrade*") if p.is_file() and not p.name.endswith(".json")]
    require(len(images) == 1 and images[0].parent == target and images[0].name.endswith(common.DEVICE + "-squashfs-sysupgrade.bin"),
            "Expected exactly one native eMMC sysupgrade image")
    image = images[0]
    tar = common.check_tar(image.read_bytes())
    profiles = json.loads((target / "profiles.json").read_text())
    require(set(profiles["profiles"]) == {common.DEVICE}, "Unexpected artifact profile(s)")
    profile = profiles["profiles"][common.DEVICE]
    entry = [entry for entry in profile["images"] if entry["type"] == "sysupgrade"]
    require(len(entry) == 1 and entry[0]["sha256"] == digest(image) and entry[0]["size"] == image.stat().st_size,
            "Profile image hash/size differs from actual file")
    versions = dict(line.split(" - ", 1) for line in next(target.glob("*.manifest")).read_text().splitlines() if line)
    roots = list(tree.glob("build_dir/target-*/root-mediatek"))
    require(len(roots) == 1, "Ambiguous final rootfs")
    root = root_check(roots[0], versions, config["package_mapping"])
    kernels = list(tree.glob("build_dir/target-*/linux-mediatek_filogic/linux-*/.config"))
    require(len(kernels) == 1, "Missing final Linux kernel configuration")
    for key in common.BUILTIN_DRIVERS:
        require(common.read_config(kernels[0]).get(key) == "y", f"Missing compiled builtin driver {key}")
    metadata_file = target / "rax-vendor-fwtool.json"
    subprocess.run([str(tree / "staging_dir/host/bin/fwtool"), "-i", str(metadata_file), str(image)], check=True)
    embedded = json.loads(metadata_file.read_text())
    require(common.BOARD in embedded.get("new_supported_devices", embedded.get("supported_devices", [])), "Wrong embedded model")
    require(embedded["version"]["version"] == pins()["OPENWRT_VERSION"], "Wrong embedded release")
    return {"status": "passed", "device": common.DEVICE, "image": image.name, "sha256": digest(image),
            "image_size_bytes": image.stat().st_size, "build_image_limit_bytes": None,
            "actual_router_partition_limit_bytes": None, "writable_overlay_bytes": None,
            "tar": tar, "embedded_metadata": embedded, "rootfs_path": str(roots[0].relative_to(tree)),
            "kernel_config_path": str(kernels[0].relative_to(tree)), "package_count": len(versions),
            "openclash_version": versions["luci-app-openclash"], "core_files": [CORE],
            "candidate_firmware": True, "safe_to_flash_confirmed": False, "game_latency_fix_verified": False,
            "hardware_validation": "pending", "proxy_runtime_validation": "pending", **root}


def check_openwrt_changes(tree):
    base = REPO / common.PROFILE_DIR / "patches"
    patches = [base / "apk-package-signing.patch", base / "kwrt-emmc-layout.patch",
               PROFILE / "patches/libnftnl-autoreconf.patch"]
    # git diff orders files by path. Compare every changed line, including the
    # one explicit build-recipe fix, without relaxing the base device review.
    blocks = []
    for file in patches:
        blocks.extend(part for part in re.split(r"(?=^diff --git )", file.read_text().strip(), flags=re.M) if part)
    reviewed = "\n".join(part.strip() for part in sorted(blocks))
    actual = common.command("git", "-C", str(tree), "diff", "HEAD", "--no-ext-diff", "--binary", "--unified=0")
    require(actual == reviewed, "OpenWrt changes differ from the reviewed device, APK-signing and libnftnl build patches")


def provenance(build, adaptation):
    lock = pins()
    # Additional source changes are explicit. No clean-tree requirement is
    # disabled to hide a compatibility patch.
    result = {"status": "passed", "kwrt": {"url": "https://github.com/jcaifly/Kwrt.git",
        "commit": common.command("git", "-C", str(REPO), "rev-parse", "HEAD"),
        "local_uncommitted_changes": bool(common.command("git", "-C", str(REPO), "status", "--porcelain"))}}
    for key, folder in (("OPENWRT", "openwrt"), ("PACKAGES", "openwrt/feeds/packages"),
                        ("LUCI", "openwrt/feeds/luci"), ("OPENCLASH", "openclash-feed"), ("VENDOR_FEED", "vendor-feed")):
        commit = common.command("git", "-C", str(build / folder), "rev-parse", "HEAD")
        require(commit == lock[key + "_COMMIT"], f"Actual {key} differs from source pins")
        result[{"OPENWRT": "openwrt", "PACKAGES": "packages", "LUCI": "luci", "OPENCLASH": "openclash", "VENDOR_FEED": "vendor_feed"}[key]] = {"url": lock[key + "_URL"], "commit": commit}
    check_openwrt_changes(build / "openwrt")
    require(not common.command("git", "-C", str(build / "openwrt/feeds/luci"), "status", "--porcelain", "--untracked-files=no"),
            "Unreviewed LuCI source changes")
    clash = build / "openclash-feed"
    require(common.command("git", "-C", str(clash), "diff", "--numstat") ==
            "1\t0\tluci-app-openclash/Makefile\n4\t4\tluci-app-openclash/root/usr/share/openclash/openclash_update.sh",
            "OpenClash differs from reviewed host-build and APK-verification patches")
    common.check_core_files(clash / "luci-app-openclash/root")
    source_report = json.loads(adaptation.read_text())
    for relative, change in source_report["changes"].items():
        file = build / relative
        require(file.resolve().is_relative_to(build.resolve()), "Adapted source path leaves this build")
        require((digest(file) if file.is_file() else None) == change["after_sha256"], f"Adapted source was changed: {relative}")
    changed = set(common.command("git", "-C", str(build / "vendor-feed"), "diff", "--name-only").splitlines())
    expected = {relative.removeprefix("vendor-feed/") for relative in source_report["changes"] if relative.startswith("vendor-feed/")}
    require(changed == expected, f"Unexpected vendor recipe edits: {sorted(changed ^ expected)}")
    changed = set(common.command("git", "-C", str(build / "openwrt/feeds/packages"), "diff", "--name-only").splitlines())
    expected = {relative.removeprefix("openwrt/feeds/packages/") for relative in source_report["changes"] if relative.startswith("openwrt/feeds/packages/")}
    require(changed == expected, f"Unexpected official package recipe edits: {sorted(changed ^ expected)}")
    result["vendor_feed"] = {"url": lock["VENDOR_FEED_URL"], "commit": lock["VENDOR_FEED_COMMIT"]}
    result["vendor_reference"] = {"url": lock["VENDOR_REFERENCE_URL"], "sha256": lock["VENDOR_REFERENCE_SHA256"],
                                  "package_count": 375, "inventory_sha256": digest(PROFILE / "vendor-packages.manifest")}
    result["mihomo"] = {"version": lock["MIHOMO_VERSION"], "url": lock["MIHOMO_URL"],
                        "gzip_sha256": lock["MIHOMO_GZIP_SHA256"], "binary_sha256": lock["MIHOMO_BINARY_SHA256"],
                        "prebuilt_official_arm64": True, "core_in_firmware": True}
    result["openclash"].update(version=lock["OPENCLASH_VERSION"] + "-" + lock["OPENCLASH_RELEASE"], core_included_in_plugin_source=False)
    result["openwrt"].update(version=lock["OPENWRT_VERSION"], tag=lock["OPENWRT_TAG"])
    result["source_adaptations"] = source_report
    result["vendor_submodules"] = {name: value["submodules"] for name, value in
                                   json.loads((PROFILE / "source-hashes.json").read_text()).items() if value.get("submodules")}
    result["fullcone_support"] = {"url": lock["FULLCONE_SUPPORT_URL"], "commit": lock["FULLCONE_SUPPORT_COMMIT"],
                                  "patch_sha256": {file.name: digest(file) for file in sorted((PROFILE / "patches").glob("*.patch"))},
                                  "default_fullcone_rules_added": False}
    result["local_packages"] = {str(file.relative_to(PROFILE)): digest(file) for file in sorted((PROFILE / "packages").rglob("*")) if file.is_file()}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("map", "config", "artifact", "core", "provenance", "versions", "archives"))
    parser.add_argument("path", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        if args.mode == "map":
            result = {"status": "passed", "packages": create_config(args.path, args.path / ".config")}
        elif args.mode == "provenance":
            result = provenance(args.path, args.output.parent / "source-adaptation.json")
        else:
            result = {"config": config_check, "artifact": artifact_check, "core": core_check,
                      "versions": package_version_check, "archives": source_archive_check}[args.mode](args.path)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(f"vendor {args.mode}: passed; report: {args.output}", flush=True)
    except (ValueError, OSError, KeyError, IndexError, subprocess.CalledProcessError, tarfile.TarError) as error:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False, indent=2) + "\n")
        if os.getenv("GITHUB_ACTIONS") == "true":
            notice = str(error).replace("%", "%25").replace("\n", "%0A").replace("\r", "%0D")
            print("::error title=RAX3000M vendor validation::" + notice, flush=True)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
