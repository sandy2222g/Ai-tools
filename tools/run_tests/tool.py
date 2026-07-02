import re
import sys
import subprocess
import json
from pathlib import Path

SANDBOX_DIR = Path("./sandbox").resolve()


def run_tests(test_file: str, timeout: int = 10) -> dict:
    """
    Runs pytest on test_file inside the sandbox directory.

    Parameters:
    - test_file (str): Relative path to the test file inside the sandbox.
    - timeout (int): Hard execution timeout in seconds. Defaults to 10.

    Returns:
    - dict: A dictionary containing test counts, summary, failures, and error status.
    """
    res = {"passed": 0, "failed": 0, "errors": 0, "summary": "0 passed", "failures": [], "timed_out": False, "error": None}
    sandbox = SANDBOX_DIR
    try:
        resolved = (sandbox / test_file).resolve()
        if not str(resolved).startswith(str(sandbox)):
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

    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", "-v", str(resolved)], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        res["timed_out"] = True
        return res
    except Exception as e:
        res["error"] = str(e)
        return res

    if "No module named pytest" in proc.stderr:
        res["error"] = "pytest is not installed"
        return res

    output = f"{proc.stdout}\n{proc.stderr}"
    for line in output.splitlines():
        if line.startswith(("FAILED ", "ERROR ")):
            res["failures"].append(" — ".join(line.split(" - ", 1)) if " - " in line else line)

    sum_line = next((l for l in reversed(output.splitlines()) if " in " in l and any(k in l for k in ["passed", "failed", "error", "no tests ran"])), "")
    if sum_line:
        m_p, m_f, m_e = re.search(r"(\d+)\s+passed", sum_line), re.search(r"(\d+)\s+failed", sum_line), re.search(r"(\d+)\s+error", sum_line)
        res["passed"] = int(m_p.group(1)) if m_p else 0
        res["failed"] = int(m_f.group(1)) if m_f else 0
        res["errors"] = int(m_e.group(1)) if m_e else 0

    parts = []
    if res["passed"]: parts.append(f"{res['passed']} passed")
    if res["failed"]: parts.append(f"{res['failed']} failed")
    if res["errors"]: parts.append(f"{res['errors']} error{'s' if res['errors'] > 1 else ''}")
    res["summary"] = ", ".join(parts) if parts else "0 passed"
    return res


def load_schema() -> dict:
    """
    Load and return the tool definition schema from tool_schema.json.
    """
    schema_path = Path(__file__).parent / "tool_schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)
