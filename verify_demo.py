import os
import json
import sys
from pathlib import Path

# Add the repository root to pythonpath
sys.path.insert(0, str(Path(__file__).parent))
from tools.run_tests.tool import run_tests

# Ensure sandbox directory exists
sandbox_dir = Path("./sandbox")
sandbox_dir.mkdir(exist_ok=True)

# Create a test file
test_file = sandbox_dir / "test_demo.py"
test_file.write_text("""
def test_one_passes():
    assert 1 + 1 == 2

def test_two_fails():
    assert 1 + 1 == 99

def test_three_errors():
    raise ValueError("Something went wrong!")
""", encoding="utf-8")

print("Executing run_tests('test_demo.py')...")
result = run_tests("test_demo.py")

print("\nResult:")
print(json.dumps(result, indent=2))

# Clean up
if test_file.exists():
    test_file.unlink()
