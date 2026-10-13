#!/usr/bin/env python3
"""Deliver signed packages matching this image, without publishing a signing key."""

import argparse
import base64
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


spec = importlib.util.spec_from_file_location("check_rax3000m", Path(__file__).with_name("check-rax3000m.py"))
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def run(*args):
    result = subprocess.run([str(arg) for arg in args], text=True, capture_output=True)
    check.require(result.returncode == 0, f"Package repository check failed: {result.stdout}{result.stderr}")
    return result.stdout


def check_metadata(info, record, kernel):
    name = record["P"]
    check.require(info.get("name") == name and info.get("version") == record["V"],
                  f"Package name/version differs from installed image: {name}")
    check.require(info.get("arch") == record["A"] and record["A"] in {check.ARCH, "noarch"},
                  f"Package architecture differs from installed image: {name}")
    for dependency in info.get("depends", []):
        if dependency.startswith("kernel="):
            check.require(dependency == f"kernel={kernel}", f"Package has a different kernel ABI: {name}")
    check.require(set(info.get("depends", [])) == set(record.get("D", "").split()),
                  f"Package dependencies differ from installed image: {name}")


def check_record(info, record, kernel):
    check_metadata(info, record, kernel)
    try:
        # Use the native mkndx identity, not a checksum of the signed container.
        # OpenWrt's legacy database stores its first 20 bytes as Q1.
        identity = record["C"]
        expected = base64.b64decode(identity[2:], validate=True)
        actual = bytes.fromhex(info["hashes"])
        valid = identity.startswith("Q1") and len(expected) == 20 and len(actual) == 32 and actual[:20] == expected
    except (KeyError, ValueError):
        valid = False
    check.require(valid, f"Package content differs from installed image: {record['P']}")


def collect(tree, artifact, output):
    tree, output = Path(tree).resolve(), Path(output).resolve()
    check.require(artifact.get("status") == "passed", "Image verification must pass before package delivery")
    root = tree / artifact["rootfs_path"]
    records = check.installed_records(root)
    kernel = records["kernel"]["V"]
    apk = (tree / "staging_dir/host/bin/apk").resolve()
    public_key, private_key = tree / "public-key.pem", tree / "private-key.pem"
    trusted = root / "etc/apk/keys"
    check.require(public_key.is_file() and private_key.is_file(), "Missing native build signing key")
    check.require((trusted / public_key.name).is_file() and
                  (trusted / public_key.name).read_bytes() == public_key.read_bytes(),
                  "Build public key is not trusted by this image")
    check.require(not output.exists(), "Refusing to mix package repositories from different builds")
    sources = tree / "staging_dir/packages/mediatek"
    chosen = {}
    for source in sorted(sources.glob("*.apk")):
        check.require(source.resolve().is_relative_to(tree / "bin"), "Package link leaves this build's bin directory")
        info = json.loads(run(apk, "adbdump", "--format", "json", source))["info"]
        name = info["name"]
        if name not in records:
            continue
        check.require(name not in chosen, f"Duplicate package in this build: {name}")
        check_metadata(info, records[name], kernel)
        chosen[name] = source
    check.require(set(chosen) == set(records), f"Missing same-build packages: {sorted(set(records) - set(chosen))}")
    # These checks require real signatures; no force or allow-untrusted options.
    run(apk, "--keys-dir", trusted, "verify", *chosen.values())
    output.mkdir(parents=True)
    packages = []
    for name in sorted(chosen):
        source = chosen[name]
        destination = output / source.name
        check.require(not destination.exists(), "Colliding APK filenames")
        shutil.copyfile(source, destination)
        packages.append(destination)
    # The selected packages were signed at mkpkg time by the local build patch.
    # Only the public key is exported. The native private key stays in the build tree.
    shutil.copyfile(public_key, output / public_key.name)
    index = output / "packages.adb"
    run(apk, "--keys-dir", trusted, "mkndx", "--hash", "sha256", "--sign-key", private_key, "--output", index, *packages)
    run(apk, "--keys-dir", trusted, "verify", index, *packages)
    entries = json.loads(run(apk, "adbdump", "--format", "json", index))["packages"]
    check.require(len(entries) == len(records) and {entry["name"] for entry in entries} == set(records),
                  "Signed repository index has a different package set")
    for entry in entries:
        check_record(entry, records[entry["name"]], kernel)
    with tempfile.TemporaryDirectory(prefix="rax3000m-apk-solver-", dir=output.parent) as temporary:
        solver = Path(temporary)
        (solver / "lib/apk/db").mkdir(parents=True)
        (solver / "etc/apk").mkdir(parents=True)
        (solver / "lib/apk/db/installed").write_text("")
        (solver / "etc/apk/world").write_text("")
        # Run the real dependency solver on an empty database. Query executes no scripts.
        selected = json.loads(run(
            apk, "--root", solver, "--arch", check.ARCH, "--keys-dir", trusted,
            "--repositories-file", "/dev/null", "--repository", index.as_uri(),
            "--no-network", "--no-cache", "query", "--from", "none", "--recursive",
            "--format", "json", "--fields", "name,version,arch,depends",
            *(f"{name}={records[name]['V']}" for name in sorted(records))))
    check.require({entry["name"]: entry["version"] for entry in selected} ==
                  {name: record["V"] for name, record in records.items()},
                  "Offline dependency solver does not reproduce the installed package set")
    hashes = {path.name: check.digest(path) for path in [*packages, index, output / public_key.name]}
    (output / "SHA256SUMS").write_text("".join(f"{hashes[name]}  {name}\n" for name in sorted(hashes)))
    report = {
        "status": "passed", "image": artifact["image"], "image_sha256": artifact["sha256"],
        "kernel_package_version": kernel, "package_count": len(packages),
        "architectures": sorted({record["A"] for record in records.values()}),
        "individual_apk_signatures": "verified with keys trusted by this image",
        "index_signature": "verified with keys trusted by this image",
        "installed_content_identities": "all matched", "offline_dependency_solver": "passed",
        "public_key_sha256": check.digest(public_key), "index_sha256": check.digest(index),
        "private_key_exported": False, "packages": {name: records[name]["V"] for name in sorted(records)},
        "sha256": hashes,
    }
    (output / "package-repository-check.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tree", type=Path)
    parser.add_argument("artifact_report", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        result = collect(args.tree, json.loads(args.artifact_report.read_text()), args.output)
    except (OSError, RuntimeError, KeyError, ValueError) as error:
        print(f"matching-packages: FAILED: {error}", flush=True)
        raise SystemExit(1) from error
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(f"matching-packages: passed; {result['package_count']} signed APKs; report: {args.report}", flush=True)


if __name__ == "__main__":
    main()
