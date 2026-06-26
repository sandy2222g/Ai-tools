# file_tools package
# Exposes sandboxed read_file, write_file, list_files, and their LLM schema loader.
import json
from pathlib import Path
from .tool import read_file, write_file, list_files

__all__ = ["read_file", "write_file", "list_files", "load_schema"]


def load_schema() -> list:
    """
    Load and return the tool definition schemas from tool_schema.json.

    Returns:
        list: A list of tool schema dicts (read_file, write_file, list_files).
    """
    schema_path = Path(__file__).parent / "tool_schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)
