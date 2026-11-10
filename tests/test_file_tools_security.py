"""Security regression tests for path confinement in the sandboxed file tools."""

from pathlib import Path

import pytest

from tools.file_tools.tool import _safe_path, list_files, read_file, write_file


def test_sibling_directory_with_shared_prefix_is_blocked(tmp_path: Path):
    # Regression: a string-prefix check accepted "<root>/sandbox_evil" for "<root>/sandbox".
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    (tmp_path / "sandbox_evil").mkdir()

    with pytest.raises(ValueError, match="Path traversal blocked"):
        _safe_path("../sandbox_evil/secret.txt", sandbox)


@pytest.mark.parametrize(
    "malicious",
    ["../outside.txt", "../../etc/passwd", "/etc/passwd", "a/../../outside.txt"],
)
def test_traversal_variants_are_blocked(tmp_path: Path, malicious: str):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    with pytest.raises(ValueError):
        _safe_path(malicious, sandbox)


def test_symlink_escape_is_blocked(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("classified", encoding="utf-8")
    (sandbox / "link").symlink_to(outside, target_is_directory=True)

    result = read_file("link/secret.txt", sandbox_dir=str(sandbox))
    assert result["content"] is None
    assert "Path traversal blocked" in result["error"]


def test_write_outside_sandbox_is_rejected_and_nothing_written(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    result = write_file("../escaped.txt", "x", sandbox_dir=str(sandbox))
    assert result["success"] is False
    assert not (tmp_path / "escaped.txt").exists()


def test_list_files_rejects_escape(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    result = list_files("..", sandbox_dir=str(sandbox))
    assert result["files"] is None
    assert result["error"]


def test_legitimate_nested_path_is_allowed(sandbox: Path):
    result = write_file("src/app/main.py", "print('ok')", sandbox_dir=str(sandbox))
    assert result == {"success": True, "error": None}
    assert read_file("src/app/main.py", sandbox_dir=str(sandbox))["content"] == "print('ok')"
