"""Exercise startup failures using real readelf and tiny, non-executed ELF files."""

import importlib.util
from pathlib import Path
import shutil
import struct
import tempfile
import unittest


spec = importlib.util.spec_from_file_location(
    "rax3000m_startup", Path(__file__).parents[1] / "rax3000m_startup.py")
startup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(startup)

LOADER = "/lib/ld-musl-aarch64.so.1"


def elf(needed=(), interpreter=None, rpath=None, runpath=None):
    """A real ELF64/AArch64 dynamic table, parsed by the host's native readelf."""
    phnum = 3 if interpreter else 2
    data = bytearray(64 + phnum * 56)
    interp_offset = len(data)
    if interpreter:
        data.extend(interpreter.encode() + b"\0")
    data.extend(b"\0" * (-len(data) % 8))
    strings_offset = len(data)
    strings = bytearray(b"\0")
    references = []
    entries = [(1, name) for name in needed]
    if rpath is not None:
        entries.append((15, rpath))
    if runpath is not None:
        entries.append((29, runpath))
    for tag, value in entries:
        references.append((tag, len(strings)))
        strings.extend(value.encode() + b"\0")
    data.extend(strings)
    data.extend(b"\0" * (-len(data) % 8))
    dynamic_offset = len(data)
    dynamic = [(5, strings_offset), (10, len(strings)), *references, (0, 0)]
    for tag, value in dynamic:
        data.extend(struct.pack("<QQ", tag, value))
    ident = b"\x7fELF\x02\x01\x01" + b"\0" * 9
    struct.pack_into("<16sHHIQQQIHHHHHH", data, 0, ident, 3, 183, 1, 0, 64, 0, 0,
                     64, 56, phnum, 64, 0, 0)
    headers = [(1, 5, 0, 0, 0, len(data), len(data), 4096),
               (2, 4, dynamic_offset, dynamic_offset, dynamic_offset,
                len(dynamic) * 16, len(dynamic) * 16, 8)]
    if interpreter:
        headers.append((3, 4, interp_offset, interp_offset, interp_offset,
                        len(interpreter) + 1, len(interpreter) + 1, 1))
    for index, header in enumerate(headers):
        struct.pack_into("<IIQQQQQQ", data, 64 + index * 56, *header)
    return bytes(data)


@unittest.skipUnless(shutil.which("readelf"), "These static ELF checks require native readelf")
class StartupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="rax3000m-startup-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "root"
        self.root.mkdir()
        for name in startup.CORE_PROGRAMS:
            if name != "/bin/sh":
                self.write(name, elf(["libfixture.so"], LOADER), executable=True)
        self.link("/bin/sh", "busybox")
        self.write(LOADER, elf(), executable=True)
        self.write("/lib/libfixture.so", elf())
        self.write("/etc/rc.common", "#!/bin/sh\n", executable=True)
        self.starts = {"network": 20, "dnsmasq": 19, "dropbear": 19, "rpcd": 12, "uhttpd": 50}
        for name, number in self.starts.items():
            self.write(f"/etc/init.d/{name}",
                       f"#!/bin/sh /etc/rc.common\nSTART={number}\n", executable=True)
            self.link(f"/etc/rc.d/S{number:02d}{name}", f"../init.d/{name}")
        self.write("/etc/config/dhcp", """config dnsmasq
    option rebind_protection '1'
config dhcp 'lan'
    option interface 'lan'
    option limit '150'
config dhcp 'wan'
    option interface 'wan'
    option ignore '1'
""")
        self.write("/etc/config/uhttpd", """config uhttpd 'main'
    list listen_http '0.0.0.0:80'
    list listen_http '[::]:80'
    list listen_https '0.0.0.0:443'
    list listen_https '[::]:443'
""")
        self.write("/etc/config/firewall", """config defaults
    option input 'REJECT'
config zone
    option name 'lan'
    option input 'ACCEPT'
config zone
    option name 'wan'
    option input 'REJECT'
""")
        self.write("/etc/board.d/02_network", """mediatek_setup_interfaces()
{
    local board="$1"
    case $board in
    other,board|\\
    cmcc,rax3000m-emmc)
        ucidef_set_interfaces_lan_wan "lan1 lan2 lan3" eth1
        ;;
    *)
        ucidef_set_interfaces_lan_wan lan0 wan
        ;;
    esac
}
""")

    def path(self, name):
        return self.root / name.lstrip("/")

    def write(self, name, value, executable=False):
        path = self.path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value.encode() if isinstance(value, str) else value)
        path.chmod(0o755 if executable else 0o644)
        return path

    def link(self, name, target):
        path = self.path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(target)

    def check(self):
        return startup.check_startup(self.root)

    def test_factory_image_has_static_evidence_only(self):
        result = self.check()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["first_boot_runtime_validation"], "not performed")
        self.assertEqual(len(result["startup_service_links"]), 5)
        self.assertEqual(result["core_startup_programs_checked"], 12)
        self.assertEqual(result["elf_files_checked"], 13)
        self.assertGreater(result["elf_dependency_edges_checked"], 0)
        self.assertTrue(result["factory_lan_dhcp_enabled"])
        management = result["management_config"]
        self.assertEqual(management["http_listeners_configured"], ["0.0.0.0:80", "[::]:80"])
        self.assertEqual(management["https_listeners_configured"], ["0.0.0.0:443", "[::]:443"])
        self.assertEqual(management["wan_input_policy_configured"], "REJECT")
        self.assertEqual(management["runtime_reachability_validation"], "not performed")
        self.assertEqual(management["complete_firewall_rules_validation"], "not performed")

    def test_each_factory_http_and_https_listener_is_required(self):
        path = self.path("/etc/config/uhttpd")
        original = path.read_text()
        for listener in ("0.0.0.0:80", "[::]:80", "0.0.0.0:443", "[::]:443"):
            with self.subTest(listener=listener):
                # A commented example must not count as an effective list item.
                path.write_text("\n".join("# " + line if "'" + listener + "'" in line else line
                                          for line in original.splitlines()) + "\n")
                with self.assertRaisesRegex(ValueError, "Missing factory IPv4/IPv6 HTTPS? port"):
                    self.check()

    def test_wan_input_policy_must_be_reject_even_when_global_default_is_reject(self):
        path = self.path("/etc/config/firewall")
        path.write_text(path.read_text().replace("option name 'wan'\n    option input 'REJECT'",
                                                "option name 'wan'\n    option input 'ACCEPT'"))
        with self.assertRaisesRegex(ValueError, "WAN zone input policy must be REJECT"):
            self.check()

    def test_absolute_startup_and_program_links_are_image_relative(self):
        self.path("/etc/rc.d/S20network").unlink()
        self.link("/etc/rc.d/S20network", "/etc/init.d/network")
        self.path("/bin/sh").unlink()
        self.link("/bin/sh", "/bin/busybox")
        self.assertEqual(self.check()["status"], "passed")

    def test_relative_and_absolute_library_links(self):
        self.path("/lib/libfixture.so").rename(self.path("/lib/libfixture.so.1"))
        self.link("/lib/libfixture.so", "libfixture.so.1")
        self.path(LOADER).rename(self.path("/lib/musl-real.so"))
        self.link(LOADER, "/lib/musl-real.so")
        self.assertEqual(self.check()["status"], "passed")

    def test_missing_key_service_link(self):
        self.path("/etc/rc.d/S19dnsmasq").unlink()
        with self.assertRaisesRegex(ValueError, "startup link: dnsmasq"):
            self.check()

    def test_wrong_key_service_target(self):
        self.path("/etc/rc.d/S20network").unlink()
        self.link("/etc/rc.d/S20network", "../init.d/dnsmasq")
        with self.assertRaisesRegex(ValueError, "wrong init script: network"):
            self.check()

    def test_duplicate_key_service_link(self):
        self.link("/etc/rc.d/S99network", "../init.d/network")
        with self.assertRaisesRegex(ValueError, "startup link: network"):
            self.check()

    def test_nonexecutable_init_is_rejected(self):
        self.path("/etc/init.d/rpcd").chmod(0o644)
        with self.assertRaisesRegex(ValueError, "not executable.*rpcd"):
            self.check()

    def test_nonexecutable_core_program_is_rejected(self):
        self.path("/sbin/init").chmod(0o644)
        with self.assertRaisesRegex(ValueError, "not executable.*init"):
            self.check()

    def test_missing_core_program_is_rejected(self):
        self.path("/sbin/procd").unlink()
        with self.assertRaisesRegex(ValueError, "Missing image path.*procd"):
            self.check()

    def test_symlink_cycle_is_rejected(self):
        self.path("/bin/busybox").unlink()
        self.link("/bin/busybox", "sh")
        with self.assertRaisesRegex(ValueError, "symlink loop"):
            self.check()

    def test_relative_escape_is_rejected_even_if_host_target_exists(self):
        (self.root.parent / "outside").write_bytes(elf())
        self.path("/lib/libfixture.so").unlink()
        self.link("/lib/libfixture.so", "../../outside")
        with self.assertRaisesRegex(ValueError, "escapes root"):
            self.check()

    def test_absolute_link_does_not_read_host_file(self):
        self.assertTrue(Path("/etc/passwd").is_file())
        self.path("/lib/libfixture.so").unlink()
        self.link("/lib/libfixture.so", "/etc/passwd")
        with self.assertRaisesRegex(ValueError, "Missing ELF dependency"):
            self.check()

    def test_missing_loader_is_rejected(self):
        self.path(LOADER).unlink()
        with self.assertRaisesRegex(ValueError, "Missing image path.*ld-musl"):
            self.check()

    def test_missing_dynamic_library_is_rejected(self):
        self.path("/lib/libfixture.so").unlink()
        with self.assertRaisesRegex(ValueError, "Missing ELF dependency.*libfixture.so"):
            self.check()

    def test_bracket_in_interpreter_name_is_not_truncated(self):
        self.write("/sbin/init", elf(["libfixture.so"], LOADER + "]missing"), executable=True)
        with self.assertRaisesRegex(ValueError, "Missing image path.*missing"):
            self.check()

    def test_bracket_in_dependency_name_is_not_truncated(self):
        self.write("/sbin/init", elf(["libfixture.so]missing"], LOADER), executable=True)
        with self.assertRaisesRegex(ValueError, "Missing ELF dependency.*missing"):
            self.check()

    def test_noncore_elf_dependencies_are_checked(self):
        self.write("/usr/lib/plugin.so", elf(["libmissing.so"]))
        with self.assertRaisesRegex(ValueError, "Missing ELF dependency.*libmissing.so"):
            self.check()

    def test_malformed_elf_is_rejected_by_real_readelf(self):
        self.write("/lib/libfixture.so", b"\x7fELFtruncated")
        with self.assertRaisesRegex(ValueError, "readelf could not inspect"):
            self.check()

    def test_musl_path_file_is_used(self):
        self.write("/opt/lib/libfixture.so", elf())
        self.path("/lib/libfixture.so").unlink()
        self.write("/etc/ld-musl-aarch64.path", "/opt/lib\n/lib\n")
        result = self.check()
        self.assertEqual(result["musl_library_path_file"], "/etc/ld-musl-aarch64.path")
        self.assertEqual(result["system_library_paths"], ["/opt/lib", "/lib"])

    def test_musl_path_file_replaces_default_search(self):
        self.write("/etc/ld-musl-aarch64.path", "/opt/lib\n")
        with self.assertRaisesRegex(ValueError, "Missing ELF dependency.*libfixture.so"):
            self.check()

    def test_musl_path_file_does_not_expand_origin(self):
        self.write("/etc/ld-musl-aarch64.path", "$ORIGIN/lib\n")
        with self.assertRaisesRegex(ValueError, "Unsupported relative or variable ELF library path"):
            self.check()

    def test_origin_rpath_is_inherited_for_transitive_dependency(self):
        self.write("/sbin/init", elf(["libapp.so"], LOADER, rpath="$ORIGIN/../opt/lib"), executable=True)
        self.write("/opt/lib/libapp.so", elf(["libleaf.so"]))
        self.write("/opt/lib/libleaf.so", elf())
        self.assertEqual(self.check()["status"], "passed")

    def test_origin_runpath_is_resolved(self):
        self.write("/sbin/init", elf(["libapp.so"], LOADER, runpath="${ORIGIN}/../opt/lib"), executable=True)
        self.write("/opt/lib/libapp.so", elf())
        self.assertEqual(self.check()["status"], "passed")

    def test_symlinked_library_origin_uses_its_load_path(self):
        self.write("/sbin/init", elf(["/opt/app/libapp.so"], LOADER), executable=True)
        self.write("/usr/lib/libapp.so", elf(["libleaf.so"], runpath="$ORIGIN"))
        self.link("/opt/app/libapp.so", "/usr/lib/libapp.so")
        self.write("/opt/app/libleaf.so", elf())
        self.assertEqual(self.check()["status"], "passed")

    def test_empty_rpath_is_valid(self):
        self.write("/sbin/init", elf(["libfixture.so"], LOADER, rpath=""), executable=True)
        self.assertEqual(self.check()["status"], "passed")

    def test_factory_lan_dhcp_must_be_enabled(self):
        self.write("/etc/config/dhcp", "config dnsmasq\nconfig dhcp lan\n option interface lan\n option ignore 1\n")
        with self.assertRaisesRegex(ValueError, "LAN DHCP is disabled"):
            self.check()

    def test_factory_lan_dhcp_needs_a_nonempty_dynamic_pool(self):
        self.write("/etc/config/dhcp", "config dnsmasq\nconfig dhcp lan\n option interface lan\n option limit 0\n")
        with self.assertRaisesRegex(ValueError, "cannot allocate dynamic leases"):
            self.check()

    def test_factory_dnsmasq_instance_must_be_enabled(self):
        path = self.path("/etc/config/dhcp")
        path.write_text(path.read_text().replace("config dnsmasq", "config dnsmasq\n option disabled 1"))
        with self.assertRaisesRegex(ValueError, "disabled or ambiguous factory dnsmasq"):
            self.check()

    def test_port_mapping_for_another_board_cannot_mask_wrong_mapping(self):
        path = self.path("/etc/board.d/02_network")
        path.write_text(path.read_text().replace('other,board|\\\n    cmcc,rax3000m-emmc)',
                                                'other,board)').replace('    *)', '    cmcc,rax3000m-emmc)'))
        with self.assertRaisesRegex(ValueError, "port mapping changed"):
            self.check()


if __name__ == "__main__":
    unittest.main()
