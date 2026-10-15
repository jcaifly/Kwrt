"""Extract a delivered sysupgrade rootfs for offline inspection only."""

import hashlib
import os
from pathlib import Path
import re
import subprocess
import tarfile


def unpack_rootfs(image: Path, workdir: Path, unsquashfs: Path, device: str) -> tuple[Path, dict]:
    """Read one regular TAR root payload, then strictly unpack it as a normal user.

    ``workdir`` must not already exist. It and the full subprocess logs are kept
    on failure. Only the supplied host unsquashfs tool runs; no firmware program
    is executed, and successful extraction does not establish device behavior.
    """
    if os.geteuid() == 0:
        raise ValueError("Rootfs extraction must run as a non-root user")
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", device):
        raise ValueError(f"Invalid sysupgrade device name: {device!r}")

    image = Path(image).resolve()
    unsquashfs = Path(unsquashfs).resolve()
    # Do not resolve first: a dangling workdir symlink must also be rejected.
    workdir = Path(workdir).absolute()
    try:
        workdir.mkdir(mode=0o700)
    except FileExistsError as error:
        raise ValueError(f"Rootfs work directory must be new: {workdir}") from error
    workdir = workdir.resolve()
    root = workdir / "rootfs"
    payload = workdir / "root.squashfs"
    member_name = f"sysupgrade-{device}/root"

    with image.open("rb") as source:
        image_sha256 = hashlib.file_digest(source, "sha256").hexdigest()
        source.seek(0)
        try:
            with tarfile.open(fileobj=source, mode="r:") as archive:
                members = [member for member in archive if member.name == member_name]
                if len(members) != 1:
                    raise ValueError(
                        f"Expected exactly one TAR member {member_name!r}, found {len(members)}"
                    )
                member = members[0]
                if (member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE)
                        or member.sparse is not None
                        or any(key.startswith("GNU.sparse.") for key in member.pax_headers)):
                    raise ValueError(f"TAR root member must be an ordinary regular file: {member_name}")
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError(f"Cannot read TAR root member: {member_name}")
                payload_digest = hashlib.sha256()
                with stream, payload.open("xb") as output:
                    while chunk := stream.read(1024 * 1024):
                        output.write(chunk)
                        payload_digest.update(chunk)
        except tarfile.TarError as error:
            raise ValueError(f"Cannot read sysupgrade TAR root payload: {error}") from error

    stdout_log = workdir / "unsquashfs.stdout.log"
    stderr_log = workdir / "unsquashfs.stderr.log"
    command = [
        str(unsquashfs), "-strict-errors", "-no-progress", "-processors", "2",
        "-dest", "rootfs", "-exclude-list", "dev/console", ";", "root.squashfs",
    ]
    with stdout_log.open("wb") as stdout, stderr_log.open("wb") as stderr:
        try:
            result = subprocess.run(
                command, cwd=workdir, stdin=subprocess.DEVNULL,
                stdout=stdout, stderr=stderr, check=False,
            )
        except OSError as error:
            stderr.write(f"Cannot start unsquashfs: {error}\n".encode())
            raise RuntimeError(
                f"Cannot start unsquashfs; full logs: {stdout_log}, {stderr_log}"
            ) from error
    if result.returncode != 0:
        raise RuntimeError(
            f"unsquashfs failed with exit status {result.returncode}; "
            f"full logs: {stdout_log}, {stderr_log}"
        )
    if not root.is_dir():
        raise RuntimeError(f"unsquashfs did not create {root}; full logs: {stdout_log}, {stderr_log}")

    return root, {
        "status": "passed",
        "image": str(image),
        "image_sha256": image_sha256,
        "root_member": member_name,
        "root_payload": str(payload),
        "root_payload_sha256": payload_digest.hexdigest(),
        "rootfs": str(root),
        "strict_errors": True,
        "excluded_paths": ["dev/console"],
        "unsquashfs": str(unsquashfs),
        "unsquashfs_command": command,
        "unsquashfs_returncode": result.returncode,
        "unsquashfs_stdout_log": str(stdout_log),
        "unsquashfs_stderr_log": str(stderr_log),
        "firmware_programs_executed": False,
        "validation_scope": "Offline rootfs extraction only; no device boot or runtime validation",
    }
