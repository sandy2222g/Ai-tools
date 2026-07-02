# AI Agent Tools

A growing collection of lightweight, dependency-free Python tools for AI agents that use function/tool calling.

Each tool lives in its own folder under `tools/`, is self-contained, and ships with a JSON schema you can pass directly to any LLM API (OpenAI, Gemini, Anthropic, etc.).

---

## Tool Catalog

| Tool | Description | Dependencies |
|------|-------------|--------------|
| [run_code](./tools/run_code/) | Execute Python snippets in an isolated subprocess. Returns `stdout`, `stderr`, `exit_code`, `timed_out`. | None (stdlib only) |
| [file_tools](./tools/file_tools/) | Sandboxed `read_file`, `write_file`, and `list_files` with path-traversal protection. | None (stdlib only) |
| [run_tests](./tools/run_tests/) | Runs pytest on a test file inside the sandbox. Returns structured test counts and failures. | None (stdlib only) |

---

## Project Structure

```
ai-agent-tools/
├── README.md                  ← You are here
├── .gitignore
│
├── tools/                     ← One folder per tool
│   ├── run_code/
│   │   ├── __init__.py
│   │   ├── tool.py
│   │   ├── tool_schema.json
│   │   └── README.md
│   ├── file_tools/
│   │   ├── __init__.py
│   │   ├── tool.py
│   │   ├── tool_schema.json
│   │   └── README.md
│   └── run_tests/
│       ├── __init__.py
│       ├── tool.py
│       ├── tool_schema.json
│       └── README.md
│
└── examples/                  ← End-to-end integration demos
    └── gemini_agent.py        ← Gemini agent loop using run_code
```

---

## Quick Start

All tools work the same way — import the function, call it, get a dict back:

```python
from tools.run_code import run_code

result = run_code("print('hello from the agent!')")
print(result)
# {'stdout': 'hello from the agent!\n', 'stderr': '', 'exit_code': 0, 'timed_out': False}
```

---

## Using a Tool with an LLM

Every tool ships a `tool_schema.json` and a `load_schema()` helper:

```python
from tools.run_code import load_schema

schema = load_schema()  # pass this to your LLM API as the tool definition
```

See [`examples/gemini_agent.py`](./examples/gemini_agent.py) for a complete, annotated agent loop that wires `run_code` into Google Gemini's function-calling API.

```bash
pip install google-generativeai

# Windows PowerShell
$env:GEMINI_API_KEY = "your-key-here"

py examples/gemini_agent.py
```

---

## Adding a New Tool

Each tool follows this convention:

```
tools/<tool_name>/
├── __init__.py          # exposes the main function + load_schema
├── tool.py              # implementation
├── tool_schema.json     # LLM-compatible JSON tool definition
└── README.md            # tool-specific docs
```

The `tool_schema.json` follows the standard OpenAI function-calling schema and is compatible with Gemini and Anthropic APIs too.

---

## Design Philosophy

- **No unnecessary dependencies** — tools use the standard library wherever possible.
- **One function per tool** — simple, composable, easy to test.
- **Subprocess isolation** — any tool that runs external code does so in a child process, never with `eval()` or `exec()`.
- **Python 3.8+** — no bleeding-edge syntax.

---

## Requirements

- Python 3.8+
- `google-generativeai` — only needed for `examples/gemini_agent.py`
