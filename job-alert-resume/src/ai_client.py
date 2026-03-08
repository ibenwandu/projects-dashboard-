"""
Single entrypoint for AI-generated text. Uses Gemini by default; use OpenAI (ChatGPT) if
JAR_AI_PROVIDER=openai and OPENAI_API_KEY is set.
"""
from __future__ import annotations

import os
import re

from dotenv import load_dotenv

load_dotenv()

# Provider: gemini | openai
JAR_AI_PROVIDER = (os.getenv("JAR_AI_PROVIDER") or "gemini").strip().lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def generate(prompt: str, model: str | None = None, system_instruction: str | None = None) -> str:
    """
    Generate text. Uses OpenAI if JAR_AI_PROVIDER=openai and OPENAI_API_KEY is set; otherwise Gemini.
    Returns response text or an error string like [Gemini error: ...].
    """
    use_openai = JAR_AI_PROVIDER == "openai" and OPENAI_API_KEY
    if use_openai:
        # Ignore model param for OpenAI so we always use OPENAI_MODEL
        return _generate_openai(prompt, model=None, system_instruction=system_instruction)
    return _generate_gemini(prompt, model=model, system_instruction=system_instruction)


def _generate_openai(prompt: str, model: str | None = None, system_instruction: str | None = None) -> str:
    """Use OpenAI API (ChatGPT)."""
    from .config import OPENAI_MODEL
    model = model or OPENAI_MODEL
    if not OPENAI_API_KEY:
        return "[OpenAI error: Set OPENAI_API_KEY in environment or .env]"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(model=model, messages=messages)
        if response.choices and len(response.choices) > 0:
            return (response.choices[0].message.content or "").strip()
        return ""
    except Exception as e:
        return f"[OpenAI error: {e}]"


def _generate_gemini(prompt: str, model: str | None = None, system_instruction: str | None = None) -> str:
    """Delegate to existing Gemini client."""
    from . import gemini_client
    return gemini_client.generate(prompt, model=model, system_instruction=system_instruction)


def parse_score_and_reasoning(text: str) -> tuple[int, str]:
    """Parse 'Score: 85' and reasoning from model output (Gemini or OpenAI). Returns (score 0-100, reasoning)."""
    score = 0
    reasoning = text.strip()
    m = re.search(r"score\s*:\s*(\d+)", text, re.IGNORECASE)
    if m:
        score = min(100, max(0, int(m.group(1))))
    m = re.search(r"reasoning\s*:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
    if m:
        reasoning = m.group(1).strip()
    return score, reasoning
