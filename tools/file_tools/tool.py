import os
from pathlib import Path

# Default sandbox directory — all file operations are restricted to this folder.
SANDBOX_DIR = Path("./sandbox").resolve()


def _safe_path(path: str, sandbox: Path = SANDBOX_DIR) -> Path:
    """
    Resolve `path` against the sandbox and verify it doesn't escape.
    Returns the resolved Path, or raises ValueError if it's outside the sandbox.
    """
    resolved = (sandbox / path).resolve()
    if not str(resolved).startswith(str(sandbox)):
        raise ValueError(f"Path traversal blocked: '{path}' resolves outside the sandbox.")
    return resolved


def read_file(path: str, sandbox_dir: str = None) -> dict:
    """
    Reads the contents of a file within the sandbox directory.

    Parameters:
    - path (str): Relative path to the file inside the sandbox.
    - sandbox_dir (str): Optional override for the sandbox root directory.

    Returns:
    - dict:
        - content (str | None): File contents on success, None on failure.
        - error (str | None): Error message on failure, None on success.
    """
    sandbox = Path(sandbox_dir).resolve() if sandbox_dir else SANDBOX_DIR
    try:
        resolved = _safe_path(path, sandbox)
        return {"content": resolved.read_text(encoding="utf-8"), "error": None}
    except Exception as e:
        return {"content": None, "error": str(e)}


def write_file(path: str, content: str, sandbox_dir: str = None) -> dict:
    """
    Writes content to a file within the sandbox directory, creating
    parent directories if needed. Overwrites if the file already exists.

    Parameters:
    - path (str): Relative path to the file inside the sandbox.
    - content (str): The text content to write.
    - sandbox_dir (str): Optional override for the sandbox root directory.

    Returns:
    - dict:
        - success (bool): True if the write succeeded.
        - error (str | None): Error message on failure, None on success.
    """
    sandbox = Path(sandbox_dir).resolve() if sandbox_dir else SANDBOX_DIR
    try:
        resolved = _safe_path(path, sandbox)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        return {"success": True, "error": None}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_files(path: str = ".", sandbox_dir: str = None) -> dict:
    """
    Lists immediate contents of a directory within the sandbox.
    Skips hidden files/directories (names starting with '.').
    Appends '/' to directory names to distinguish them from files.

    Parameters:
    - path (str): Relative path to a directory inside the sandbox. Defaults to ".".
    - sandbox_dir (str): Optional override for the sandbox root directory.

    Returns:
    - dict:
        - files (list[str] | None): Sorted list of entry names on success, None on failure.
        - error (str | None): Error message on failure, None on success.
    """
    sandbox = Path(sandbox_dir).resolve() if sandbox_dir else SANDBOX_DIR
    try:
        resolved = _safe_path(path, sandbox)
        if not resolved.is_dir():
            return {"files": None, "error": f"Not a directory: '{path}'"}
        entries = sorted(
            f"{entry.name}/" if entry.is_dir() else entry.name
            for entry in resolved.iterdir()
            if not entry.name.startswith(".")
        )
        return {"files": entries, "error": None}
    except Exception as e:
        return {"files": None, "error": str(e)}
