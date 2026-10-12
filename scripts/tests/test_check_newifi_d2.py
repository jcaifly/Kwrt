"""Exercise artifact validation with synthetic images, never real firmware."""

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


CHECKER_PATH = Path(__file__).resolve().parents[1] / "check-newifi-d2.py"
spec = importlib.util.spec_from_file_location("newifi_checker", CHECKER_PATH)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class ArtifactRootfsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="newifi-artifact-test-")
        self.addCleanup(self.temp.cleanup)
        self.tree = Path(self.temp.name)
        self.target = self.tree / "bin/targets/ramips/mt7621"
        self.target.mkdir(parents=True)
        self.image = self.target / f"test-{checker.DEVICE}-squashfs-sysupgrade.bin"
        self.image.write_bytes(b"Synthetic test fixture, not a firmware image.")
        self.versions = {name: "1.0-r1" for name in checker.REQUIRED}
        self.versions["luci-app-openclash"] = "0.47.156-r8"
        self.manifest = self.target / "test.manifest"
        self.manifest.write_text("".join(
            f"{name} - {version}\n" for name, version in sorted(self.versions.items())))
        self.profile = {
            "target": "ramips/mt7621",
            "profiles": {
                checker.DEVICE: {
                    "supported_devices": [checker.BOARD],
                    "file_size_limits": {"image": checker.LIMIT},
                    "images": [{
                        "name": self.image.name,
                        "type": "sysupgrade",
                        "filesystem": "squashfs",
                        "size": self.image.stat().st_size,
                        "sha256": hashlib.sha256(self.image.read_bytes()).hexdigest(),
                    }],
                },
            },
        }
        (self.target / "profiles.json").write_text(json.dumps(self.profile))
        packageinfo = self.tree / "tmp/.packageinfo"
        packageinfo.parent.mkdir()
        packageinfo.write_text("Package: luci-app-openclash\nVersion: 0.47.156-r8\n@@\n")

        # This payload staging directory existed in the failed Actions run, but
        # contains neither the installed APK database nor our rootfs overlay.
        self.staging = self.tree / "staging_dir/target-mipsel_24kc_musl/root-ramips"
        self.staging.mkdir(parents=True)
        self.root = self.tree / "build_dir/target-mipsel_24kc_musl/root-ramips"
        self.database = self.root / "lib/apk/db/installed"
        self.database.parent.mkdir(parents=True)
        self.write_database(self.database, self.versions)
        config = self.root / "etc/config/openclash"
        config.parent.mkdir(parents=True)
        config.write_text("config openclash 'config'\n\toption enable '0'\n")
        startup = self.root / "etc/uci-defaults/zz-newifi-d2-openclash"
        startup.parent.mkdir()
        startup.write_text("#!/bin/sh\nuci set openclash.config.enable='0'\n"
                           "/etc/init.d/openclash disable\n")

        # Configuration validation has its own real-source checks. Only replace
        # it and native fwtool decoding; all filesystem/package checks run here.
        self.addCleanup(patch.stopall)
        patch.object(checker, "check_config", return_value={"status": "passed"}).start()
        patch.object(checker.subprocess, "run", side_effect=self.decode_metadata).start()

    @staticmethod
    def write_database(path, versions):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(f"P:{name}\nV:{version}\n\n"
                                for name, version in sorted(versions.items())))

    @staticmethod
    def decode_metadata(args, **_kwargs):
        Path(args[2]).write_text(json.dumps({
            "supported_devices": [checker.BOARD],
            "version": {"target": "ramips/mt7621"},
        }))

    def test_valid_final_rootfs_with_empty_payload_staging(self):
        report = checker.check_artifact(self.tree)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["installed_database"],
                         "build_dir/target-mipsel_24kc_musl/root-ramips/lib/apk/db/installed")
        self.assertEqual(report["package_count"], len(self.versions))

    def test_staging_database_cannot_replace_missing_final_database(self):
        self.database.unlink()
        self.write_database(self.staging / "lib/apk/db/installed", self.versions)
        with self.assertRaisesRegex(ValueError, "Missing final APK package database"):
            checker.check_artifact(self.tree)

    def test_final_database_must_match_manifest_versions(self):
        versions = dict(self.versions, ruby="2.0-r1")
        self.write_database(self.database, versions)
        with self.assertRaisesRegex(ValueError, "package database versions differ"):
            checker.check_artifact(self.tree)

    def test_core_in_final_rootfs_is_rejected(self):
        core = self.root / "etc/openclash/core/clash_meta"
        core.parent.mkdir(parents=True)
        core.write_text("Test marker only, not an executable or downloaded core.")
        with self.assertRaisesRegex(ValueError, "Preinstalled core path"):
            checker.check_artifact(self.tree)

    def test_enabled_proxy_in_final_rootfs_is_rejected(self):
        (self.root / "etc/config/openclash").write_text("option enable '1'\n")
        with self.assertRaisesRegex(ValueError, "Proxy enabled by default"):
            checker.check_artifact(self.tree)

    def test_automatic_core_download_in_final_rootfs_is_rejected(self):
        startup = self.root / "etc/uci-defaults/zz-newifi-d2-openclash"
        startup.write_text(startup.read_text() + "curl https://example.invalid/core\n")
        with self.assertRaisesRegex(ValueError, "Automatic first-boot core download"):
            checker.check_artifact(self.tree)

    def test_multiple_final_rootfs_directories_are_rejected(self):
        (self.tree / "build_dir/target-other/root-ramips").mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "Expected one assembled rootfs"):
            checker.check_artifact(self.tree)


if __name__ == "__main__":
    unittest.main()
