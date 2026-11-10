import json
import tempfile
from pathlib import Path

from tools._common.isolation import IsolationError, run_isolated


def run_code(code: str, timeout: float = 5.0, isolation: str | None = None) -> dict:
    """
    Executes Python source code in an isolated environment with a timeout.

    Under the default ``auto`` mode the code runs in a Docker container with no network,
    a read-only filesystem, and no capabilities. Without Docker it falls back to a
    scrubbed child process and reports that in ``isolation`` and ``warning``.

    Parameters:
    - code (str): Python source code to execute. Passed over stdin; never written to the host.
    - timeout (float): Hard execution timeout in seconds. Defaults to 5.0.
    - isolation (str | None): ``"auto"``, ``"docker"``, or ``"process"``.
      Defaults to the ``AI_TOOLS_ISOLATION`` environment variable, or ``"auto"``.

    Returns:
    - dict:
        - stdout (str): Captured standard output.
        - stderr (str): Captured standard error.
        - exit_code (int or None): Exit code, or None if timed out or the run failed.
        - timed_out (bool): True if execution exceeded the timeout.
        - isolation (str | None): Backend actually used: ``"docker"`` or ``"process"``.
        - warning (str | None): Set when a weaker backend was used than requested.
    """
    res = {
        "stdout": "",
        "stderr": "",
        "exit_code": None,
        "timed_out": False,
        "isolation": None,
        "warning": None,
    }
    if not isinstance(code, str):
        res["stderr"] = "code must be a string."
        return res

    # A fresh, empty working directory per call. Under Docker it is the only mount.
    with tempfile.TemporaryDirectory(prefix="run_code-") as workdir:
        try:
            result = run_isolated(
                ["-I", "-"],  # -I: isolated mode (ignores PYTHON* env vars and user site)
                workdir=Path(workdir),
                timeout=timeout,
                stdin=code,
                backend=isolation,
            )
        except (IsolationError, ValueError) as exc:
            res["stderr"] = f"{type(exc).__name__}: {exc}"
            return res
        except OSError as exc:
            res["stderr"] = f"Execution error: {exc}"
            return res

    res.update(
        {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "timed_out": result.timed_out,
            "isolation": result.isolation,
            "warning": result.warning,
        }
    )
    return res


def load_schema() -> dict:
    """
    Load and return the tool definition schema from tool_schema.json.

    Usage:
        from tools.run_code import run_code, load_schema
        schema = load_schema()  # pass to your LLM API as the tool definition

    Returns:
        dict: The full tool schema (name, description, parameters, returns).
    """
    schema_path = Path(__file__).parent / "tool_schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)
