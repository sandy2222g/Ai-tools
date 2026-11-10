"""Tests for run_code. Process-backend tests are deterministic and need no Docker."""

import pytest

from tools._common import isolation
from tools.run_code.tool import run_code


def test_captures_stdout_and_exit_code():
    result = run_code("print('hello')", isolation="process")
    assert result["stdout"].strip() == "hello"
    assert result["exit_code"] == 0
    assert result["timed_out"] is False
    assert result["isolation"] == "process"


def test_reports_nonzero_exit_and_stderr():
    result = run_code("import sys; sys.stderr.write('boom'); sys.exit(3)", isolation="process")
    assert result["exit_code"] == 3
    assert "boom" in result["stderr"]


def test_timeout_is_enforced():
    result = run_code("while True:\n    pass", timeout=0.5, isolation="process")
    assert result["timed_out"] is True
    assert result["exit_code"] is None
    assert "TimeoutExpired" in result["stderr"]


def test_host_secrets_are_not_visible_to_code(monkeypatch):
    monkeypatch.setenv("AI_TOOLS_TEST_SECRET", "s3cr3t-value")
    result = run_code(
        "import os; print(os.environ.get('AI_TOOLS_TEST_SECRET', 'absent'))",
        isolation="process",
    )
    assert result["stdout"].strip() == "absent"


def test_code_is_not_written_to_a_host_file(monkeypatch):
    """Code is passed over stdin, so no source file is created for it."""
    seen = {}
    real_run = isolation.subprocess.run

    def spy(args, **kwargs):
        seen["argv"] = list(args)
        seen["input"] = kwargs.get("input")
        return real_run(args, **kwargs)

    monkeypatch.setattr(isolation.subprocess, "run", spy)
    run_code("print('x')", isolation="process")
    assert seen["input"] == "print('x')"
    assert "-I" in seen["argv"] and "-" in seen["argv"]


def test_auto_mode_falls_back_to_process_with_warning(monkeypatch):
    monkeypatch.setattr(isolation, "_docker_ready", lambda: False)
    monkeypatch.delenv("AI_TOOLS_ISOLATION", raising=False)
    result = run_code("print(1)")
    assert result["isolation"] == "process"
    assert result["warning"] and "process-level isolation" in result["warning"]
    assert result["stdout"].strip() == "1"


def test_docker_mode_fails_closed_when_unavailable(monkeypatch):
    monkeypatch.setattr(isolation, "_docker_ready", lambda: False)
    result = run_code("print(1)", isolation="docker")
    assert result["exit_code"] is None
    assert "IsolationError" in result["stderr"]
    assert result["stdout"] == ""


def test_unknown_isolation_mode_is_rejected():
    result = run_code("print(1)", isolation="yolo")
    assert "ValueError" in result["stderr"]


@pytest.mark.parametrize("bad", [None, 42, b"print(1)"])
def test_non_string_code_is_rejected(bad):
    result = run_code(bad)
    assert result["exit_code"] is None
    assert "must be a string" in result["stderr"]
