"""Exercise corruption, wrong target and unsafe defaults without a real proxy core."""

import importlib.util
import gzip
from pathlib import Path
import struct
import tempfile
import unittest
import zlib
import hashlib


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

    base = tree({"compatible": string(check.BOARD)}, [
        ("chosen", {"bootargs-override": string("root=/dev/fit0 rootwait")}, [])])
    emmc = tree({"compatible": string(check.BOARD)}, [
        ("production", {"partname": string("production")}, []),
        ("factory", {"partname": string("factory")}, [])])
    nand = tree({"compatible": string(check.BOARD)}, [])
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


if __name__ == "__main__":
    unittest.main()
