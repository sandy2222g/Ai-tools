import subprocess
import tempfile
import os
import sys
import json
from pathlib import Path

def run_code(code: str, timeout: float = 5.0) -> dict:
    """
    Executes Python source code in an isolated subprocess with a timeout.

    Parameters:
    - code (str): A string containing valid Python source code to execute.
    - timeout (float): Hard execution timeout in seconds. Defaults to 5.0.

    Returns:
    - dict: A dictionary containing:
        - stdout (str): Captured standard output.
        - stderr (str): Captured standard error.
        - exit_code (int or None): Subprocess exit code (None if timed out or failed).
        - timed_out (bool): True if execution timed out, False otherwise.
    """
    res = {"stdout": "", "stderr": "", "exit_code": None, "timed_out": False}
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        temp_path = f.name
    try:
        proc = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        res.update({"stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode})
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
        res.update({
            "stdout": stdout,
            "stderr": stderr + f"\nTimeoutExpired: Code execution timed out after {timeout} seconds.",
            "timed_out": True
        })
    except Exception as e:
        res["stderr"] = f"Execution error: {str(e)}"
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass
    return res


def load_schema() -> dict:
    """
    Load and return the tool definition schema from tool_schema.json.

    Usage:
        from run_code_tool.tool import run_code, load_schema
        schema = load_schema()  # pass to your LLM API as the tool definition

    Returns:
        dict: The full tool schema (name, description, parameters, returns).
    """
    schema_path = Path(__file__).parent / "tool_schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)
