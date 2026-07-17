"""
Organizer-agent tool implementations
=====================================
Five sandboxed filesystem tools for an autonomous file-organiser agent.
All paths are restricted to ``./organizer_sandbox/`` via _safe_path().

Tools
-----
  list_files      – enumerate directory contents with type + extension fields
  move_file       – move a file; refuses to overwrite an existing destination
  rename_file     – rename in place; refuses path-separator smuggling
  create_folder   – mkdir -p inside the sandbox
  get_file_info   – stat metadata (size, mtime, type) without reading contents

Schema helpers
--------------
  TOOLS_ANTHROPIC – list[dict] ready to pass to client.messages.create(tools=…)
  TOOLS_OPENAI    – list[dict] ready for OpenAI / Ollama function-calling
  execute_tool    – dispatcher used by the agent loop
"""

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# SANDBOX — all operations are restricted to this directory
# ──────────────────────────────────────────────────────────────────────────────

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SANDBOX = os.path.realpath(os.path.join(_REPO_ROOT, "organizer_sandbox"))
os.makedirs(SANDBOX, exist_ok=True)


def _safe_path(path: str) -> str:
    """Resolve *path* inside SANDBOX; raise ValueError if it escapes."""
    full = os.path.realpath(os.path.join(SANDBOX, path))
    if not full.startswith(os.path.realpath(SANDBOX)):
        raise ValueError(f"Path '{path}' escapes the sandbox.")
    return full


# ──────────────────────────────────────────────────────────────────────────────
# TOOL IMPLEMENTATIONS
# ──────────────────────────────────────────────────────────────────────────────

def list_files(path: str = ".") -> dict:
    """
    Tool name: list_files
    Description: List the immediate contents of a directory inside the sandbox.
      Returns each entry's name, type ('file' | 'dir'), and file extension
      (e.g. '.pdf', '.py', or null for directories / extension-less files)
      so the agent can group by type without parsing names.

    Parameters:
      path (str): Relative directory path inside the sandbox. Defaults to '.'.

    Returns:
      files  – list of {name, type, extension} dicts, sorted by name
      error  – null on success, error string on failure
    """
    try:
        resolved = _safe_path(path)
        if not os.path.isdir(resolved):
            return {"files": None, "error": f"Not a directory: '{path}'"}
        entries = []
        for name in sorted(os.listdir(resolved)):
            full = os.path.join(resolved, name)
            is_dir = os.path.isdir(full)
            ext = None if is_dir else (os.path.splitext(name)[1] or None)
            entries.append({"name": name, "type": "dir" if is_dir else "file", "extension": ext})
        return {"files": entries, "error": None}
    except Exception as exc:
        return {"files": None, "error": str(exc)}


def move_file(src: str, dst: str) -> dict:
    """
    Tool name: move_file
    Description: Move a file from src to dst (both relative to the sandbox root).
      Creates the destination directory tree if it does not exist.
      Refuses to overwrite an existing file at dst — returns an error instead.

    Parameters:
      src (str): Relative source path inside the sandbox.
      dst (str): Relative destination path inside the sandbox.

    Returns:
      success – true on success
      error   – null on success, error string on failure
    """
    try:
        src_full = _safe_path(src)
        dst_full = _safe_path(dst)
        if not os.path.exists(src_full):
            return {"success": False, "error": f"Source not found: '{src}'"}
        if os.path.exists(dst_full):
            return {"success": False, "error": f"Destination already exists: '{dst}'"}
        os.makedirs(os.path.dirname(dst_full), exist_ok=True)
        shutil.move(src_full, dst_full)
        return {"success": True, "error": None}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def rename_file(path: str, new_name: str) -> dict:
    """
    Tool name: rename_file
    Description: Rename a file or directory to new_name in the same parent
      directory. new_name must be a plain filename — path separators are
      rejected to prevent covert moves disguised as renames.

    Parameters:
      path     (str): Relative path to the file or directory inside the sandbox.
      new_name (str): New filename only (no slashes or subdirectory components).

    Returns:
      success – true on success
      error   – null on success, error string on failure
    """
    try:
        if os.sep in new_name or "/" in new_name:
            return {"success": False, "error": f"new_name must not contain path separators: '{new_name}'"}
        src_full = _safe_path(path)
        if not os.path.exists(src_full):
            return {"success": False, "error": f"Path not found: '{path}'"}
        dst_full = os.path.join(os.path.dirname(src_full), new_name)
        if os.path.exists(dst_full):
            return {"success": False, "error": f"A file named '{new_name}' already exists in that directory."}
        os.rename(src_full, dst_full)
        return {"success": True, "error": None}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def create_folder(path: str) -> dict:
    """
    Tool name: create_folder
    Description: Create a new subdirectory at path inside the sandbox,
      including any missing intermediate directories (equivalent to mkdir -p).
      Succeeds silently if the folder already exists.

    Parameters:
      path (str): Relative path of the directory to create inside the sandbox.

    Returns:
      success – true on success (or if folder already existed)
      error   – null on success, error string on failure
    """
    try:
        resolved = _safe_path(path)
        os.makedirs(resolved, exist_ok=True)
        return {"success": True, "error": None}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def get_file_info(path: str) -> dict:
    """
    Tool name: get_file_info
    Description: Return metadata about a file or directory without reading its
      contents. Useful for making agent decisions based on file size or age.

    Parameters:
      path (str): Relative path inside the sandbox.

    Returns:
      name       – basename of the entry
      extension  – file extension (e.g. '.pdf') or null for dirs / no extension
      size_bytes – file size in bytes (0 for directories)
      modified   – last-modified timestamp in ISO 8601 format, UTC
      type       – 'file' | 'dir'
      error      – null on success, error string on failure
    """
    try:
        resolved = _safe_path(path)
        if not os.path.exists(resolved):
            return {"name": None, "extension": None, "size_bytes": None,
                    "modified": None, "type": None, "error": f"Path not found: '{path}'"}
        stat = os.stat(resolved)
        is_dir = os.path.isdir(resolved)
        name = os.path.basename(resolved)
        ext = None if is_dir else (os.path.splitext(name)[1] or None)
        modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        return {
            "name": name,
            "extension": ext,
            "size_bytes": stat.st_size,
            "modified": modified,
            "type": "dir" if is_dir else "file",
            "error": None,
        }
    except Exception as exc:
        return {"name": None, "extension": None, "size_bytes": None,
                "modified": None, "type": None, "error": str(exc)}


# ──────────────────────────────────────────────────────────────────────────────
# TOOL SCHEMAS — shared definitions, then Anthropic + OpenAI derived views
# ──────────────────────────────────────────────────────────────────────────────

_TOOL_DEFS = [
    {
        "name": "list_files",
        "description": (
            "List the immediate contents of a directory inside the sandbox. "
            "Returns each entry's name, type ('file' | 'dir'), and file extension "
            "(e.g. '.pdf', or null for directories) so the agent can group by type."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative directory path inside the sandbox. Defaults to '.'.",
                    "default": ".",
                },
            },
            "required": [],
        },
    },
    {
        "name": "move_file",
        "description": (
            "Move a file from src to dst (both relative to the sandbox root). "
            "Creates the destination directory if needed. "
            "Refuses to overwrite an existing file — returns an error instead."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "src": {
                    "type": "string",
                    "description": "Relative source path inside the sandbox, e.g. 'report.pdf'.",
                },
                "dst": {
                    "type": "string",
                    "description": "Relative destination path inside the sandbox, e.g. 'Documents/report.pdf'.",
                },
            },
            "required": ["src", "dst"],
        },
    },
    {
        "name": "rename_file",
        "description": (
            "Rename a file or directory to new_name within its current parent directory. "
            "new_name must be a plain filename with no path separators. "
            "Refuses to rename if the target name already exists."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file or directory inside the sandbox.",
                },
                "new_name": {
                    "type": "string",
                    "description": "New filename only (no slashes), e.g. 'budget_2024.xlsx'.",
                },
            },
            "required": ["path", "new_name"],
        },
    },
    {
        "name": "create_folder",
        "description": (
            "Create a new subdirectory at path inside the sandbox (like mkdir -p). "
            "Creates intermediate directories as needed. "
            "Succeeds silently if the folder already exists."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path of the folder to create, e.g. 'Images/Vacation'.",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "get_file_info",
        "description": (
            "Return metadata (name, extension, size_bytes, modified timestamp, type) "
            "about a file or directory without reading its contents. "
            "Useful for agent decisions based on file size or age."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path inside the sandbox, e.g. 'report.pdf'.",
                },
            },
            "required": ["path"],
        },
    },
]

# Anthropic format — uses "input_schema" key
TOOLS_ANTHROPIC = [
    {"name": t["name"], "description": t["description"], "input_schema": t["schema"]}
    for t in _TOOL_DEFS
]

# OpenAI / Ollama format — wrapped in a "function" object with "parameters" key
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
# DISPATCHER
# ──────────────────────────────────────────────────────────────────────────────

_TOOL_MAP = {
    "list_files":   list_files,
    "move_file":    move_file,
    "rename_file":  rename_file,
    "create_folder": create_folder,
    "get_file_info": get_file_info,
}


def execute_tool(name: str, inputs: dict) -> str:
    """
    Call the named tool with *inputs* and return the result as a JSON string.
    Unknown tool names and unhandled exceptions are returned as JSON error objects.
    """
    fn = _TOOL_MAP.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool '{name}'."})
    try:
        return json.dumps(fn(**inputs))
    except Exception as exc:
        return json.dumps({"error": f"Tool '{name}' raised: {exc}"})
