# file_tools

Sandboxed `read_file`, `write_file`, and `list_files` for AI agents.

All file operations are restricted to a configurable sandbox directory (`./sandbox/` by default). Any path that resolves outside the sandbox is rejected — protecting against `../` traversal attacks.

## Files

| File | Purpose |
|------|---------|
| `tool.py` | Core implementation — `read_file()`, `write_file()`, `list_files()`, and `_safe_path()` |
| `tool_schema.json` | JSON tool definitions (array of three schemas) |
| `__init__.py` | Package marker |

## Usage

```python
from tools.file_tools import read_file, write_file, list_files

# List files
result = list_files(".", sandbox_dir="./sandbox")
# {'files': ['solution.py', 'test_solution.py', 'utils/'], 'error': None}

# Read a file
result = read_file("solution.py", sandbox_dir="./sandbox")
# {'content': 'print("hello")\n', 'error': None}

# Write a file
result = write_file("solution.py", "print('fixed')\n", sandbox_dir="./sandbox")
# {'success': True, 'error': None}

# Path traversal → blocked
result = list_files("../", sandbox_dir="./sandbox")
# {'files': None, 'error': "Path traversal blocked: ..."}
```

## Schema

```python
from tools.file_tools import load_schema

schemas = load_schema()  # returns a list of three tool definitions
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

**list_files:**
```json
{"files": ["solution.py", "utils/"], "error": null}
{"files": [], "error": null}
{"files": null, "error": "error message"}
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

### list_files

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `path` | `str` | `"."` | Relative path to a directory inside the sandbox |
| `sandbox_dir` | `str` | `"./sandbox"` | Override the sandbox root |

## Dependencies

None — standard library only (`pathlib`, `os`).
