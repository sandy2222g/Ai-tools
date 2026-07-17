"""
Research Summarizer Agent
==========================
Autonomous web-research agent powered by Claude + five sandboxed tools.

  web_search  – DuckDuckGo search (no API key)
  fetch_page  – clean plain-text page fetcher, 10 s timeout
  save_note   – persist a focused note to ./research_sandbox/notes/
  list_notes  – enumerate saved notes
  read_note   – retrieve a note by title

Usage
-----
  export ANTHROPIC_API_KEY=sk-ant-...
  python research_agent/agent.py
  python research_agent/agent.py --topic "your topic here"
  python research_agent/agent.py --model claude-opus-4-5 --max-iter 25

Requires
--------
  pip install anthropic requests beautifulsoup4 duckduckgo_search
"""

import argparse
import json
import textwrap

import anthropic

# Import the five tools and their Anthropic-ready schemas from the shared module.
from tools.research_tools.tool import (
    TOOLS_ANTHROPIC,
    execute_tool as _dispatch,
    fetch_page as _raw_fetch,
)

# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_MODEL    = "claude-sonnet-4-6"
DEFAULT_MAX_ITER = 20
MAX_FETCH        = 8          # hard cap on fetch_page calls per session

# ──────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are an expert research assistant. Your job is to investigate a topic
thoroughly and produce a well-structured summary backed by real sources.

Work in this order — do NOT skip steps:
1. Always call web_search first to discover relevant URLs.
2. Call fetch_page on at least 3 different pages before saving any notes.
3. Save one focused note per source with save_note (title = source topic,
   not the URL). Do not cram everything into one giant note.
4. After saving notes, call list_notes to confirm what you have collected.
5. Write the final summary only after reviewing your notes.

Final answer format (required — do not deviate):
## Summary: <topic>
### Key Findings
- <finding 1>
- <finding 2>
- <finding 3>
### Sources
- <page title> — <url>
### Confidence
<One sentence: how consistent and reliable were the sources?>
"""

# ──────────────────────────────────────────────────────────────────────────────
# FETCH GUARD — wraps execute_tool to enforce MAX_FETCH
# ──────────────────────────────────────────────────────────────────────────────

def _make_guarded_dispatcher(max_fetch: int = MAX_FETCH):
    """
    Return a dispatcher that intercepts fetch_page calls and enforces
    a per-session page-fetch cap. All other tools pass through unchanged.
    """
    fetch_count = {"n": 0}

    def execute_tool(name: str, inputs: dict) -> str:
        if name == "fetch_page":
            if fetch_count["n"] >= max_fetch:
                return json.dumps({
                    "url":     inputs.get("url", ""),
                    "content": None,
                    "error":   (
                        f"MAX_FETCH limit ({max_fetch}) reached. "
                        "Use your saved notes to write the summary."
                    ),
                })
            fetch_count["n"] += 1
        return _dispatch(name, inputs)

    return execute_tool

# ──────────────────────────────────────────────────────────────────────────────
# AGENT LOOP
# ──────────────────────────────────────────────────────────────────────────────

def run_agent(topic: str, model: str = DEFAULT_MODEL,
              max_iterations: int = DEFAULT_MAX_ITER) -> str:
    """Agentic research loop using the Anthropic SDK (Claude models)."""
    client       = anthropic.Anthropic()       # reads ANTHROPIC_API_KEY from env
    execute_tool = _make_guarded_dispatcher()  # fresh fetch counter per session

    history = [{"role": "user", "content": f"Research this topic: {topic}"}]

    print(f"[agent] Model: {model} | Topic: {topic}\n")

    for iteration in range(1, max_iterations + 1):
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            tools=TOOLS_ANTHROPIC,
            messages=history,
        )
        stop_reason = response.stop_reason

        if stop_reason == "tool_use":
            history.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                raw = execute_tool(block.name, block.input)
                print(
                    f"[iter {iteration:2d}] tool: {block.name:<12} | "
                    f"result: {textwrap.shorten(raw, 200, placeholder='…')}"
                )
                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": block.id,
                    "content":     raw,
                })
            history.append({"role": "user", "content": tool_results})

        elif stop_reason == "end_turn":
            final = next(
                (b.text for b in response.content if hasattr(b, "text")),
                "(No text returned)",
            )
            print(f"\n{'─' * 60}\nFinal answer:\n{final}\n{'─' * 60}")
            return final

        else:
            print(f"[iter {iteration}] Unexpected stop_reason: '{stop_reason}'. Stopping.")
            break

    print(f"[agent] Reached max iterations ({max_iterations}).")
    return ""

# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────

SAMPLE_TOPICS = [
    "latest developments in AI agent frameworks 2025",
    "how do large language models handle tool use internally",
]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous research summarizer agent")
    parser.add_argument(
        "--topic", type=str, default=None,
        help="Research topic. Omit to run both sample topics sequentially.",
    )
    parser.add_argument(
        "--model", type=str, default=DEFAULT_MODEL,
        help=f"Claude model name (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--max-iter", type=int, default=DEFAULT_MAX_ITER,
        help=f"Max tool-call iterations per topic (default: {DEFAULT_MAX_ITER})",
    )
    args = parser.parse_args()

    topics = [args.topic] if args.topic else SAMPLE_TOPICS
    for topic in topics:
        print(f"\n{'═' * 60}")
        print(f"  TOPIC: {topic}")
        print(f"{'═' * 60}\n")
        run_agent(topic, model=args.model, max_iterations=args.max_iter)
