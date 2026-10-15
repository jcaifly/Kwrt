"""Exercise delivered-image extraction using real OpenWrt SquashFS fixtures."""

import hashlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock


spec = importlib.util.spec_from_file_location("rax3000m_image", Path(__file__).parents[1] / "rax3000m_image.py")
image_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(image_tools)

DEVICE = "cmcc_rax3000m-emmc"
ROOT_MEMBER = f"sysupgrade-{DEVICE}/root"


def sysupgrade(path, payload=b"fixture", members=None):
    if members is None:
        member = tarfile.TarInfo(ROOT_MEMBER)
        member.size = len(payload)
        members = [(member, payload)]
    with tarfile.open(path, "w", format=tarfile.GNU_FORMAT) as archive:
        for member, content in members:
            archive.addfile(member, io.BytesIO(content) if content is not None else None)


class TarRootChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.image = self.base / "sysupgrade.bin"
        self.workdir = self.base / "unpacked"
        self.tool = self.base / "must-not-execute"
        # These tests reject input before any subprocess and work under root too.
        self.nonroot = mock.patch.object(image_tools.os, "geteuid", return_value=1000)
        self.nonroot.start()
        self.addCleanup(self.nonroot.stop)

    def unpack(self):
        return image_tools.unpack_rootfs(self.image, self.workdir, self.tool, DEVICE)

    def test_wrong_device_member_is_rejected(self):
        member = tarfile.TarInfo("sysupgrade-another-device/root")
        member.size = 7
        sysupgrade(self.image, members=[(member, b"fixture")])
        with self.assertRaisesRegex(ValueError, "exactly one TAR member.*found 0"):
            self.unpack()
        self.assertFalse((self.workdir / "root.squashfs").exists())

    def test_duplicate_roots_are_rejected(self):
        for second_type in (tarfile.REGTYPE, tarfile.SYMTYPE):
            with self.subTest(type=second_type):
                self.workdir = self.base / f"unpacked-{second_type.hex()}"
                first = tarfile.TarInfo(ROOT_MEMBER)
                first.size = 7
                second = tarfile.TarInfo(ROOT_MEMBER)
                second.type = second_type
                second.linkname = "elsewhere"
                second.size = 7 if second_type == tarfile.REGTYPE else 0
                sysupgrade(self.image, members=[
                    (first, b"fixture"),
                    (second, b"fixture" if second_type == tarfile.REGTYPE else None),
                ])
                with self.assertRaisesRegex(ValueError, "exactly one TAR member.*found 2"):
                    self.unpack()

    def test_special_root_members_are_rejected(self):
        for member_type in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE,
                            tarfile.BLKTYPE, tarfile.FIFOTYPE, tarfile.DIRTYPE,
                            tarfile.CONTTYPE, tarfile.GNUTYPE_SPARSE):
            with self.subTest(type=member_type):
                self.workdir = self.base / f"unpacked-{member_type.hex()}"
                member = tarfile.TarInfo(ROOT_MEMBER)
                member.type = member_type
                member.linkname = "elsewhere"
                sysupgrade(self.image, members=[(member, None)])
                with self.assertRaisesRegex(ValueError, "ordinary regular file"):
                    self.unpack()

    def test_existing_workdir_is_rejected_without_modification(self):
        sysupgrade(self.image)
        self.workdir.mkdir()
        marker = self.workdir / "preserve"
        marker.write_bytes(b"keep")
        with self.assertRaisesRegex(ValueError, "must be new"):
            self.unpack()
        self.assertEqual(list(self.workdir.iterdir()), [marker])
        self.assertEqual(marker.read_bytes(), b"keep")

    def test_existing_empty_directory_file_and_dangling_symlink_are_rejected(self):
        sysupgrade(self.image)
        for kind in ("directory", "file", "symlink"):
            with self.subTest(kind=kind):
                self.workdir = self.base / kind
                if kind == "directory":
                    self.workdir.mkdir()
                elif kind == "file":
                    self.workdir.write_bytes(b"keep")
                else:
                    self.workdir.symlink_to(self.base / "missing-target")
                with self.assertRaisesRegex(ValueError, "must be new"):
                    self.unpack()
        self.assertFalse((self.base / "missing-target").exists())

    def test_root_execution_is_rejected(self):
        with mock.patch.object(image_tools.os, "geteuid", return_value=0):
            with self.assertRaisesRegex(ValueError, "non-root user"):
                self.unpack()
        self.assertFalse(self.workdir.exists())


class SquashfsRootChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tool_paths = [os.environ.get(name) for name in ("OPENWRT_MKSQUASHFS", "OPENWRT_UNSQUASHFS")]
        if any(not value or not Path(value).is_file() or not os.access(value, os.X_OK)
               for value in tool_paths):
            raise unittest.SkipTest(
                "Set OPENWRT_MKSQUASHFS and OPENWRT_UNSQUASHFS to executable OpenWrt SquashFS 4.7.4 host tools"
            )
        if os.geteuid() == 0:
            raise unittest.SkipTest("Real strict extraction requires a non-root user")
        cls.mksquashfs, cls.unsquashfs = (Path(value).resolve() for value in tool_paths)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.source = self.base / "source"
        (self.source / "etc").mkdir(parents=True)
        (self.source / "etc/banner").write_bytes(b"offline fixture only\n")
        (self.source / "dev").mkdir()
        (self.source / "usr/bin").mkdir(parents=True)
        self.execution_marker = self.base / "firmware-was-executed"
        program = self.source / "usr/bin/must-not-run"
        program.write_text(f"#!/bin/sh\ntouch '{self.execution_marker}'\n")
        program.chmod(0o755)
        (self.source / "etc/banner-link").symlink_to("banner")
        self.squashfs = self.base / "fixture.squashfs"
        self.image = self.base / "sysupgrade.bin"
        self.workdir = self.base / "unpacked"

    def make_squashfs(self, extra_pseudo=None):
        command = [
            str(self.mksquashfs), str(self.source), str(self.squashfs),
            "-noappend", "-no-progress", "-processors", "2", "-comp", "xz",
            "-p", "dev/console c 0600 0 0 5 1",
        ]
        if extra_pseudo:
            command += ["-p", extra_pseudo]
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def unpack(self):
        return image_tools.unpack_rootfs(self.image, self.workdir, self.unsquashfs, DEVICE)

    def test_real_fixture_is_unpacked_and_reported_without_execution(self):
        self.make_squashfs()
        payload = self.squashfs.read_bytes()
        sysupgrade(self.image, payload)
        root, report = self.unpack()
        self.assertEqual(root, (self.workdir / "rootfs").resolve())
        self.assertEqual((root / "etc/banner").read_bytes(), b"offline fixture only\n")
        self.assertTrue((root / "etc/banner-link").is_symlink())
        self.assertEqual((root / "etc/banner-link").read_bytes(), b"offline fixture only\n")
        self.assertTrue(os.access(root / "usr/bin/must-not-run", os.X_OK))
        self.assertFalse(self.execution_marker.exists())
        self.assertFalse((root / "dev/console").exists())
        self.assertEqual((self.workdir / "root.squashfs").read_bytes(), payload)
        self.assertEqual(report["image_sha256"], hashlib.sha256(self.image.read_bytes()).hexdigest())
        self.assertEqual(report["root_payload_sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(report["rootfs"], str(root))
        self.assertEqual(report["root_member"], ROOT_MEMBER)
        self.assertTrue(report["strict_errors"])
        self.assertEqual(report["excluded_paths"], ["dev/console"])
        self.assertFalse(report["firmware_programs_executed"])
        self.assertEqual(report["unsquashfs_returncode"], 0)
        self.assertEqual(report["unsquashfs_command"], [
            str(self.unsquashfs), "-strict-errors", "-no-progress", "-processors", "2",
            "-dest", "rootfs", "-exclude-list", "dev/console", ";", "root.squashfs",
        ])
        self.assertTrue(Path(report["unsquashfs_stdout_log"]).is_file())
        self.assertEqual(Path(report["unsquashfs_stderr_log"]).read_bytes(), b"")

    def test_corrupt_real_squashfs_is_rejected_with_logs(self):
        self.make_squashfs()
        sysupgrade(self.image, self.squashfs.read_bytes()[:96])
        with self.assertRaisesRegex(RuntimeError, "unsquashfs failed with exit status.*full logs"):
            self.unpack()
        self.assertTrue((self.workdir / "unsquashfs.stdout.log").is_file())
        self.assertTrue((self.workdir / "unsquashfs.stderr.log").read_bytes())
        self.assertFalse(self.execution_marker.exists())

    def test_other_device_node_error_is_not_ignored(self):
        self.make_squashfs("dev/unexpected c 0600 0 0 5 2")
        sysupgrade(self.image, self.squashfs.read_bytes())
        with self.assertRaisesRegex(RuntimeError, "unsquashfs failed with exit status.*full logs"):
            self.unpack()
        stderr = (self.workdir / "unsquashfs.stderr.log").read_text()
        self.assertIn("unexpected", stderr)
        self.assertFalse(self.execution_marker.exists())


if __name__ == "__main__":
    unittest.main()
