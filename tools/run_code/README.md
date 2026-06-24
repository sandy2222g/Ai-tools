# run_code

A sandboxed Python code executor for AI agents.

Executes untrusted Python snippets in an isolated subprocess with a hard timeout, and returns `stdout`, `stderr`, `exit_code`, and `timed_out` as a dict — ready to send back to the LLM.

## Files

| File | Purpose |
|------|---------|
| `tool.py` | Core implementation — `run_code()` and `load_schema()` |
| `tool_schema.json` | JSON tool definition for OpenAI / Gemini function-calling APIs |
| `__init__.py` | Package marker |

## Usage

```python
from tools.run_code import run_code

result = run_code("print(2 + 2)")
# {'stdout': '4\n', 'stderr': '', 'exit_code': 0, 'timed_out': False}
```

## Schema

```python
from tools.run_code import load_schema

schema = load_schema()  # returns the dict from tool_schema.json
```

## Return Shape

```json
{
  "stdout": "4\n",
  "stderr": "",
  "exit_code": 0,
  "timed_out": false
}
```

## Parameters

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `code` | `str` | required | Python source code to execute |
| `timeout` | `float` | `5.0` | Seconds before the process is killed |

## Dependencies

None — standard library only (`subprocess`, `tempfile`, `sys`, `pathlib`).
