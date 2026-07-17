"""
Research-summarizer agent tool implementations
================================================
Five tools for an autonomous web-research agent.
Web operations use requests + BeautifulSoup + duckduckgo_search.
Notes are persisted to ``./research_sandbox/notes/`` as plain .txt files.

Tools
-----
  web_search  – DuckDuckGo search, deduped by URL, no API key needed
  fetch_page  – fetch + strip HTML to clean plain text, 10 s timeout
  save_note   – write a titled note to the notes directory
  list_notes  – enumerate saved notes with filename + size
  read_note   – read a note back by title

Schema helpers
--------------
  TOOLS_ANTHROPIC – list[dict] ready to pass to client.messages.create(tools=…)
  TOOLS_OPENAI    – list[dict] ready for OpenAI / Ollama function-calling
  execute_tool    – dispatcher used by the agent loop

Dependencies (pip install):
  requests  beautifulsoup4  duckduckgo_search
"""

import json
import os
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

# ──────────────────────────────────────────────────────────────────────────────
# NOTES DIRECTORY — created automatically on import
# ──────────────────────────────────────────────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parents[3]
NOTES_DIR  = _REPO_ROOT / "research_sandbox" / "notes"
NOTES_DIR.mkdir(parents=True, exist_ok=True)


def _title_to_filename(title: str) -> str:
    """Derive a safe .txt filename from an arbitrary note title."""
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9\s_]", "", slug)   # strip non-alphanumeric (keep spaces + _)
    slug = re.sub(r"\s+", "_", slug)             # spaces → underscores
    slug = re.sub(r"_+", "_", slug).strip("_")   # collapse duplicate underscores
    return f"{slug}.txt"


# ──────────────────────────────────────────────────────────────────────────────
# TOOL IMPLEMENTATIONS
# ──────────────────────────────────────────────────────────────────────────────

def web_search(query: str, max_results: int = 5) -> dict:
    """
    Tool name: web_search
    Description: Search the web using DuckDuckGo (no API key required) and
      return a deduplicated list of results. Each result includes a title,
      URL, and short snippet. Use this to discover relevant pages before
      fetching their full content with fetch_page.

    Parameters:
      query       (str): The search query string.
      max_results (int): Maximum number of results to return. Defaults to 5.

    Returns:
      results – list of {title, url, snippet} dicts
      error   – null on success, error string on failure
    """
    try:
        seen_urls: set[str] = set()
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results * 2):  # over-fetch to allow dedup
                url = r.get("href", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                results.append({
                    "title":   r.get("title", ""),
                    "url":     url,
                    "snippet": r.get("body", ""),
                })
                if len(results) >= max_results:
                    break
        return {"results": results, "error": None}
    except Exception as exc:
        return {"results": [], "error": str(exc)}


def fetch_page(url: str, max_chars: int = 3000) -> dict:
    """
    Tool name: fetch_page
    Description: Fetch a webpage and return clean plain text with no HTML tags,
      scripts, styles, or navigation boilerplate. Only paragraph and heading
      text is kept. Content is truncated to max_chars characters to keep
      LLM context manageable. Handles 404s, timeouts, and non-HTML responses
      (PDFs, images) gracefully — all returned as error strings.

    Parameters:
      url       (str): The full URL to fetch.
      max_chars (int): Maximum characters of text to return. Defaults to 3000.

    Returns:
      url     – the requested URL (echoed back for traceability)
      content – clean plain-text content, truncated to max_chars
      error   – null on success, error string on failure
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (research-agent/1.0)"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            return {"url": url, "content": None,
                    "error": f"Non-HTML content-type: '{content_type}'"}

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header",
                          "aside", "form", "noscript", "iframe"]):
            tag.decompose()

        chunks = []
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "p"]):
            text = tag.get_text(" ", strip=True)
            if text:
                chunks.append(text)

        content = "\n\n".join(chunks)[:max_chars]
        return {"url": url, "content": content or "(no readable text found)", "error": None}
    except requests.exceptions.Timeout:
        return {"url": url, "content": None, "error": "Request timed out after 10 seconds."}
    except requests.exceptions.HTTPError as exc:
        return {"url": url, "content": None, "error": f"HTTP error: {exc}"}
    except Exception as exc:
        return {"url": url, "content": None, "error": str(exc)}


def save_note(title: str, content: str) -> dict:
    """
    Tool name: save_note
    Description: Save a research note as a plain .txt file inside the notes
      directory. The filename is derived from the title (lowercased, spaces
      replaced with underscores, special characters stripped). Overwrites any
      existing note with the same derived filename.

    Parameters:
      title   (str): Human-readable note title, e.g. 'Agentic AI Overview'.
      content (str): The note body to save.

    Returns:
      success  – true on success
      filename – the derived filename (e.g. 'agentic_ai_overview.txt')
      error    – null on success, error string on failure
    """
    try:
        filename = _title_to_filename(title)
        if not filename or filename == ".txt":
            return {"success": False, "filename": None,
                    "error": f"Could not derive a valid filename from title: '{title}'"}
        path = NOTES_DIR / filename
        path.write_text(content, encoding="utf-8")
        return {"success": True, "filename": filename, "error": None}
    except Exception as exc:
        return {"success": False, "filename": None, "error": str(exc)}


def list_notes() -> dict:
    """
    Tool name: list_notes
    Description: List all saved notes in the notes directory. Returns each
      note's display title (derived from filename), the actual filename, and
      its size in bytes. Use this to see what research has already been saved
      before deciding what to read or overwrite.

    Parameters:
      (none)

    Returns:
      notes – list of {title, filename, size_bytes} dicts, sorted by filename
      error – null on success, error string on failure
    """
    try:
        notes = []
        for p in sorted(NOTES_DIR.glob("*.txt")):
            title = p.stem.replace("_", " ").title()
            notes.append({
                "title":      title,
                "filename":   p.name,
                "size_bytes": p.stat().st_size,
            })
        return {"notes": notes, "error": None}
    except Exception as exc:
        return {"notes": None, "error": str(exc)}


def read_note(title: str) -> dict:
    """
    Tool name: read_note
    Description: Read the contents of a saved note by its title. The filename
      is derived the same way as save_note, so titles must match. Returns an
      error if no note with that derived filename exists.

    Parameters:
      title (str): The note title to read, e.g. 'Agentic AI Overview'.

    Returns:
      title   – the requested title (echoed back)
      content – full note text on success
      error   – null on success, error string on failure
    """
    try:
        filename = _title_to_filename(title)
        path = NOTES_DIR / filename
        if not path.exists():
            return {"title": title, "content": None,
                    "error": f"Note not found: '{filename}'"}
        return {"title": title, "content": path.read_text(encoding="utf-8"), "error": None}
    except Exception as exc:
        return {"title": title, "content": None, "error": str(exc)}


# ──────────────────────────────────────────────────────────────────────────────
# TOOL SCHEMAS — shared definitions, then Anthropic + OpenAI derived views
# ──────────────────────────────────────────────────────────────────────────────

_TOOL_DEFS = [
    {
        "name": "web_search",
        "description": (
            "Search the web using DuckDuckGo (no API key required) and return a "
            "deduplicated list of results with title, URL, and snippet. "
            "Use this first to discover relevant pages, then fetch them with fetch_page."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query string.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return. Defaults to 5.",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_page",
        "description": (
            "Fetch a webpage and return clean plain text (no HTML, scripts, or nav boilerplate). "
            "Content is truncated to max_chars characters. "
            "Handles 404s, timeouts, and non-HTML files gracefully."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL to fetch, e.g. 'https://example.com/article'.",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum characters of plain text to return. Defaults to 3000.",
                    "default": 3000,
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "save_note",
        "description": (
            "Save a research note as a .txt file in the notes directory. "
            "Filename is derived from the title (slug form). "
            "Overwrites an existing note with the same derived filename."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Human-readable note title, e.g. 'Agentic AI Overview'.",
                },
                "content": {
                    "type": "string",
                    "description": "The note body / key points to save.",
                },
            },
            "required": ["title", "content"],
        },
    },
    {
        "name": "list_notes",
        "description": (
            "List all saved notes in the notes directory. "
            "Returns each note's display title, filename, and size in bytes. "
            "Use to check what research has already been saved."
        ),
        "schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "read_note",
        "description": (
            "Read the full contents of a saved note by its title. "
            "Uses the same filename derivation as save_note. "
            "Returns an error if the note does not exist."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The note title to read, e.g. 'Agentic AI Overview'.",
                },
            },
            "required": ["title"],
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
    "web_search":  web_search,
    "fetch_page":  fetch_page,
    "save_note":   save_note,
    "list_notes":  list_notes,
    "read_note":   read_note,
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
