#!/usr/bin/env python3
"""Apply deterministic compatibility changes only in the independent build tree."""

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

spec = importlib.util.spec_from_file_location("vendor", Path(__file__).with_name("rax3000m-vendor.py"))
vendor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vendor)


def git_package_version(text):
    original = re.search(r"^PKG_VERSION:=([^\n]+)$", text, re.M)
    if original:
        return original[1]
    date = re.search(r"^PKG_SOURCE_DATE:=([^\n]+)$", text, re.M)[1]
    commit = re.search(r"^PKG_SOURCE_VERSION:=(\w+)$", text, re.M)[1]
    # Match include/download.mk: Git snapshot dates use dots, not hyphens.
    return date.replace("-", ".") + "~" + commit[:8]


def archive_recipe(text, source, url, sha, version=None):
    text = re.sub(r"^PKG_(?:SOURCE_PROTO|SOURCE_URL|SOURCE_DATE|SOURCE_VERSION|MIRROR_HASH|SOURCE|HASH|BUILD_DIR):=.*\n", "", text, flags=re.M)
    if version:
        text = re.sub(r"^PKG_VERSION:=.*\n", "", text, flags=re.M)
    upstream = re.search(r"codeload.github.com/[^/]+/([^/]+)/tar.gz/(\w+)$", url)
    vendor.require(upstream is not None, "Expected a pinned upstream Git archive")
    root = "$(KERNEL_BUILD_DIR)" if "include $(INCLUDE_DIR)/kernel.mk" in text else "$(BUILD_DIR)"
    insertion = (f"PKG_VERSION:={version}\n" if version else "") + f"PKG_SOURCE:={source}\nPKG_SOURCE_URL:={url}?\nPKG_HASH:={sha}\nPKG_BUILD_DIR:={root}/{upstream[1]}-{upstream[2]}\n"
    return text.replace("include $(INCLUDE_DIR)/package.mk", insertion + "\ninclude $(INCLUDE_DIR)/package.mk", 1)


def submodule_recipe(text, package, modules):
    downloads, prepare = [], ["define Build/Prepare", "\t$(call Build/Prepare/Default)"]
    for path, source in sorted(modules.items()):
        vendor.require(re.fullmatch(r"[\w-]+", path) is not None, "Unexpected submodule build path")
        name = package + "-" + path
        downloads.append(f"define Download/{name}\n  FILE:={source['local_filename']}\n"
                         f"  URL:={source['url']}?\n  HASH:={source['sha256']}\nendef\n"
                         f"$(eval $(call Download,{name}))\n")
        prepare.extend([f"\t$(INSTALL_DIR) $(PKG_BUILD_DIR)/{path}",
                        f"\t$(TAR) -xzf $(DL_DIR)/{source['local_filename']} -C $(PKG_BUILD_DIR)/{path} --strip-components=1"])
    prepare.append("endef\n")
    insertion = "\n" + "\n".join(downloads + ["\n".join(prepare)])
    return text.replace("include $(INCLUDE_DIR)/package.mk\n", "include $(INCLUDE_DIR)/package.mk\n" + insertion, 1)


def adapt(build):
    tree, feed = build / "openwrt", build / "vendor-feed"
    profile = vendor.PROFILE
    hashes = json.loads((profile / "source-hashes.json").read_text())
    changes = {}
    for name, source in hashes.items():
        file = feed / name / "Makefile"
        before = file.read_bytes()
        text = before.decode()
        if name == "chinadns-ng":
            start, end = text.index("ifeq ($(ARCH),aarch64)"), text.index("PKG_SOURCE:=")
            text = text[:start] + "PKG_ARCH:=chinadns-ng+wolfssl_noasm@aarch64-linux-musl@generic+v8a@fast+lto\n" + text[end:]
            text = text.replace("include $(INCLUDE_DIR)/package.mk", f"PKG_HASH:={source['sha256']}\n\ninclude $(INCLUDE_DIR)/package.mk", 1)
        elif name in ("fullconenat-nft", "simple-obfs", "tcping"):
            commit = re.search(r"^PKG_SOURCE_VERSION:=(\w+)$", text, re.M)[1]
            text = archive_recipe(text, f"{name}-{commit}.tar.gz", source["url"], source["sha256"], git_package_version(text))
            if source.get("submodules"):
                text = submodule_recipe(text, name, source["submodules"])
        else:
            text, count = re.subn(r"^PKG_HASH:=skip$", "PKG_HASH:=" + source["sha256"], text, flags=re.M)
            vendor.require(count == 1, f"Unexpected hash declaration for {name}")
        vendor.require("PKG_HASH:=skip" not in text and "PKG_MIRROR_HASH:=skip" not in text, f"Unchecked download remains for {name}")
        file.write_text(text)
        changes[str(file.relative_to(build))] = {"before_sha256": hashlib.sha256(before).hexdigest(), "after_sha256": vendor.digest(file)}
    # The IPK-era recipe repeats the release in PKG_VERSION and PKG_RELEASE.
    # Keep the same fan code with a single native APK revision, 1.0.0-r3.
    file = feed / "luci-app-fan/Makefile"
    before = file.read_bytes()
    text, count = re.subn(r"^PKG_VERSION:=1\.0\.0-r3\nPKG_RELEASE:=1$",
                         "PKG_VERSION:=1.0.0\nPKG_RELEASE:=3", before.decode(), count=1, flags=re.M)
    vendor.require(count == 1, "Unexpected fan package version declaration")
    file.write_text(text)
    changes[str(file.relative_to(build))] = {"before_sha256": hashlib.sha256(before).hexdigest(), "after_sha256": vendor.digest(file)}
    # The profile has a fixed client set. Self-dependent package options create
    # Kconfig cycles on 25.12; express their actual required dependencies directly.
    file = feed / "luci-app-passwall/Makefile"
    before = file.read_bytes()
    text = before.decode()
    deps = "LUCI_DEPENDS:=" + " \\\n\t".join([
        "+coreutils +coreutils-base64 +coreutils-nohup +coreutils-timeout +curl",
        "+chinadns-ng +dns2socks +dnsmasq-full +ip-full +libuci-lua +lua +luci-compat +luci-lib-jsonc",
        "+microsocks +resolveip +tcping +lyaml +ipt2socks +geoview +haproxy",
        "+shadowsocksr-libev-ssr-local +shadowsocksr-libev-ssr-redir +simple-obfs-client +sing-box",
        "+kmod-nft-socket +kmod-nft-tproxy +kmod-nft-nat +kmod-nf-reject +kmod-nf-reject6",
    ]) + "\n"
    text, count = re.subn(r"^LUCI_DEPENDS:=.*?(?=\ndefine Package/)", lambda _: deps,
                         text, count=1, flags=re.M | re.S)
    vendor.require(count == 1, "Unexpected Passwall dependency declaration")
    text, count = re.subn(r"^define Package/\$\(PKG_NAME\)/config\n.*?^endef\n", "", text, count=1, flags=re.M | re.S)
    vendor.require(count == 1, "Unexpected Passwall build option menu")
    file.write_text(text)
    changes[str(file.relative_to(build))] = {"before_sha256": hashlib.sha256(before).hexdigest(), "after_sha256": vendor.digest(file)}
    # The vendor uses full sing-box. Removing an unselected tiny variant's
    # self-provide breaks another Kconfig cycle without removing any full feature.
    file = tree / "feeds/packages/net/sing-box/Makefile"
    before = file.read_bytes()
    text, count = re.subn(r"^\$\(eval \$\(call BuildPackage,sing-box-tiny\)\)\n?", "", before.decode(), count=1, flags=re.M)
    vendor.require(count == 1, "Unexpected official sing-box variant declaration")
    file.write_text(text)
    changes[str(file.relative_to(build))] = {"before_sha256": hashlib.sha256(before).hexdigest(), "after_sha256": vendor.digest(file)}
    # The feed's historical ELF helper is not the 25.12 build-host po2lmo API.
    for file in feed.glob("*/Makefile"):
        text = file.read_text()
        if "po2lmo " in text and "PKG_BUILD_DEPENDS" not in text:
            before = file.read_bytes()
            file.write_text(text.replace("include $(TOPDIR)/feeds/luci/luci.mk", "PKG_BUILD_DEPENDS:=luci-base/host\n\ninclude $(TOPDIR)/feeds/luci/luci.mk", 1))
            if file.read_bytes() != before:
                changes[str(file.relative_to(build))] = {"before_sha256": hashlib.sha256(before).hexdigest(), "after_sha256": vendor.digest(file)}
    # Legacy restoration hooks assume an IPK database and force dependency/checksum checks.
    for relative in ("luci-app-gpsysupgrade/root/etc/hotplug.d/online/50-opkg-restore",
                     "luci-app-gpsysupgrade/root/etc/profile.d/opkg.sh"):
        file = feed / relative
        if file.is_file():
            changes[str(file.relative_to(build))] = {"before_sha256": vendor.digest(file), "after_sha256": None}
            file.unlink()
    # Keep store signatures and ABI checks; no cross-architecture/untrusted forced installs.
    for file in (feed / "luci-app-store").rglob("*"):
        if not file.is_file() or file.name == "Makefile":
            continue
        before = file.read_bytes()
        try:
            text = before.decode()
        except UnicodeError:
            continue
        text = re.sub(r"(?<!\S)--(?:allow-untrusted|force-overwrite|force-broken-world)(?=\s|$)", "", text)
        if text.encode() != before:
            file.write_text(text)
            changes[str(file.relative_to(build))] = {"before_sha256": hashlib.sha256(before).hexdigest(), "after_sha256": vendor.digest(file)}
    # FullCone changes src/Makefile.am. Regenerate it with the explicit OpenWrt
    # autotools environment before configure, as in the pinned support upstream.
    file = tree / "package/libs/libnftnl/Makefile"
    before = file.read_bytes()
    subprocess.run(["git", "-C", str(tree), "apply", "--index", "--unidiff-zero",
                    str(profile / "patches/libnftnl-autoreconf.patch")], check=True)
    changes[str(file.relative_to(build))] = {"before_sha256": hashlib.sha256(before).hexdigest(), "after_sha256": vendor.digest(file)}
    locations = {
        "fullcone-libnftnl.patch": "package/libs/libnftnl/patches/001-rax-fullcone-expression.patch",
        "fullcone-nftables.patch": "package/network/utils/nftables/patches/002-rax-fullcone-expression.patch",
        "952-net-conntrack-events-support-multiple-registrant.patch": "target/linux/generic/hack-6.12/952-net-conntrack-events-support-multiple-registrant.patch",
        "001-firewall4-add-support-for-fullcone-nat.patch": "package/network/config/firewall4/patches/001-rax-fullcone-nat.patch",
    }
    for name, relative in locations.items():
        dest = tree / relative
        vendor.require(not dest.exists(), f"Refusing to replace an upstream patch: {relative}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(profile / "patches" / name, dest)
        changes[str(dest.relative_to(build))] = {"before_sha256": None, "after_sha256": vendor.digest(dest)}
    return {"status": "passed", "changes": changes, "reason": "source verification, native APK compatibility, fullcone package support"}


if __name__ == "__main__":
    result = adapt(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2) + "\n")
    print("Vendor source adaptation: passed", flush=True)
