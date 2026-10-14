import hashlib
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("vendor", Path(__file__).resolve().parents[1] / "rax3000m-vendor.py")
vendor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vendor)


class VendorMappingTests(unittest.TestCase):
    def test_real_inventory_contains_every_package(self):
        inventory = dict(vendor.inventory())
        self.assertEqual(len(inventory), 375)
        self.assertEqual(inventory["kernel"], "6.12.94~1-r1")
        self.assertIn("luci-app-passwall", inventory)
        self.assertNotIn("luci-app-openclash", inventory)

    def test_missing_package_cannot_be_silently_dropped(self):
        with patch.object(vendor, "metadata", return_value={}), patch.object(vendor, "inventory", return_value=[("unavailable-package", "1")]):
            with self.assertRaisesRegex(ValueError, "refusing to drop"):
                vendor.map_packages(Path("unused"))

    def test_abi_names_and_package_manager_are_explicitly_mapped(self):
        records = {"libubox": {"ABI-Version": "20260213", "Version": "1"}, "apk-mbedtls": {"Version": "3"}}
        rows = [("libubox20260213", "1"), ("opkg", "old"), ("kernel", "6.12.94~1-r1")]
        with patch.object(vendor, "metadata", return_value=records), patch.object(vendor, "inventory", return_value=rows):
            actual = vendor.map_packages(Path("unused"))
        self.assertEqual(actual[0]["symbol"], "libubox")
        self.assertEqual(actual[0]["runtime"], "libubox20260213")
        self.assertEqual(actual[1]["runtime"], "apk-mbedtls")
        self.assertIsNone(actual[2]["symbol"])

    def test_numeric_package_abi_separator(self):
        self.assertEqual(vendor.runtime_name("liblua5.4", {"ABI-Version": "5.4"}), "liblua5.4-5.4")


class CoreIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "core"
        self.data = bytearray(64)
        self.data[:6] = b"\x7fELF\x02\x01"
        struct.pack_into("<H", self.data, 18, 183)
        self.path.write_bytes(self.data)
        self.lock = {"MIHOMO_BINARY_SHA256": hashlib.sha256(self.data).hexdigest(), "MIHOMO_VERSION": "test",
                     "MIHOMO_URL": "https://example.invalid/core", "MIHOMO_GZIP_SHA256": "test"}

    def test_verified_arm64_header(self):
        with patch.object(vendor, "pins", return_value=self.lock):
            self.assertEqual(vendor.core_check(self.path)["architecture"], "AArch64")

    def test_tampered_payload_rejected(self):
        self.data[-1] = 1
        self.path.write_bytes(self.data)
        with patch.object(vendor, "pins", return_value=self.lock):
            with self.assertRaisesRegex(ValueError, "differs from the official pinned"):
                vendor.core_check(self.path)

    def test_wrong_architecture_rejected_even_with_matching_hash(self):
        struct.pack_into("<H", self.data, 18, 62)
        self.path.write_bytes(self.data)
        self.lock["MIHOMO_BINARY_SHA256"] = hashlib.sha256(self.data).hexdigest()
        with patch.object(vendor, "pins", return_value=self.lock):
            with self.assertRaisesRegex(ValueError, "not little-endian ARM64"):
                vendor.core_check(self.path)


if __name__ == "__main__":
    unittest.main()
