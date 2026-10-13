"""Exercise corruption, wrong target and unsafe defaults without a real proxy core."""

import importlib.util
import gzip
import io
import lzma
from pathlib import Path
import struct
import tempfile
import unittest
import zlib
import hashlib
import subprocess
import tarfile


spec = importlib.util.spec_from_file_location("check_rax3000m", Path(__file__).parents[1] / "check-rax3000m.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def string(value):
    return value.encode() + b"\0"


def fdt(nodes, properties=None):
    strings, names = bytearray(), {}
    structure = bytearray()

    def word(value):
        structure.extend(struct.pack(">I", value))

    def emit(name, properties, children):
        word(1)
        structure.extend(string(name))
        structure.extend(b"\0" * (-len(structure) % 4))
        for key, value in properties.items():
            if key not in names:
                names[key] = len(strings)
                strings.extend(string(key))
            word(3)
            word(len(value))
            word(names[key])
            structure.extend(value)
            structure.extend(b"\0" * (-len(structure) % 4))
        for child in children:
            emit(*child)
        word(2)

    emit("", properties or {}, nodes)
    word(9)
    offset = 56
    size = offset + len(structure) + len(strings)
    header = struct.pack(">10I", 0xD00DFEED, size, offset, offset + len(structure), 40, 17, 16, 0,
                         len(strings), len(structure))
    return header + b"\0" * 16 + structure + strings


def fit_fixture():
    # Build real flattened trees using dtc-compatible tokens, without any executable payload.
    def tree(properties, children):
        return fdt(children, properties)

    base = tree({"compatible": string(check.UNIFIED_BOARD)}, [
        ("chosen", {"bootargs-override": string("root=/dev/fit0 rootwait")}, [])])
    emmc = tree({"compatible": string(check.UNIFIED_BOARD)}, [
        ("production", {"partname": string("production")}, []),
        ("factory", {"partname": string("factory")}, [])])
    nand = tree({"compatible": string(check.UNIFIED_BOARD)}, [])
    root = bytearray(96)
    root[:4] = b"hsqs"
    struct.pack_into("<H", root, 28, 4)
    struct.pack_into("<Q", root, 40, 96)
    linux_header = bytearray(64)
    linux_header[56:60] = b"ARM\x64"
    payloads = {"kernel-1": gzip.compress(linux_header, mtime=0), "fdt-1": base,
                "fdt-mt7981b-cmcc-rax3000m-emmc": emmc,
                "fdt-mt7981b-cmcc-rax3000m-nand": nand, "rootfs-1": bytes(root)}
    images, offsets = [], {}
    offset = 4096
    for name, payload in payloads.items():
        offsets[name] = offset
        images.append((name, {"arch": string("arm64"), "data-position": struct.pack(">I", offset),
                              "data-size": struct.pack(">I", len(payload))}, [
            ("hash-1", {"algo": string("crc32"), "value": struct.pack(">I", zlib.crc32(payload))}, []),
            ("hash-2", {"algo": string("sha1"), "value": hashlib.sha1(payload).digest()}, [])]))
        offset += len(payload)
    configurations = [
        ("config-1", {"kernel": string("kernel-1"), "fdt": string("fdt-1"), "loadables": string("rootfs-1")}, []),
        ("mt7981b-cmcc-rax3000m-emmc", {"fdt": string("fdt-mt7981b-cmcc-rax3000m-emmc")}, []),
        ("mt7981b-cmcc-rax3000m-nand", {"fdt": string("fdt-mt7981b-cmcc-rax3000m-nand")}, [])]
    header = tree({}, [("images", {}, images), ("configurations", {"default": string("config-1")}, configurations)])
    return header + b"\0" * (4096 - len(header)) + b"".join(payloads.values()), offsets


class FitChecks(unittest.TestCase):
    def test_official_shape_including_both_overlays(self):
        data, _ = fit_fixture()
        self.assertEqual(check.check_fit(data)["status"], "passed")

    def test_payload_corruption_fails(self):
        data, offsets = fit_fixture()
        damaged = bytearray(data)
        damaged[offsets["rootfs-1"] + 50] ^= 1
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            check.check_fit(damaged)

    def test_external_payload_bounds(self):
        data, _ = fit_fixture()
        with self.assertRaisesRegex(ValueError, "payload exceeds image"):
            check.check_fit(data[:-50])

    def test_wrong_architecture(self):
        data, _ = fit_fixture()
        with self.assertRaisesRegex(ValueError, "architecture"):
            check.check_fit(data.replace(b"arm64\0", b"mipsl\0"))

    def test_missing_emmc_configuration(self):
        data, _ = fit_fixture()
        with self.assertRaises(KeyError):
            check.check_fit(data.replace(b"mt7981b-cmcc-rax3000m-emmc\0", b"mt7981b-cmcc-rax3000m-xxxx\0", 1))

    def test_truncated_fdt(self):
        with self.assertRaisesRegex(ValueError, "header"):
            check.parse_fdt(b"\xd0\x0d\xfe\xed")


class PackageAndCoreChecks(unittest.TestCase):
    def test_excluded_apps_and_dependency_exceptions(self):
        for name in ("mihomo", "luci-app-ttyd", "nlbwmon", "btop", "mosdns", "luci-app-turboacc"):
            self.assertTrue(check.unwanted(name), name)
        for name in ("luci-app-openclash", "luci-app-firewall", "luci-app-package-manager", "kmod-mt7915e"):
            self.assertFalse(check.unwanted(name), name)

    def test_core_directory_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = root / "etc/openclash/core/clash_meta"
            payload.parent.mkdir(parents=True)
            payload.write_bytes(b"synthetic fixture only")
            with self.assertRaisesRegex(ValueError, "Bundled core"):
                check.check_core_files(root)

    def test_wrong_userspace_elf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            header = bytearray(20)
            header[:6] = b"\x7fELF\x02\x01"
            struct.pack_into("<H", header, 18, 62)  # x86-64 rather than AArch64
            (root / "binary").write_bytes(header)
            with self.assertRaisesRegex(ValueError, "ELF architecture"):
                check.check_core_files(root)

    def test_database_required_in_installed_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, "installed APK database"):
                check.installed_records(root)

    def test_dependency_guards(self):
        config = {"PACKAGE_firewall4": "y", "IPV6": "y"}
        value = "+PACKAGE_firewall4:nftables-json +!PACKAGE_firewall4:iptables +IPV6&&PACKAGE_firewall4:kmod-nft-tproxy"
        self.assertEqual(list(check.dependency_names(value, config)), ["nftables-json", "kmod-nft-tproxy"])


class ApkRepositoryChecks(unittest.TestCase):
    def check_files(self, custom, dist=None):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            feeds = root / "etc/apk/repositories.d"
            feeds.mkdir(parents=True)
            (feeds / "customfeeds.list").write_text(custom)
            if dist is not None:
                (feeds / "distfeeds.list").write_text(dist)
            return check.check_apk_sources(root)

    def test_official_commented_example_is_not_an_active_feed(self):
        custom = "# add your custom package feeds here\n#\n# http://www.example.com/path/to/files/packages.adb\n"
        official = "https://downloads.openwrt.org/releases/25.12.5/targets/mediatek/filogic/packages/packages.adb\n"
        report = self.check_files(custom, official)
        self.assertEqual(report["active_software_repositories"], [official.strip()])
        self.assertIn("www.example.com", report["software_repositories"]["etc/apk/repositories.d/customfeeds.list"])

    def test_whitespace_before_disabled_feed_is_ignored(self):
        official = "https://downloads.openwrt.org/releases/25.12.5/packages/aarch64_cortex-a53/base/packages.adb\n"
        self.assertEqual(len(self.check_files("\n  # https://example.com/packages.adb\n", official)
                             ["active_software_repositories"]), 1)

    def test_same_example_url_enabled_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unexpected active APK feed"):
            self.check_files("http://www.example.com/path/to/files/packages.adb\n")

    def test_wrong_release_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unexpected active APK feed"):
            self.check_files("https://downloads.openwrt.org/releases/24.10.5/packages/aarch64_cortex-a53/base/packages.adb\n")

    def test_wrong_architecture_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "target/architecture"):
            self.check_files("https://downloads.openwrt.org/releases/25.12.5/packages/mipsel_24kc/base/packages.adb\n")

    def test_nonexistent_openclash_feed_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Nonexistent OpenClash"):
            self.check_files("https://downloads.openwrt.org/releases/25.12.5/packages/aarch64_cortex-a53/openclash/packages.adb\n")

    def test_comment_only_repositories_cannot_pass(self):
        with self.assertRaisesRegex(ValueError, "Missing active software repositories"):
            self.check_files("# https://downloads.openwrt.org/releases/25.12.5/packages/aarch64_cortex-a53/base/packages.adb\n")

    def test_unrecognized_active_repository_line_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Invalid active APK feed"):
            self.check_files("file:///tmp/packages\n")


def tar_fixture(board=check.BOARD, bootargs="root=PARTLABEL=rootfs rootwait", symlink=False):
    dt = fdt([
        ("chosen", {"bootargs": string(bootargs)}, []),
        ("mmc@11230000", {"status": string("okay")}, [
            ("factory", {"partname": string("factory")}, [])])], {"compatible": string(board)})
    header = bytearray(64)
    header[56:60] = b"ARM\x64"
    images = []
    for name, payload, kind in (("kernel-1", lzma.compress(header, format=lzma.FORMAT_ALONE), "kernel"),
                                ("fdt-1", dt, "flat_dt")):
        images.append((name, {"arch": string("arm64"), "type": string(kind), "data": payload,
                              "compression": string("lzma" if kind == "kernel" else "none")}, [
            ("hash-1", {"algo": string("crc32"), "value": struct.pack(">I", zlib.crc32(payload))}, []),
            ("hash-2", {"algo": string("sha1"), "value": hashlib.sha1(payload).digest()}, [])]))
    kernel = fdt([( "images", {}, images), ("configurations", {"default": string("config-1")}, [
        ("config-1", {"kernel": string("kernel-1"), "fdt": string("fdt-1")}, [])])])
    root = bytearray(96)
    root[:4] = b"hsqs"
    struct.pack_into("<H", root, 28, 4)
    struct.pack_into("<Q", root, 40, 96)
    stream = io.BytesIO()
    folder = "sysupgrade-" + check.DEVICE
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.GNU_FORMAT) as archive:
        directory = tarfile.TarInfo(folder + "/")
        directory.type = tarfile.DIRTYPE
        archive.addfile(directory)
        for name, payload in (("CONTROL", ("BOARD=" + check.DEVICE + "\n").encode()),
                               ("kernel", kernel), ("root", bytes(root))):
            member = tarfile.TarInfo(folder + "/" + name)
            member.size = len(payload)
            if symlink and name == "root":
                member.type, member.linkname = tarfile.SYMTYPE, "/etc/passwd"
                member.size = 0
                archive.addfile(member)
            else:
                archive.addfile(member, io.BytesIO(payload))
    return stream.getvalue()


class TarChecks(unittest.TestCase):
    def test_native_tar_and_minimum_partition_sizes(self):
        report = check.check_tar(tar_fixture())
        self.assertEqual(report["board"], check.BOARD)
        self.assertEqual(report["minimum_root_partition_bytes"], 65536 + 4096)

    def test_unified_identity_is_rejected_for_legacy_layout(self):
        with self.assertRaisesRegex(ValueError, "identity"):
            check.check_tar(tar_fixture(board=check.UNIFIED_BOARD))

    def test_fit_root_is_rejected_for_legacy_layout(self):
        with self.assertRaisesRegex(ValueError, "root/boot"):
            check.check_tar(tar_fixture(bootargs="root=/dev/fit0 rootwait"))

    def test_symlink_member_rejected(self):
        with self.assertRaisesRegex(ValueError, "special files"):
            check.check_tar(tar_fixture(symlink=True))

    def test_kernel_corruption_is_rejected(self):
        data = bytearray(tar_fixture())
        location = data.index(b"ARM64") if b"ARM64" in data else data.index(b"cmcc,rax3000m-emmc")
        data[location] ^= 1
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            check.check_tar(data)


class UpgradeCapacityChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        patch = (Path(__file__).parents[2] / check.PROFILE_DIR / "patches/kwrt-emmc-layout.patch").read_text()
        block = patch.split("diff --git a/target/linux/mediatek/filogic/base-files/lib/upgrade/rax3000m-emmc.sh", 1)[1]
        block = block.split("diff --git", 1)[0]
        cls.helper = "\n".join(line[1:] for line in block.splitlines() if line.startswith("+") and not line.startswith("+++")) + "\n"

    def run_guard(self, kernel_sectors, root_sectors, backup_bytes=0):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "helper.sh").write_text(self.helper)
            (directory / "image.bin").write_bytes(tar_fixture())
            (directory / "backup.tar.gz").write_bytes(b"x" * backup_bytes)
            # Mock hardware I/O only; the actual shell guard reads and measures a real TAR.
            runner = '''. "$1/helper.sh"
rax3000m_emmc_partition() { case "$1" in kernel) echo mmcblk0p4;; rootfs) echo mmcblk0p5;; esac; }
cat() { case "$1" in */mmcblk0p4/size) echo "$KERNEL_SECTORS";; */mmcblk0p5/size) echo "$ROOT_SECTORS";; *) command cat "$@";; esac; }
[() { if command [ "$1" = -b ]; then return 0; else command [ "$@"; fi; }
export UPGRADE_BACKUP=""
if command [ "$BACKUP_BYTES" -gt 0 ]; then export UPGRADE_BACKUP="$1/backup.tar.gz"; fi
rax3000m_emmc_check_image "$1/image.bin"
'''
            import os
            environment = dict(os.environ, KERNEL_SECTORS=str(kernel_sectors), ROOT_SECTORS=str(root_sectors),
                               BACKUP_BYTES=str(backup_bytes))
            return subprocess.run(["bash", "-c", runner, "test", str(directory)], env=environment,
                                  text=True, capture_output=True)

    def test_fitting_existing_partitions(self):
        result = self.run_guard(4096, 4096)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_oversized_kernel_rejected(self):
        self.assertNotEqual(self.run_guard(1, 4096).returncode, 0)

    def test_overlay_marker_must_fit(self):
        self.assertNotEqual(self.run_guard(4096, 128).returncode, 0)

    def test_actual_config_backup_must_fit(self):
        self.assertNotEqual(self.run_guard(4096, 136, 65536).returncode, 0)

    def test_invalid_partition_capacity_rejected(self):
        self.assertNotEqual(self.run_guard("invalid", 4096).returncode, 0)


if __name__ == "__main__":
    unittest.main()
