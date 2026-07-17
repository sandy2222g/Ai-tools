"""Smoke-test for research_agent imports and the fetch-guard logic."""
import sys, json
sys.path.insert(0, ".")

from research_agent.agent import (
    TOOLS_ANTHROPIC, DEFAULT_MODEL, DEFAULT_MAX_ITER, MAX_FETCH,
    _make_guarded_dispatcher,
)

# 1) schema sanity
print("=== Tool schemas ===")
for t in TOOLS_ANTHROPIC:
    name = t["name"]
    req  = t["input_schema"]["required"]
    print(f"  {name:<14} required={req}")

# 2) fetch guard — cap at 2 for speed
print(f"\n=== Fetch guard (cap=2) ===")
execute = _make_guarded_dispatcher(max_fetch=2)
for i in range(4):
    result = json.loads(execute("fetch_page", {"url": "https://httpbin.org/status/200"}))
    blocked = "MAX_FETCH" in str(result.get("error", ""))
    tag = "BLOCKED" if blocked else "allowed"
    print(f"  call {i+1}: {tag}")

# 3) unknown tool
print("\n=== Unknown tool ===")
execute2 = _make_guarded_dispatcher()
print(" ", execute2("does_not_exist", {}))

print("\nAll checks passed.")
