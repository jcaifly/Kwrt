"""Use the actual native APK tool to catch legacy vendor version failures."""

import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


scripts = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("adapt", scripts / "adapt-rax3000m-vendor.py")
adapt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapt)
vendor = adapt.vendor


class NativeVersionTests(unittest.TestCase):
    def setUp(self):
        self.apk = Path(os.environ.get("OPENWRT_APK", "/missing/native-apk"))
        self.assertTrue(self.apk.is_file(), "Set OPENWRT_APK to the verified native APK tool")
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.tree = Path(self.temporary.name)
        self.files = self.tree / "files"
        self.files.mkdir()
        (self.files / "fixture.txt").write_text("Harmless packaging fixture; no module or executable.\n")

    def pack(self, version):
        return subprocess.run([str(self.apk), "mkpkg", "--output", str(self.tree / "probe.apk"),
                               "--info", "name:version-probe", "--info", "version:" + version,
                               "--info", "arch:all", "--files", str(self.files)], capture_output=True, text=True)

    def check(self, records):
        (self.tree / ".config").write_text("".join(f"CONFIG_PACKAGE_{name}=y\n" for name in records))
        with patch.object(vendor, "metadata", return_value=records), \
                patch.dict(os.environ, {"OPENWRT_APK": str(self.apk)}):
            return vendor.package_version_check(self.tree)

    def test_actual_fullcone_packaging_failure_and_corrected_git_date(self):
        old = self.pack("6.12.94.2023-05-17~07d93b62-r1")
        self.assertEqual(old.returncode, 99, old.stderr)
        self.assertIn("package version is invalid", old.stderr)
        recipe = "PKG_SOURCE_DATE:=2023-05-17\nPKG_SOURCE_VERSION:=07d93b626ce5ea885cd16f9ab07fac3213c355d9\n"
        version = adapt.git_package_version(recipe)
        self.assertEqual(version, "2023.05.17~07d93b62")
        fixed = self.pack("6.12.94." + version + "-r1")
        self.assertEqual(fixed.returncode, 0, fixed.stderr)

    def test_duplicate_fan_revision_is_rejected_and_single_revision_packs(self):
        self.assertEqual(self.pack("1.0.0-r3-r1").returncode, 99)
        fixed = self.pack("1.0.0-r3")
        self.assertEqual(fixed.returncode, 0, fixed.stderr)

    def test_explicit_upstream_versions_are_preserved(self):
        for version in ("0.0.5", "0.3"):
            with self.subTest(version=version):
                recipe = f"PKG_VERSION:={version}\nPKG_SOURCE_DATE:=2020-07-04\nPKG_SOURCE_VERSION:=db9101834732\n"
                self.assertEqual(adapt.git_package_version(recipe), version)

    def test_invalid_kernel_template_suffix_is_not_deferred(self):
        with self.assertRaisesRegex(ValueError, "Native APK rejected.*kmod-nft-fullcone"):
            self.check({"kmod-nft-fullcone": {"Version": "<LINUX_VERSION>.2023-05-17~07d93b62-r1"}})

    def test_valid_templates_and_deferred_luci_are_reported_without_fake_abi(self):
        version = "<LINUX_VERSION>.2023.05.17~07d93b62-r1"
        records = {"fan": {"Version": "1.0.0-r3"}, "kmod-nft-fullcone": {"Version": version},
                   "luci-base": {"Version": "x", "Source-Makefile": "feeds/luci/modules/luci-base/Makefile"}}
        result = self.check(records)
        self.assertEqual(result["selected_package_count"], 3)
        self.assertEqual(result["literal_versions_checked"], 1)
        self.assertEqual(result["template_syntax_checked"], 1)
        self.assertEqual(result["deferred_luci_version_count"], 1)
        self.assertTrue(result["final_version_validation_pending"])
        self.assertFalse(result["actual_kernel_abi_verified"])
        self.assertEqual(records["kmod-nft-fullcone"]["Version"], version)

    def test_unknown_placeholder_cannot_silently_pass(self):
        with self.assertRaisesRegex(ValueError, "Unknown package version placeholder"):
            self.check({"probe": {"Version": "<UNKNOWN_VERSION>-r1"}})

    def test_invalid_concrete_version_names_the_failing_package(self):
        with self.assertRaisesRegex(ValueError, "Native APK rejected.*fan=1.0.0-r3-r1"):
            self.check({"fan": {"Version": "1.0.0-r3-r1"}})


if __name__ == "__main__":
    unittest.main()
