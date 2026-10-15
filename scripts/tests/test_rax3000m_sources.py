"""Reject incomplete pinned source archives and keep useful failure excerpts."""

import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest


spec = importlib.util.spec_from_file_location("vendor", Path(__file__).resolve().parents[1] / "rax3000m-vendor.py")
vendor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vendor)


class SourceArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.downloads = Path(self.temporary.name)
        self.modules = ('[submodule "libcork"]\n\tpath = libcork\n'
                        '\turl = https://github.com/shadowsocks/libcork.git\n    ignore = dirty\n')

    def archive(self, name, files):
        file = self.downloads / (name + ".tar.gz")
        with tarfile.open(file, "w:gz") as archive:
            for path, text in files.items():
                data = text.encode()
                info = tarfile.TarInfo(name + "/" + path)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
        return file, {"sha256": vendor.digest(file)}

    def complete(self, child_files=None):
        child, lock = self.archive("libcork", child_files or {"Makefile.am": "library sources\n"})
        lock.update(git_url="https://github.com/shadowsocks/libcork.git", commit="f02984545061c924808e4b9ea7cc6749a41f1979",
                    url="https://codeload.github.com/shadowsocks/libcork/tar.gz/f02984545061c924808e4b9ea7cc6749a41f1979",
                    local_filename=child.name, required_files=["Makefile.am"])
        parent, source = self.archive("simple-obfs", {".gitmodules": self.modules, "configure.ac": "project\n"})
        source["submodules"] = {"libcork": lock}
        return parent, source

    def test_declared_but_unpinned_submodule_fails_before_build(self):
        parent, source = self.archive("simple-obfs", {".gitmodules": self.modules})
        with self.assertRaisesRegex(ValueError, "Unpinned or missing submodule"):
            vendor.check_source_archive(parent, source, self.downloads)

    def test_complete_locked_submodule_is_reported(self):
        parent, source = self.complete()
        result = vendor.check_source_archive(parent, source, self.downloads)
        self.assertEqual(result["submodules"]["libcork"]["commit"], source["submodules"]["libcork"]["commit"])

    def test_missing_download_is_rejected(self):
        parent, source = self.complete()
        (self.downloads / source["submodules"]["libcork"]["local_filename"]).unlink()
        with self.assertRaisesRegex(ValueError, "missing or hash mismatch"):
            vendor.check_source_archive(parent, source, self.downloads)

    def test_changed_submodule_archive_is_rejected(self):
        parent, source = self.complete()
        (self.downloads / source["submodules"]["libcork"]["local_filename"]).write_bytes(b"changed archive")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            vendor.check_source_archive(parent, source, self.downloads)

    def test_hash_matching_archive_without_build_sources_is_rejected(self):
        parent, source = self.complete({"README": "missing actual build files\n"})
        with self.assertRaisesRegex(ValueError, "Missing required source file Makefile.am"):
            vendor.check_source_archive(parent, source, self.downloads)

    def test_unpinned_nested_submodule_is_rejected(self):
        parent, source = self.complete({"Makefile.am": "library\n", ".gitmodules": self.modules})
        with self.assertRaisesRegex(ValueError, "Unpinned or missing submodule"):
            vendor.check_source_archive(parent, source, self.downloads)

    def test_submodule_url_cannot_silently_change(self):
        parent, source = self.complete()
        source["submodules"]["libcork"]["git_url"] = "https://example.invalid/other.git"
        with self.assertRaisesRegex(ValueError, "Submodule URL differs"):
            vendor.check_source_archive(parent, source, self.downloads)


class DiagnosticTests(unittest.TestCase):
    def test_compiler_failed_slots_definition_is_not_a_failure(self):
        text = 'gcc -DFAILED_SLOTS_DIR="/var/run/mdadm/failed-slots" -c probe_roms.c\n'
        text += "configure.ac:215: error: required file 'libcork/Makefile.in' not found\n"
        text += "make[3]: *** [simple-obfs/.configured] Error 2\n"
        result = vendor.failure_excerpt(text)
        self.assertNotIn("FAILED_SLOTS_DIR", result)
        self.assertIn("libcork/Makefile.in", result)
        self.assertIn("simple-obfs/.configured", result)

    def test_public_excerpt_stays_within_byte_limit_and_keeps_cause(self):
        text = "configure.ac:215: error: missing libcork/Makefile.in\n"
        text += "\n".join("make: *** " + "路径" * 500 + " Error 2" for _ in range(10))
        result = vendor.failure_excerpt(text)
        self.assertLessEqual(len(result.encode()), 3000)
        self.assertIn("missing libcork/Makefile.in", result)
        self.assertIn("Error 2", result)


if __name__ == "__main__":
    unittest.main()
