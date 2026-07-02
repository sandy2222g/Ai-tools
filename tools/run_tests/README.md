# run_tests

A sandboxed pytest executor for AI agents.

Runs pytest on a specified test file inside the sandbox directory. Captures and returns structured outcome counts, a human-readable summary, and trimmed failure/error messages.

## Files

| File | Purpose |
|------|---------|
| `tool.py` | Core implementation — `run_tests()` and `load_schema()` |
| `tool_schema.json` | JSON tool definition for OpenAI / Gemini function-calling APIs |
| `__init__.py` | Package marker |

## Usage

```python
from tools.run_tests import run_tests

result = run_tests("test_solution.py")
# {
#   "passed": 3,
#   "failed": 1,
#   "errors": 0,
#   "summary": "3 passed, 1 failed",
#   "failures": ["FAILED test_solution.py::test_edge_case — assert 0 == 1"],
#   "timed_out": False,
#   "error": None
# }
```

## Schema

```python
from tools.run_tests import load_schema

schema = load_schema()  # returns the dict from tool_schema.json
```

## Return Shape

```json
{
  "passed": 3,
  "failed": 1,
  "errors": 0,
  "summary": "3 passed, 1 failed",
  "failures": ["FAILED test_solution.py::test_edge_case — assert 0 == 1"],
  "timed_out": false,
  "error": null
}
```

## Parameters

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `test_file` | `str` | required | Relative path to the test file inside the sandbox |
| `timeout` | `int` | `10` | Seconds before the process is killed |

## Dependencies

None — standard library only (`subprocess`, `re`, `pathlib`, `sys`, `json`). Requires `pytest` to be installed in the target environment where the subprocess runs.
