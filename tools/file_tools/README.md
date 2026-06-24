# file_tools

Sandboxed `read_file` and `write_file` for AI agents.

All file operations are restricted to a configurable sandbox directory (`./sandbox/` by default). Any path that resolves outside the sandbox is rejected — protecting against `../` traversal attacks.

## Files

| File | Purpose |
|------|---------|
| `tool.py` | Core implementation — `read_file()`, `write_file()`, and `_safe_path()` |
| `tool_schema.json` | JSON tool definitions (array of two schemas) |
| `__init__.py` | Package marker |

## Usage

```python
from tools.file_tools import read_file, write_file

# Read a file
result = read_file("solution.py", sandbox_dir="./sandbox")
# {'content': 'print("hello")\n', 'error': None}

# Write a file
result = write_file("solution.py", "print('fixed')\n", sandbox_dir="./sandbox")
# {'success': True, 'error': None}

# Path traversal → blocked
result = read_file("../secrets.txt", sandbox_dir="./sandbox")
# {'content': None, 'error': "Path traversal blocked: ..."}
```

## Schema

```python
from tools.file_tools import load_schema

schemas = load_schema()  # returns a list of two tool definitions
```

## Return Shapes

**read_file:**
```json
{"content": "file text here...", "error": null}
{"content": null, "error": "error message"}
```

**write_file:**
```json
{"success": true, "error": null}
{"success": false, "error": "error message"}
```

## Parameters

### read_file

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `path` | `str` | required | Relative path inside the sandbox |
| `sandbox_dir` | `str` | `"./sandbox"` | Override the sandbox root |

### write_file

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `path` | `str` | required | Relative path inside the sandbox |
| `content` | `str` | required | Text to write |
| `sandbox_dir` | `str` | `"./sandbox"` | Override the sandbox root |

## Dependencies

None — standard library only (`pathlib`, `os`).
