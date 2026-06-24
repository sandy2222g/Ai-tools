"""
gemini_agent.py — A minimal AI coding agent that uses run_code as a tool.

Usage:
    Run from the repo root:
        py examples/gemini_agent.py

    Requires:
        pip install google-generativeai
"""

import os
import json
import google.generativeai as genai
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))  # repo root
from tools.run_code.tool import run_code

# ── 1. Configure Gemini ───────────────────────────────────────────────────────
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise EnvironmentError(
        "GEMINI_API_KEY environment variable is not set.\n"
        "Get a free key at: https://aistudio.google.com/apikey"
    )

genai.configure(api_key=api_key)

# ── 2. Declare the tool schema ─────────────────────────────────────────────────
# This JSON is sent to Gemini so it knows when and how to call run_code.
TOOL_SCHEMA = genai.protos.Tool(
    function_declarations=[
        genai.protos.FunctionDeclaration(
            name="run_code",
            description=(
                "Executes a Python code snippet in an isolated subprocess. "
                "Returns stdout, stderr, exit_code (int), and timed_out (bool). "
                "Use this to verify that code actually works before presenting it to the user."
            ),
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "code": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="The Python source code to execute.",
                    )
                },
                required=["code"],
            ),
        )
    ]
)

# ── 3. Tool dispatcher ─────────────────────────────────────────────────────────
# Routes LLM tool-call requests to the correct Python function.
def dispatch(function_name: str, args: dict) -> dict:
    if function_name == "run_code":
        return run_code(args["code"])
    raise ValueError(f"Unknown tool: {function_name}")

# ── 4. The agent loop ──────────────────────────────────────────────────────────
def run_agent(user_prompt: str, max_turns: int = 8) -> None:
    """
    Runs the LLM → tool → LLM loop until the model produces a final text
    answer or we hit the max_turns safety limit.
    """
    model = genai.GenerativeModel("gemini-1.5-pro", tools=[TOOL_SCHEMA])
    chat  = model.start_chat()

    print(f"\n{'='*60}")
    print(f"USER: {user_prompt}")
    print(f"{'='*60}\n")

    message = user_prompt  # First message is just the user's text

    for turn in range(max_turns):
        response = chat.send_message(message)
        part     = response.candidates[0].content.parts[0]

        # ── The LLM is calling a tool ─────────────────────────────────────────
        if part.HasField("function_call"):
            fc     = part.function_call
            args   = dict(fc.args)

            print(f"[Turn {turn+1}] LLM called tool: '{fc.name}'")
            if "code" in args:
                print(f"  Code snippet:\n    " +
                      "\n    ".join(args["code"].strip().splitlines()))

            # Execute the tool
            result = dispatch(fc.name, args)

            print(f"  → exit_code={result['exit_code']}  "
                  f"timed_out={result['timed_out']}")
            if result["stdout"]:
                print(f"  stdout: {result['stdout'].strip()}")
            if result["stderr"]:
                print(f"  stderr: {result['stderr'].strip()[:300]}")
            print()

            # Feed tool result back to the LLM as a "function response"
            message = genai.protos.Content(
                role="tool",
                parts=[
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=fc.name,
                            response={"result": result},
                        )
                    )
                ],
            )

        # ── The LLM produced a final text answer ──────────────────────────────
        else:
            print(f"[FINAL ANSWER]\n{part.text}")
            return

    print("[WARN] Hit max_turns limit — agent did not converge.")


# ── 5. Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run_agent(
        "Write and run Python to find the first 10 prime numbers, "
        "then explain how the code works."
    )
