"""Execution isolation for untrusted, model-generated code.

Backends
--------
docker   Each command runs in a throwaway container with: no network, a read-only
         root filesystem, a size-limited noexec /tmp, all Linux capabilities
         dropped, no-new-privileges, a non-root user, memory / CPU / PID limits,
         a scrubbed environment, and ONLY the working directory mounted.
         This is the recommended backend for any deployment.

process  A child Python process with a scrubbed environment, CPU and memory
         rlimits, and a wall-clock timeout. It provides NO filesystem or network
         isolation and must not be used for untrusted code in production.

Selection
---------
Set ``AI_TOOLS_ISOLATION`` to ``auto`` (default), ``docker``, or ``process``.

* ``docker``  fails closed: raises ``IsolationError`` if Docker or the image is missing.
* ``auto``    uses Docker when the daemon and sandbox image are available; otherwise
              falls back to ``process`` and says so in the result's ``warning`` field.
* ``process`` always uses the process backend (intended for development only).

The sandbox image is set by ``AI_TOOLS_SANDBOX_IMAGE`` and built from the repository
``Dockerfile`` (``make docker``).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

ISOLATION_ENV = "AI_TOOLS_ISOLATION"
IMAGE_ENV = "AI_TOOLS_SANDBOX_IMAGE"
DEFAULT_IMAGE = "ai-agent-tools-sandbox:1.0.0"
MODES = ("auto", "docker", "process")

MEMORY_LIMIT = "256m"
CPU_LIMIT = "1"
PIDS_LIMIT = "128"
TMPFS_SPEC = "/tmp:rw,noexec,nosuid,nodev,size=64m"  # noqa: S108 - container-internal tmpfs, not a host path
CONTAINER_WORKDIR = "/work"
NOBODY_UID = 65534

_PROCESS_CPU_SECONDS = 30
_PROCESS_MEMORY_BYTES = 512 * 1024 * 1024
_WARNING_PROCESS_FALLBACK = (
    "Docker isolation is unavailable, so the code ran with process-level isolation only. "
    "Do not use this result path for untrusted code in production."
)


class IsolationError(RuntimeError):
    """Raised when a requested isolation backend cannot be used."""


@dataclass
class ExecResult:
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None
    timed_out: bool = False
    isolation: str = "process"
    warning: str | None = None


def sandbox_image() -> str:
    return os.environ.get(IMAGE_ENV, DEFAULT_IMAGE)


def _docker_ready() -> bool:
    """True when the Docker daemon answers and the sandbox image is present locally."""
    if shutil.which("docker") is None:
        return False
    try:
        daemon = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if daemon.returncode != 0:
            return False
        image = subprocess.run(
            ["docker", "image", "inspect", sandbox_image()],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return image.returncode == 0


def resolve_backend(requested: str | None = None) -> tuple[str, str | None]:
    """Return ``(backend, warning)`` where backend is ``"docker"`` or ``"process"``."""
    mode = (requested or os.environ.get(ISOLATION_ENV, "auto")).strip().lower()
    if mode not in MODES:
        raise ValueError(f"Unknown isolation mode '{mode}'. Expected one of: {', '.join(MODES)}.")
    if mode == "process":
        return "process", None
    ready = _docker_ready()
    if mode == "docker":
        if not ready:
            raise IsolationError(
                "Docker isolation was requested, but the Docker daemon or sandbox image "
                f"'{sandbox_image()}' is unavailable. Build it with `make docker`."
            )
        return "docker", None
    if ready:
        return "docker", None
    return "process", _WARNING_PROCESS_FALLBACK


def _container_user() -> str:
    """Run as the invoking host user, or as nobody when the host runs as root."""
    if hasattr(os, "getuid") and os.getuid() != 0:
        return f"{os.getuid()}:{os.getgid()}"
    return f"{NOBODY_UID}:{NOBODY_UID}"


def build_docker_argv(args: list[str], workdir: Path, *, name: str, interactive: bool) -> list[str]:
    """Build the ``docker run`` command line. Pure function, safe to unit-test."""
    argv = [
        "docker",
        "run",
        "--rm",
        "--name",
        name,
        # Network: none. Nothing inside can reach the internet or the host network.
        "--network",
        "none",
        # Filesystem: read-only root, one writable scratch tmpfs, and the workdir only.
        "--read-only",
        "--tmpfs",
        TMPFS_SPEC,
        "--volume",
        f"{workdir}:{CONTAINER_WORKDIR}:rw",
        "--workdir",
        CONTAINER_WORKDIR,
        # Privileges: no capabilities, no privilege escalation, non-root user.
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--user",
        _container_user(),
        # Resources.
        "--memory",
        MEMORY_LIMIT,
        "--memory-swap",
        MEMORY_LIMIT,
        "--cpus",
        CPU_LIMIT,
        "--pids-limit",
        PIDS_LIMIT,
        # Environment: explicit only. Host variables are never forwarded.
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--env",
        "PYTHONIOENCODING=utf-8",
        "--env",
        "HOME=/tmp",
    ]
    if interactive:
        argv.append("--interactive")
    argv.append(sandbox_image())
    argv.extend(args)
    return argv


def _process_env(workdir: Path) -> dict[str, str]:
    """Minimal environment for the process backend. Host secrets are not inherited."""
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        "HOME": str(workdir),
        "TMPDIR": str(workdir),
    }


def _limit_process_resources() -> None:  # pragma: no cover - runs in the child
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (_PROCESS_CPU_SECONDS, _PROCESS_CPU_SECONDS + 1))
    resource.setrlimit(resource.RLIMIT_AS, (_PROCESS_MEMORY_BYTES, _PROCESS_MEMORY_BYTES))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def run_isolated(
    args: list[str],
    *,
    workdir: Path,
    timeout: float,
    stdin: str | None = None,
    backend: str | None = None,
) -> ExecResult:
    """
    Run ``python <args>`` with the selected isolation backend.

    ``args`` are arguments to the Python interpreter, e.g. ``["-I", "-"]``.
    ``workdir`` is the only host directory visible to the executed code under Docker.
    """
    resolved_backend, warning = resolve_backend(backend)
    workdir = Path(workdir).resolve()

    if resolved_backend == "docker":
        name = f"aitools-{uuid.uuid4().hex[:12]}"
        argv = build_docker_argv(
            ["python", *args], workdir, name=name, interactive=stdin is not None
        )
        env = None  # the docker CLI needs the host environment; the container does not get it
        preexec = None
    else:
        name = None
        argv = [sys.executable, *args]
        env = _process_env(workdir)
        preexec = _limit_process_resources if os.name == "posix" else None

    try:
        proc = subprocess.run(
            argv,
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workdir,
            env=env,
            preexec_fn=preexec,
        )
        return ExecResult(
            stdout=_as_text(proc.stdout),
            stderr=_as_text(proc.stderr),
            returncode=proc.returncode,
            isolation=resolved_backend,
            warning=warning,
        )
    except subprocess.TimeoutExpired as exc:
        if name is not None:
            # Killing the docker CLI does not stop the container; remove it explicitly.
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=10)
        return ExecResult(
            stdout=_as_text(exc.stdout),
            stderr=_as_text(exc.stderr)
            + f"\nTimeoutExpired: execution exceeded {timeout} seconds.",
            returncode=None,
            timed_out=True,
            isolation=resolved_backend,
            warning=warning,
        )
