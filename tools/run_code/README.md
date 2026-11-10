# run_code

A sandboxed Python executor for AI agents.

Runs untrusted, model-written Python with a hard timeout and returns `stdout`, `stderr`, `exit_code`, `timed_out`, and the isolation level used — as a dict ready to send back to the LLM.

## Isolation

| Backend | When | What it enforces |
|---------|------|------------------|
| `docker` | Docker daemon up and sandbox image built (`make docker`) | No network, read-only root filesystem, no Linux capabilities, no-new-privileges, non-root user, memory/CPU/PID limits, scrubbed environment, only a fresh temp directory mounted |
| `process` | Fallback when Docker is unavailable | Scrubbed environment, CPU and memory rlimits, timeout. **No filesystem or network isolation.** |

Selection is controlled by `AI_TOOLS_ISOLATION`:

- `auto` (default): Docker if available, otherwise `process`. A fallback always sets `warning` in the result.
- `docker`: fails closed if Docker is unavailable.
- `process`: development only.

The model cannot choose the backend. `isolation` is deliberately **not** in `tool_schema.json`, so an agent can't downgrade its own sandbox.

## Files

| File | Purpose |
|------|---------|
| `tool.py` | `run_code()` and `load_schema()` |
| `tool_schema.json` | JSON tool definition for OpenAI / Gemini / Anthropic function calling |
| `__init__.py` | Package marker |

## Usage

```python
from tools.run_code import run_code

result = run_code("print(2 + 2)")
# {'stdout': '4\n', 'stderr': '', 'exit_code': 0, 'timed_out': False,
#  'isolation': 'docker', 'warning': None}
```

## Parameters

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `code` | `str` | required | Python source code. Passed over stdin; never written to the host. |
| `timeout` | `float` | `5.0` | Seconds before the execution is killed. |
| `isolation` | `str \| None` | `None` | `auto`, `docker`, or `process`. Host operators only. |

## Return Shape

```json
{
  "stdout": "4\n",
  "stderr": "",
  "exit_code": 0,
  "timed_out": false,
  "isolation": "docker",
  "warning": null
}
```

## Dependencies

None for the tool itself. Docker is needed for the `docker` backend. See [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md).
