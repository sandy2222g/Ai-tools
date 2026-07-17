"""
Autonomous Code-Debugging Agent
================================
Supports two LLM backends selectable at runtime:

  • Anthropic (default) — requires ANTHROPIC_API_KEY env var
        python debug_agent/agent.py

  • Ollama local model — requires Ollama running on localhost:11434
        python debug_agent/agent.py --local
        python debug_agent/agent.py --local --model qwen2.5-coder:7b

Requires:
    pip install anthropic openai pytest
"""

import argparse
import json
import os
import subprocess
import sys
import textwrap

# Both SDKs imported; only the selected one is used at runtime.
import anthropic
from openai import OpenAI


# ──────────────────────────────────────────────────────────────────────────────
# SANDBOX — all file operations are scoped to this directory
# ──────────────────────────────────────────────────────────────────────────────

# Resolve sandbox relative to the repo root so the script works regardless of CWD.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SANDBOX = os.path.join(_REPO_ROOT, "sandbox")
os.makedirs(SANDBOX, exist_ok=True)


# ──────────────────────────────────────────────────────────────────────────────
# TOOL IMPLEMENTATIONS — five sandboxed Python functions
# ──────────────────────────────────────────────────────────────────────────────

def _safe_path(path: str) -> str:
    """Resolve *path* inside SANDBOX; raise ValueError if it escapes."""
    full = os.path.realpath(os.path.join(SANDBOX, path))
    if not full.startswith(os.path.realpath(SANDBOX)):
        raise ValueError(f"Path '{path}' escapes the sandbox.")
    return full


def run_code(code: str) -> dict:
    """Execute a Python snippet inside the sandbox; capture stdout/stderr."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=10, cwd=SANDBOX,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Timed out.", "exit_code": -1, "timed_out": True}
    except Exception as exc:
        return {"stdout": "", "stderr": str(exc), "exit_code": -1, "timed_out": False}


def read_file(path: str) -> dict:
    """Read a text file from inside the sandbox."""
    try:
        with open(_safe_path(path), "r", encoding="utf-8") as fh:
            return {"content": fh.read(), "error": None}
    except Exception as exc:
        return {"content": None, "error": str(exc)}


def write_file(path: str, content: str) -> dict:
    """Write (or overwrite) a file inside the sandbox."""
    try:
        full = _safe_path(path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        return {"success": True, "error": None}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def list_files(path: str = ".") -> dict:
    """List immediate children of a sandbox directory."""
    try:
        full = _safe_path(path)
        entries = sorted(os.listdir(full))
        return {"files": entries, "error": None}
    except Exception as exc:
        return {"files": [], "error": str(exc)}


def run_tests(test_file: str, timeout: int = 30) -> dict:
    """Run pytest on a test file inside the sandbox; return structured results."""
    try:
        full = _safe_path(test_file)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", full, "-v", "--tb=short", "--no-header"],
            capture_output=True, text=True, timeout=timeout, cwd=SANDBOX,
        )
        output = result.stdout + result.stderr
        passed = output.count(" PASSED")
        failed = output.count(" FAILED")
        errors = output.count(" ERROR")
        failures = [
            line.strip()
            for line in output.splitlines()
            if "FAILED" in line or "AssertionError" in line or ("Error" in line and "::" in line)
        ]
        return {
            "passed": passed,
            "failed": failed + errors,
            "failures": failures[:20],
            "output": output[-3000:],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        return {"passed": 0, "failed": -1, "failures": [], "output": "Timed out.", "timed_out": True}
    except Exception as exc:
        return {"passed": 0, "failed": -1, "failures": [], "output": str(exc), "timed_out": False}


# ──────────────────────────────────────────────────────────────────────────────
# TOOLS — two flavours of the same five schemas.
#
#   TOOLS_ANTHROPIC  → uses "input_schema" key  (Anthropic SDK)
#   TOOLS_OPENAI     → uses "parameters" key     (OpenAI SDK / Ollama)
#
# The tool *descriptions* are shared; only the key name differs.
# ──────────────────────────────────────────────────────────────────────────────

_TOOL_DEFS = [
    {
        "name": "run_code",
        "description": (
            "Execute an arbitrary Python snippet inside the sandbox directory. "
            "Returns stdout, stderr, exit_code, and timed_out."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Self-contained Python source code to run. Output via print().",
                },
            },
            "required": ["code"],
        },
    },
    {
        "name": "read_file",
        "description": (
            "Read the contents of a file inside the sandbox. "
            "Returns content (string) or an error message."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path inside the sandbox, e.g. 'solution.py'.",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": (
            "Write (or overwrite) a file inside the sandbox. "
            "Returns success (bool) and error (null on success)."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path inside the sandbox.",
                },
                "content": {
                    "type": "string",
                    "description": "Full file content to write.",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_files",
        "description": "List files and directories inside a sandbox path. Defaults to the sandbox root.",
        "schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative directory path to list. Defaults to '.'.",
                    "default": ".",
                },
            },
            "required": [],
        },
    },
    {
        "name": "run_tests",
        "description": (
            "Run pytest on a test file inside the sandbox. "
            "Returns passed count, failed count, failure snippets, and raw output."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "test_file": {
                    "type": "string",
                    "description": "Relative path to the pytest file, e.g. 'test_solution.py'.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Max seconds to wait before killing pytest. Defaults to 30.",
                    "default": 30,
                },
            },
            "required": ["test_file"],
        },
    },
]

# Anthropic format — `input_schema` key
TOOLS_ANTHROPIC = [
    {"name": t["name"], "description": t["description"], "input_schema": t["schema"]}
    for t in _TOOL_DEFS
]

# OpenAI / Ollama format — wrapped in a "function" object with `parameters` key
TOOLS_OPENAI = [
    {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["schema"],
        },
    }
    for t in _TOOL_DEFS
]


# ──────────────────────────────────────────────────────────────────────────────
# DISPATCHER — routes tool_use / tool_call blocks to the right Python function.
# Never raises: errors are captured and returned as JSON so the model can recover.
# ──────────────────────────────────────────────────────────────────────────────

_TOOL_MAP = {
    "run_code":   run_code,
    "read_file":  read_file,
    "write_file": write_file,
    "list_files": list_files,
    "run_tests":  run_tests,
}


def execute_tool(name: str, inputs: dict) -> str:
    """
    Call the named tool with *inputs* and return the result as a JSON string.
    Unknown tool names and exceptions are returned as JSON error objects.
    """
    fn = _TOOL_MAP.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool '{name}'."})
    try:
        return json.dumps(fn(**inputs))
    except Exception as exc:
        return json.dumps({"error": f"Tool '{name}' raised: {exc}"})


# ──────────────────────────────────────────────────────────────────────────────
# AGENT LOOP — Anthropic backend
# ──────────────────────────────────────────────────────────────────────────────

def run_agent_anthropic(user_instruction: str, model: str, max_iterations: int) -> str:
    """Agentic loop using the Anthropic SDK (Claude models)."""
    client = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY from env
    history = [{"role": "user", "content": user_instruction}]

    for iteration in range(1, max_iterations + 1):
        response = client.messages.create(
            model=model,
            max_tokens=1000,
            tools=TOOLS_ANTHROPIC,
            messages=history,
        )
        stop_reason = response.stop_reason

        if stop_reason == "tool_use":
            history.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                raw = execute_tool(block.name, block.input)
                print(f"[iter {iteration:2d}] tool: {block.name:<12} | result: {textwrap.shorten(raw, 200, placeholder='…')}")
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": raw})
            history.append({"role": "user", "content": tool_results})

        elif stop_reason == "end_turn":
            final = next((b.text for b in response.content if hasattr(b, "text")), "(No text)")
            print(f"\nFinal answer:\n{final}")
            return final

        else:
            print(f"[iter {iteration}] Unexpected stop_reason: '{stop_reason}'. Stopping.")
            break

    print(f"[agent] Reached max iterations ({max_iterations}).")
    return ""


# ──────────────────────────────────────────────────────────────────────────────
# AGENT LOOP — OpenAI-compatible backend (Ollama local models)
#
# Ollama exposes the same REST surface as the OpenAI API at:
#   http://localhost:11434/v1
# The openai Python SDK can talk to it by overriding base_url + api_key.
# Tool calling follows the OpenAI "function calling" protocol:
#   • Tools sent as TOOLS_OPENAI (type="function" wrapper)
#   • Tool calls returned in message.tool_calls[]
#   • Results sent back as role="tool" messages, one per call
# ──────────────────────────────────────────────────────────────────────────────

def run_agent_ollama(user_instruction: str, model: str, max_iterations: int) -> str:
    """Agentic loop using Ollama's OpenAI-compatible endpoint."""
    client = OpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama",           # Ollama ignores this but the SDK requires it
    )
    history = [{"role": "user", "content": user_instruction}]

    for iteration in range(1, max_iterations + 1):
        response = client.chat.completions.create(
            model=model,
            max_tokens=1000,
            tools=TOOLS_OPENAI,
            messages=history,
        )
        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        if finish_reason == "tool_calls" and message.tool_calls:
            # Append the assistant turn (with tool_calls embedded)
            history.append(message)

            # Execute every tool call and append individual tool-role messages
            for tc in message.tool_calls:
                try:
                    inputs = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    inputs = {}
                raw = execute_tool(tc.function.name, inputs)
                print(f"[iter {iteration:2d}] tool: {tc.function.name:<12} | result: {textwrap.shorten(raw, 200, placeholder='…')}")
                history.append({
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "content":      raw,
                })

        elif finish_reason == "stop":
            final = message.content or "(No text)"
            print(f"\nFinal answer:\n{final}")
            return final

        else:
            print(f"[iter {iteration}] Unexpected finish_reason: '{finish_reason}'. Stopping.")
            break

    print(f"[agent] Reached max iterations ({max_iterations}).")
    return ""


# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous code-debugging agent")
    parser.add_argument(
        "--local", action="store_true",
        help="Use a local Ollama model instead of the Anthropic API",
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help="Model name override. Defaults to 'claude-sonnet-4-6' (Anthropic) "
             "or 'qwen2.5-coder:7b' (Ollama).",
    )
    parser.add_argument(
        "--max-iter", type=int, default=10,
        help="Maximum number of tool-call iterations (default: 10)",
    )
    args = parser.parse_args()

    INSTRUCTION = (
        "List the files in the sandbox, read solution.py, run the tests in "
        "test_solution.py, identify what is failing, fix it, rerun the tests, "
        "and tell me what you changed and whether all tests now pass."
    )

    if args.local:
        model = args.model or "qwen2.5-coder:7b"
        print(f"[agent] Backend: Ollama | Model: {model}\n")
        run_agent_ollama(INSTRUCTION, model=model, max_iterations=args.max_iter)
    else:
        model = args.model or "claude-sonnet-4-6"
        print(f"[agent] Backend: Anthropic | Model: {model}\n")
        run_agent_anthropic(INSTRUCTION, model=model, max_iterations=args.max_iter)
