import json
import re
from pathlib import Path

from tools._common.isolation import IsolationError, run_isolated

SANDBOX_DIR = Path("./sandbox").resolve()


def run_tests(test_file: str, timeout: int = 10, isolation: str | None = None) -> dict:
    """
    Runs pytest on test_file inside the sandbox directory.

    Parameters:
    - test_file (str): Relative path to the test file inside the sandbox.
    - timeout (int): Hard execution timeout in seconds. Defaults to 10.
    - isolation (str | None): ``"auto"``, ``"docker"``, or ``"process"``. Defaults to
      the ``AI_TOOLS_ISOLATION`` environment variable, or ``"auto"``.

    Returns:
    - dict: A dictionary containing test counts, summary, failures, error status,
      the isolation backend used, and a warning if a weaker backend was used.
    """
    res = {
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "summary": "0 passed",
        "failures": [],
        "timed_out": False,
        "error": None,
        "isolation": None,
        "warning": None,
    }
    sandbox = SANDBOX_DIR
    try:
        resolved = (sandbox / test_file).resolve()
        if not resolved.is_relative_to(sandbox.resolve()):
            res["error"] = f"Path traversal blocked: '{test_file}' resolves outside the sandbox."
        elif not resolved.exists():
            res["error"] = f"File not found: '{test_file}'"
        elif not resolved.is_file():
            res["error"] = f"Not a file: '{test_file}'"
        if res["error"]:
            return res
    except Exception as e:
        res["error"] = str(e)
        return res

    # Run pytest through the isolation layer. The sandbox is the only host directory
    # visible under Docker, so the test path is passed relative to it.
    try:
        proc = run_isolated(
            [
                "-m",
                "pytest",
                "-v",
                "--tb=short",
                "--no-header",
                "-p",
                "no:cacheprovider",
                resolved.relative_to(sandbox.resolve()).as_posix(),
            ],
            workdir=sandbox.resolve(),
            timeout=timeout,
            backend=isolation,
        )
    except (IsolationError, ValueError) as e:
        res["error"] = f"{type(e).__name__}: {e}"
        return res
    except OSError as e:
        res["error"] = str(e)
        return res

    res["isolation"] = proc.isolation
    res["warning"] = proc.warning
    if proc.timed_out:
        res["timed_out"] = True
        return res

    if "No module named pytest" in proc.stderr:
        res["error"] = "pytest is not installed in the execution environment"
        return res

    output = f"{proc.stdout}\n{proc.stderr}"
    for line in output.splitlines():
        if line.startswith(("FAILED ", "ERROR ")):
            res["failures"].append(" — ".join(line.split(" - ", 1)) if " - " in line else line)

    sum_line = next(
        (
            ln
            for ln in reversed(output.splitlines())
            if " in " in ln and any(k in ln for k in ["passed", "failed", "error", "no tests ran"])
        ),
        "",
    )
    if sum_line:
        m_p, m_f, m_e = (
            re.search(r"(\d+)\s+passed", sum_line),
            re.search(r"(\d+)\s+failed", sum_line),
            re.search(r"(\d+)\s+error", sum_line),
        )
        res["passed"] = int(m_p.group(1)) if m_p else 0
        res["failed"] = int(m_f.group(1)) if m_f else 0
        res["errors"] = int(m_e.group(1)) if m_e else 0

    parts = []
    if res["passed"]:
        parts.append(f"{res['passed']} passed")
    if res["failed"]:
        parts.append(f"{res['failed']} failed")
    if res["errors"]:
        parts.append(f"{res['errors']} error{'s' if res['errors'] > 1 else ''}")
    res["summary"] = ", ".join(parts) if parts else "0 passed"
    return res


def load_schema() -> dict:
    """
    Load and return the tool definition schema from tool_schema.json.
    """
    schema_path = Path(__file__).parent / "tool_schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)
