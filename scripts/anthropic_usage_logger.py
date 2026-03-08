"""
Log Anthropic API token usage so you can correlate with Claude Console Cost/Logs.

Usage:
  1. One-off: run this script to make a single test call and log usage to a file.
     Set ANTHROPIC_API_KEY and optionally PROCESS_NAME in env.

  2. In your code: call log_usage() after each API response (see docstring below).

  Log file: personal/scripts/anthropic_usage.log (or ANTHROPIC_USAGE_LOG path).
"""

import os
import json
from datetime import datetime
from pathlib import Path

# Default log path (same folder as this script, or set ANTHROPIC_USAGE_LOG)
LOG_PATH = os.getenv("ANTHROPIC_USAGE_LOG") or str(Path(__file__).resolve().parent / "anthropic_usage.log")
PROCESS_NAME = os.getenv("PROCESS_NAME", "anthropic_script")


def log_usage(
    process_name: str,
    input_tokens: int,
    output_tokens: int,
    model: str = "",
    request_id: str = "",
):
    """
    Append one line of usage to the log file. Call this after each Anthropic API call.

    Example with anthropic SDK:
        response = client.messages.create(...)
        log_usage(
            process_name="email_automation",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=getattr(response, "model", ""),
            request_id=getattr(response, "id", ""),
        )
    """
    entry = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "process": process_name,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model": model,
        "request_id": request_id,
    }
    line = json.dumps(entry) + "\n"
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError as e:
        print(f"[anthropic_usage_logger] Could not write log: {e}")


def run_test_call():
    """Make one minimal API call and log usage. Requires ANTHROPIC_API_KEY and anthropic package."""
    try:
        import anthropic
    except ImportError:
        print("Install anthropic: pip install anthropic")
        return
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY in your environment.")
        return
    client = anthropic.Anthropic(api_key=api_key)
    print(f"Process name: {PROCESS_NAME}")
    print(f"Log file: {LOG_PATH}")
    print("Sending one minimal message...")
    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=10,
        messages=[{"role": "user", "content": "Say OK in one word."}],
    )
    inp = response.usage.input_tokens
    out = response.usage.output_tokens
    log_usage(
        process_name=PROCESS_NAME,
        input_tokens=inp,
        output_tokens=out,
        model=getattr(response, "model", ""),
        request_id=getattr(response, "id", ""),
    )
    print(f"Logged: input_tokens={inp}, output_tokens={out}")


if __name__ == "__main__":
    run_test_call()
