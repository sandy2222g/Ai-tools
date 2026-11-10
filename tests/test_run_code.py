"""Tests for the isolated run_code executor."""

from tools.run_code.tool import run_code


def test_captures_stdout_and_exit_code():
    result = run_code("print('hello')")
    assert result["stdout"].strip() == "hello"
    assert result["exit_code"] == 0
    assert result["timed_out"] is False


def test_reports_nonzero_exit_and_stderr():
    result = run_code("import sys; sys.stderr.write('boom'); sys.exit(3)")
    assert result["exit_code"] == 3
    assert "boom" in result["stderr"]


def test_timeout_is_enforced():
    result = run_code("while True:\n    pass", timeout=0.5)
    assert result["timed_out"] is True
    assert "timed out" in result["stderr"].lower()


def test_temporary_file_is_removed(tmp_path, monkeypatch):
    import tools.run_code.tool as mod

    seen = {}
    real_run = mod.subprocess.run

    def spy(args, **kwargs):
        seen["path"] = args[1]
        return real_run(args, **kwargs)

    monkeypatch.setattr(mod.subprocess, "run", spy)
    run_code("x = 1")
    import os

    assert not os.path.exists(seen["path"])
