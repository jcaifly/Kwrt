"""Reject wrong ABI, replacement content and untrusted signatures before delivery."""

import base64
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


spec = importlib.util.spec_from_file_location(
    "collect_rax3000m_packages", Path(__file__).parents[1] / "collect-rax3000m-packages.py")
packages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packages)
KERNEL = "6.12.94~9127b7d13b17ee62d508f2f4aaa555f4-r1"


class MetadataChecks(unittest.TestCase):
    def setUp(self):
        self.info = {"name": "kmod-example", "version": "6.12.94-r1", "arch": packages.check.ARCH,
                     "hashes": "12" * 32, "depends": ["kernel=" + KERNEL]}
        self.record = {"P": self.info["name"], "V": self.info["version"], "A": self.info["arch"],
                       "C": "Q1" + base64.b64encode(bytes.fromhex("12" * 20)).decode(),
                       "D": "kernel=" + KERNEL}

    def test_wrong_kernel_abi_even_with_matching_image_record(self):
        self.info["depends"] = ["kernel=6.12.94~11111111111111111111111111111111-r1"]
        self.record["D"] = self.info["depends"][0]
        with self.assertRaises(ValueError):
            packages.check_record(self.info, self.record, KERNEL)

    def test_wrong_architecture_even_if_record_matches(self):
        self.info["arch"] = self.record["A"] = "mipsel_24kc"
        with self.assertRaises(ValueError):
            packages.check_record(self.info, self.record, KERNEL)

    def test_same_name_and_version_with_other_content(self):
        self.info["hashes"] = "ab" * 32
        with self.assertRaises(ValueError):
            packages.check_record(self.info, self.record, KERNEL)

    def test_short_index_identity_is_rejected(self):
        self.info["hashes"] = "12" * 20
        with self.assertRaises(ValueError):
            packages.check_record(self.info, self.record, KERNEL)

    def test_dependency_change_is_rejected(self):
        self.info["depends"].append("new-library")
        with self.assertRaises(ValueError):
            packages.check_record(self.info, self.record, KERNEL)


class NativeSignedRepositoryChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.apk, cls.openssl = os.getenv("OPENWRT_APK"), os.getenv("OPENWRT_OPENSSL")
        if not cls.apk or not cls.openssl:
            raise unittest.SkipTest("Native OpenWrt tools are checked after compilation")

    def command(self, *args):
        return subprocess.check_output([str(arg) for arg in args], stderr=subprocess.STDOUT, text=True)

    def make_package(self, name, version, key=None):
        destination = self.bin / f"{name}-{version}.apk"
        files = self.files if name == "probe" else self.tree / "empty-fixture-files"
        files.mkdir(exist_ok=True)
        args = [self.apk, "mkpkg", "--sign-key", key or self.private,
                "--info", "name:" + name, "--info", "version:" + version,
                "--info", "arch:" + packages.check.ARCH, "--files", files]
        if name == "probe":
            args.extend(["--info", "depends:kernel=" + KERNEL])
        self.command(*args, "--output", destination)
        link = self.sources / destination.name
        if not link.exists():
            link.symlink_to(destination)
        return destination

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="rax3000m-signed-packages-")
        self.addCleanup(self.temporary.cleanup)
        self.tree = Path(self.temporary.name) / "openwrt"
        self.bin = self.tree / "bin/packages"
        self.sources = self.tree / "staging_dir/packages/mediatek"
        self.files = self.tree / "fixture-files"
        for directory in (self.bin, self.sources, self.files / "usr/share/fixture", self.tree / "staging_dir/host/bin"):
            directory.mkdir(parents=True, exist_ok=True)
        (self.tree / "staging_dir/host/bin/apk").symlink_to(self.apk)
        (self.files / "usr/share/fixture/readme").write_text("test data, no executable\n")
        self.private = self.tree / "private-key.pem"
        public = self.tree / "public-key.pem"
        self.command(self.openssl, "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", self.private)
        self.command(self.openssl, "ec", "-in", self.private, "-pubout", "-out", public)
        self.root = self.tree / "build_dir/root-mediatek"
        self.keys = self.root / "etc/apk/keys"
        self.keys.mkdir(parents=True)
        shutil.copyfile(public, self.keys / public.name)
        (self.root / "lib/apk/db").mkdir(parents=True)
        (self.root / "lib/apk/db/installed").write_text("")
        (self.root / "etc/apk/world").write_text("")
        built = [self.make_package("kernel", KERNEL), self.make_package("probe", "1-r1")]
        index = self.sources / "packages.adb"
        self.command(self.apk, "--keys-dir", self.keys, "mkndx", "--sign-key", self.private, "--output", index, *built)
        # Install only harmless fixture data in this temporary root, with scripts disabled.
        # Read the real native installed database rather than inventing its checksum encoding.
        self.command(self.apk, "--root", self.root, "--arch", packages.check.ARCH, "--keys-dir", self.keys,
                     "--repositories-file", "/dev/null", "--repository", index.as_uri(), "--no-network", "--no-cache",
                     "add", "--usermode", "--initdb", "--no-scripts", "probe=1-r1")
        self.artifact = {"status": "passed", "rootfs_path": "build_dir/root-mediatek",
                         "image": "fixture-image.bin", "sha256": "12" * 32}
        self.output = self.tree.parent / "matching-packages"

    def test_signed_same_build_repository_with_no_private_key(self):
        self.make_package("unselected", "1-r1")
        result = packages.collect(self.tree, self.artifact, self.output)
        self.assertEqual(result["package_count"], 2)
        self.assertEqual(set(result["packages"]), {"kernel", "probe"})
        self.assertFalse(result["private_key_exported"])
        self.assertEqual({p.name for p in self.output.iterdir()}, {
            "kernel-" + KERNEL + ".apk", "probe-1-r1.apk", "public-key.pem", "packages.adb",
            "SHA256SUMS", "package-repository-check.json"})

    def test_other_signing_key_is_rejected(self):
        other = self.tree / "other-private-key.pem"
        self.command(self.openssl, "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", other)
        self.make_package("probe", "1-r1", other)
        with self.assertRaises(ValueError):
            packages.collect(self.tree, self.artifact, self.output)
        self.assertFalse(self.output.exists())

    def test_valid_signature_with_replaced_payload_is_rejected(self):
        (self.files / "usr/share/fixture/readme").write_text("replaced test payload\n")
        self.make_package("probe", "1-r1")
        with self.assertRaises(ValueError):
            packages.collect(self.tree, self.artifact, self.output)

    def test_corrupt_archive_is_rejected(self):
        package = self.bin / "probe-1-r1.apk"
        data = bytearray(package.read_bytes())
        data[len(data) // 2] ^= 1
        package.write_bytes(data)
        with self.assertRaises((RuntimeError, ValueError)):
            packages.collect(self.tree, self.artifact, self.output)

    def test_unverified_image_is_rejected(self):
        artifact = copy.deepcopy(self.artifact)
        artifact["status"] = "failed"
        with self.assertRaises(ValueError):
            packages.collect(self.tree, artifact, self.output)


if __name__ == "__main__":
    unittest.main()
