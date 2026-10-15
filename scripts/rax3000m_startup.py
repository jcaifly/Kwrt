"""Read-only checks of factory startup files; never run an image's programs."""

from collections import deque
import fnmatch
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import stat
import subprocess


SERVICES = {
    "network": "/sbin/netifd",
    "dnsmasq": "/usr/sbin/dnsmasq",
    "dropbear": "/usr/sbin/dropbear",
    "rpcd": "/sbin/rpcd",
    "uhttpd": "/usr/sbin/uhttpd",
}
CORE_PROGRAMS = (
    "/sbin/init", "/sbin/procd", "/bin/busybox", "/bin/sh",
    "/sbin/ubusd", "/bin/ubus", "/sbin/uci", *SERVICES.values(),
)
DEFAULT_LIBRARY_PATH = ("/lib", "/usr/local/lib", "/usr/lib")


class MissingImagePath(ValueError):
    """An image path does not exist, as opposed to an unsafe link."""


def require(condition, message):
    if not condition:
        raise ValueError(message)


def image_path(root, name):
    """Resolve links with / anchored at root, without consulting host paths."""
    name = str(name)
    require(name.startswith("/") and "\0" not in name, f"Invalid image path: {name!r}")
    pending = deque(PurePosixPath(name).parts[1:])
    parts, links = [], 0
    while pending:
        component = pending.popleft()
        if component in ("", "."):
            continue
        if component == "..":
            require(parts, f"Image path escapes root: {name}")
            parts.pop()
            continue
        candidate = root.joinpath(*parts, component)
        try:
            mode = candidate.lstat().st_mode
        except FileNotFoundError as error:
            raise MissingImagePath(f"Missing image path: {name}") from error
        if stat.S_ISLNK(mode):
            links += 1
            require(links <= 40, f"Image symlink loop or excessive depth: {name}")
            target = PurePosixPath(os.readlink(candidate))
            if target.is_absolute():
                parts = []
            pending.extendleft(reversed(target.parts[1:] if target.is_absolute() else target.parts))
        else:
            require(not pending or stat.S_ISDIR(mode), f"Non-directory in image path: {name}")
            parts.append(component)
    return root.joinpath(*parts)


def image_file(root, name, executable=False):
    path = image_path(root, name)
    mode = path.stat().st_mode
    require(stat.S_ISREG(mode), f"Not a regular image file: {name}")
    require(not executable or mode & 0o111, f"Image program is not executable: {name}")
    return path


def check_services(root):
    directory = image_path(root, "/etc/rc.d")
    require(directory.is_dir(), "Missing image startup directory")
    checked = {}
    for service in SERVICES:
        script = image_file(root, f"/etc/init.d/{service}", executable=True)
        text = script.read_text()
        require(text.splitlines() and shlex.split(text.splitlines()[0][2:]) ==
                ["/bin/sh", "/etc/rc.common"] and text.startswith("#!"),
                f"Unexpected init interpreter: {service}")
        starts = re.findall(r"^START=['\"]?([0-9]{1,2})['\"]?\s*(?:#.*)?$", text, re.M)
        require(len(starts) == 1, f"Missing or ambiguous init START: {service}")
        links = [p for p in directory.iterdir() if re.fullmatch(r"S[0-9]{2}" + service, p.name)]
        expected = f"S{int(starts[0]):02d}{service}"
        require(len(links) == 1 and links[0].name == expected and links[0].is_symlink(),
                f"Missing or incorrect startup link: {service}")
        require(image_path(root, "/etc/rc.d/" + expected) == script,
                f"Startup link targets the wrong init script: {service}")
        checked[service] = "/etc/rc.d/" + expected
    image_file(root, "/etc/rc.common", executable=True)
    return checked


def factory_sections(root, name):
    """Read the simple config/option/list lines used by the factory files."""
    sections, current = [], None
    for line in image_file(root, name).read_text().splitlines():
        words = shlex.split(line, comments=True)
        if not words:
            continue
        if words[0] == "config":
            require(len(words) in (2, 3), f"Invalid factory UCI section: {name}")
            current = {"type": words[1], "name": words[2] if len(words) == 3 else "", "options": {}, "lists": {}}
            sections.append(current)
        elif words[0] in ("option", "list"):
            require(current is not None and len(words) == 3, f"Invalid factory UCI value: {name}")
            if words[0] == "option":
                require(words[1] not in current["lists"], f"Mixed factory UCI scalar/list: {name}: {words[1]}")
                current["options"][words[1]] = words[2]
            else:
                require(words[1] not in current["options"], f"Mixed factory UCI scalar/list: {name}: {words[1]}")
                current["lists"].setdefault(words[1], []).append(words[2])
    return sections


def check_factory_network(root):
    sections = factory_sections(root, "/etc/config/dhcp")
    lan = [s for s in sections if s["type"] == "dhcp" and s["name"] == "lan"]
    require(len(lan) == 1, "Missing or ambiguous factory LAN DHCP section")
    options = lan[0]["options"]
    false_values = {"0", "false", "off", "no"}
    instances = [s for s in sections if s["type"] == "dnsmasq"]
    require(len(instances) == 1 and instances[0]["options"].get("disabled", "0").lower() in false_values,
            "Missing, disabled or ambiguous factory dnsmasq instance")
    require("instance" not in options or options["instance"] == instances[0]["name"],
            "Factory LAN DHCP refers to a different dnsmasq instance")
    require(options.get("interface") == "lan" and options.get("ignore", "0").lower() in false_values and
            options.get("dynamicdhcp", "1").lower() not in false_values and
            options.get("dhcpv4", "server") != "disabled" and
            options.get("limit", "150").isdigit() and int(options.get("limit", "150")) > 0,
            "Factory LAN DHCP is disabled or cannot allocate dynamic leases")

    text = image_file(root, "/etc/board.d/02_network").read_text().replace("\\\n", "")
    function = re.search(r"^mediatek_setup_interfaces\(\)\s*\n\{\n(.*?)^\}", text, re.M | re.S)
    require(function is not None, "Missing factory board interface setup")
    switch = re.search(r"^[ \t]*case\s+[\"']?\$board[\"']?\s+in\s*\n(.*?)^[ \t]*esac\b",
                       function[1], re.M | re.S)
    require(switch is not None, "Missing factory board selection")
    board = "cmcc,rax3000m-emmc"
    selected = None
    for arm in re.finditer(r"^\s*([^()\n]+)\)\s*\n(.*?)^\s*;;", switch[1], re.M | re.S):
        patterns = arm[1].strip().split("|")
        if any(fnmatch.fnmatchcase(board, pattern.strip()) for pattern in patterns):
            selected = [shlex.split(line, comments=True) for line in arm[2].splitlines()]
            selected = [line for line in selected if line]
            break
    require(selected == [["ucidef_set_interfaces_lan_wan", "lan1 lan2 lan3", "eth1"]],
            "Factory RAX3000M eMMC LAN/WAN port mapping changed")
    return {"factory_lan_dhcp_enabled": True, "factory_lan_ports": ["lan1", "lan2", "lan3"],
            "factory_wan_port": "eth1", "factory_network_source": "/etc/board.d/02_network"}


def check_management_config(root):
    sections = factory_sections(root, "/etc/config/uhttpd")
    mains = [s for s in sections if s["type"] == "uhttpd" and s["name"] == "main"]
    require(len(mains) == 1, "Missing or ambiguous factory uhttpd main configuration")
    listeners = mains[0]["lists"]
    http, https = {"0.0.0.0:80", "[::]:80"}, {"0.0.0.0:443", "[::]:443"}
    require(http <= set(listeners.get("listen_http", [])), "Missing factory IPv4/IPv6 HTTP port 80 listener")
    require(https <= set(listeners.get("listen_https", [])), "Missing factory IPv4/IPv6 HTTPS port 443 listener")
    zones = [s for s in factory_sections(root, "/etc/config/firewall")
             if s["type"] == "zone" and s["options"].get("name") == "wan"]
    require(len(zones) == 1 and zones[0]["options"].get("input", "").upper() == "REJECT",
            "Factory WAN zone input policy must be REJECT")
    return {"validation_scope": "static factory UCI configuration only",
            "http_listeners_configured": sorted(http), "https_listeners_configured": sorted(https),
            "wan_input_policy_configured": "REJECT", "runtime_reachability_validation": "not performed",
            "complete_firewall_rules_validation": "not performed"}


def elf_info(readelf, path, name):
    with path.open("rb") as stream:
        require(stream.read(4) == b"\x7fELF", f"Not an ELF startup program or library: {name}")
    result = subprocess.run([readelf, "-lW", "-dW", "--", str(path)],
                            capture_output=True, text=True, env={**os.environ, "LC_ALL": "C"})
    require(result.returncode == 0, f"Host readelf could not inspect image ELF: {name}: {result.stderr.strip()}")
    text = result.stdout
    interpreters = re.findall(r"^[ \t]*\[Requesting program interpreter: (.*)\][ \t]*$", text, re.M)
    interp_count = len(re.findall(r"^[ \t]*INTERP[ \t]", text, re.M))
    require(interp_count == len(interpreters) and len(interpreters) <= 1,
            f"Unrecognized or multiple ELF interpreters: {name}")

    def dynamic_strings(tag, label):
        # Capture the entire readelf line: ']' is legal inside an ELF string.
        pattern = (r"^[ \t]*0x[0-9a-fA-F]+[ \t]+\(" + tag + r"\)[ \t]+" +
                   label + r": \[(.*)\][ \t]*$")
        values = re.findall(pattern, text, re.M)
        require(text.count("(" + tag + ")") == len(values),
                f"Unrecognized ELF {tag} string: {name}")
        return values

    needed = dynamic_strings("NEEDED", "Shared library")
    # musl treats RUNPATH as RPATH and searches the requesting object's ancestors.
    runpath = dynamic_strings("RUNPATH", "Library runpath")
    rpath = dynamic_strings("RPATH", "Library rpath")
    return {"interpreter": interpreters[0] if interpreters else None,
            "needed": needed, "rpath": runpath if runpath else rpath}


def library_paths(values, origin=None):
    result = []
    for value in values:
        for directory in re.split(r"[:\n]", value):
            if not directory:
                continue
            if origin is not None:
                directory = directory.replace("${ORIGIN}", origin).replace("$ORIGIN", origin)
            require(directory.startswith("/") and "$" not in directory,
                    f"Unsupported relative or variable ELF library path: {directory!r}")
            if directory not in result:
                result.append(directory)
    return result


def check_elf_dependencies(root):
    readelf = shutil.which("readelf")
    require(readelf is not None, "Host readelf is required for static startup validation")
    require(not Path(readelf).resolve().is_relative_to(root), "Refusing to execute image-provided readelf")
    infos = {}

    def inspect(name, executable=False):
        path = image_file(root, name, executable=executable)
        canonical = "/" + path.relative_to(root).as_posix()
        if canonical not in infos:
            infos[canonical] = elf_info(readelf, path, canonical)
        return canonical

    programs = {name: inspect(name, executable=True) for name in CORE_PROGRAMS}
    for directory, dirs, files in os.walk(root, followlinks=False):
        relative = Path(directory).relative_to(root)
        if relative.parts[:2] == ("lib", "firmware"):
            dirs[:] = []
            continue
        for filename in files:
            path = Path(directory) / filename
            if not stat.S_ISREG(path.lstat().st_mode):
                continue
            with path.open("rb") as stream:
                magic = stream.read(4)
            if magic == b"\x7fELF":
                inspect("/" + path.relative_to(root).as_posix())

    musl_loaders = {i["interpreter"] for i in infos.values() if i["interpreter"] and
                    re.fullmatch(r"/lib/ld-musl-[^/]+\.so\.1", i["interpreter"])}
    require(len(musl_loaders) <= 1, "Multiple musl loader architectures in image")
    system_paths = list(DEFAULT_LIBRARY_PATH)
    musl_path_file = None
    if musl_loaders:
        loader = next(iter(musl_loaders))
        musl_path_file = "/etc/" + PurePosixPath(loader).name.removesuffix(".so.1") + ".path"
        try:
            text = image_file(root, musl_path_file).read_text()
        except MissingImagePath:
            musl_path_file = None
        else:
            system_paths = library_paths([text.rstrip("\n")]) if text.rstrip("\n") else []

    visited, covered, edges, interpreters = set(), set(), set(), set()

    def visit(name, inherited=(), loaded_as=None):
        info = infos[name]
        # musl keeps the path used to load a DSO for its ORIGIN, even for symlinks.
        # The main executable uses its canonical /proc/self/exe location instead.
        origin = str(PurePosixPath(loaded_as or name).parent)
        search = tuple(dict.fromkeys([*library_paths(info["rpath"], origin), *inherited]))
        context = (name, search)
        if context in visited:
            return
        visited.add(context)
        covered.add(name)
        if info["interpreter"]:
            interpreter = info["interpreter"]
            loaded = inspect(interpreter, executable=True)
            interpreters.add(interpreter)
            visit(loaded)
        for needed in info["needed"]:
            require("/" not in needed or needed.startswith("/"),
                    f"Unsupported relative ELF dependency: {name}: {needed}")
            candidates = [needed] if needed.startswith("/") else [
                str(PurePosixPath(directory) / needed) for directory in (*search, *system_paths)]
            loaded = None
            for candidate in candidates:
                try:
                    loaded = inspect(candidate)
                except MissingImagePath:
                    continue
                break
            require(loaded is not None, f"Missing ELF dependency in image: {name}: {needed}")
            edges.add((name, needed, loaded))
            visit(loaded, search, candidate)

    # Start with executable contexts so inherited musl RPATHs reach their libraries.
    entrypoints = list(dict.fromkeys([*programs.values(), *[n for n, i in infos.items() if i["interpreter"]]]))
    for name in entrypoints:
        visit(name)
    for name in list(infos):
        if name not in covered:
            visit(name)
    return {"core_startup_programs_checked": len(programs), "elf_files_checked": len(infos),
            "elf_dependency_edges_checked": len(edges), "elf_interpreters": sorted(interpreters),
            "musl_library_path_file": musl_path_file, "system_library_paths": system_paths}


def check_startup(root: Path) -> dict:
    """Raise ValueError on a static failure; do not boot, chroot or run image code."""
    root = Path(root).resolve(strict=True)
    require(root.is_dir(), "Image root is not a directory")
    services = check_services(root)
    network = check_factory_network(root)
    return {"status": "passed", "validation": "static image files only; no target program executed",
            "first_boot_runtime_validation": "not performed", "startup_service_links": services,
            "management_config": check_management_config(root), **network, **check_elf_dependencies(root)}
