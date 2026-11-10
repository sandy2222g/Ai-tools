"""Unit tests for the isolation layer. These check the security configuration itself."""

from pathlib import Path

import pytest

from tools._common import isolation
from tools._common.isolation import IsolationError, build_docker_argv, resolve_backend


def _argv(tmp_path: Path) -> list[str]:
    return build_docker_argv(["python", "-I", "-"], tmp_path, name="t1", interactive=True)


def _flag_value(argv: list[str], flag: str) -> str:
    return argv[argv.index(flag) + 1]


def test_docker_network_is_disabled(tmp_path):
    assert _flag_value(_argv(tmp_path), "--network") == "none"


def test_docker_root_filesystem_is_read_only(tmp_path):
    assert "--read-only" in _argv(tmp_path)


def test_docker_drops_all_capabilities_and_blocks_escalation(tmp_path):
    argv = _argv(tmp_path)
    assert _flag_value(argv, "--cap-drop") == "ALL"
    assert _flag_value(argv, "--security-opt") == "no-new-privileges"


def test_docker_runs_as_non_root(tmp_path, monkeypatch):
    monkeypatch.setattr(isolation.os, "getuid", lambda: 0)
    assert _flag_value(_argv(tmp_path), "--user") == "65534:65534"
    monkeypatch.setattr(isolation.os, "getuid", lambda: 1000)
    monkeypatch.setattr(isolation.os, "getgid", lambda: 1000)
    assert _flag_value(_argv(tmp_path), "--user") == "1000:1000"


def test_docker_has_resource_limits(tmp_path):
    argv = _argv(tmp_path)
    assert _flag_value(argv, "--memory") == isolation.MEMORY_LIMIT
    assert _flag_value(argv, "--memory-swap") == isolation.MEMORY_LIMIT
    assert _flag_value(argv, "--pids-limit") == isolation.PIDS_LIMIT
    assert _flag_value(argv, "--cpus") == isolation.CPU_LIMIT


def test_docker_mounts_only_the_workdir(tmp_path):
    argv = _argv(tmp_path)
    mounts = [argv[i + 1] for i, a in enumerate(argv) if a == "--volume"]
    assert mounts == [f"{tmp_path}:{isolation.CONTAINER_WORKDIR}:rw"]
    assert not any("docker.sock" in a for a in argv)


def test_docker_does_not_forward_host_environment(tmp_path):
    argv = _argv(tmp_path)
    env_pairs = [argv[i + 1] for i, a in enumerate(argv) if a == "--env"]
    assert all("=" in pair for pair in env_pairs)
    assert not any(
        pair.startswith(("PATH=", "AWS_", "ANTHROPIC_", "OPENAI_")) for pair in env_pairs
    )


def test_docker_image_and_command_come_last(tmp_path, monkeypatch):
    monkeypatch.setenv(isolation.IMAGE_ENV, "example/sandbox:test")
    argv = _argv(tmp_path)
    assert argv[-4:] == ["example/sandbox:test", "python", "-I", "-"]


def test_explicit_process_mode_skips_docker_probe(monkeypatch):
    def boom():
        raise AssertionError("docker must not be probed in process mode")

    monkeypatch.setattr(isolation, "_docker_ready", boom)
    assert resolve_backend("process") == ("process", None)


def test_unknown_mode_raises():
    with pytest.raises(ValueError):
        resolve_backend("nonsense")


def test_docker_mode_raises_when_unavailable(monkeypatch):
    monkeypatch.setattr(isolation, "_docker_ready", lambda: False)
    with pytest.raises(IsolationError):
        resolve_backend("docker")


def test_auto_uses_docker_when_ready(monkeypatch):
    monkeypatch.setattr(isolation, "_docker_ready", lambda: True)
    assert resolve_backend("auto") == ("docker", None)


def test_auto_warns_when_falling_back(monkeypatch):
    monkeypatch.setattr(isolation, "_docker_ready", lambda: False)
    backend, warning = resolve_backend("auto")
    assert backend == "process"
    assert warning
