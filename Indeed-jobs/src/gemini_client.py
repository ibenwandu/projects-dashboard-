"""Shared Gemini API client."""
from __future__ import annotations

import os
import re

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def _generate_new_sdk(prompt: str, model: str) -> str:
    from google import genai
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(model=model, contents=prompt)
    if response and hasattr(response, "text"):
        return response.text or ""
    return ""


def _generate_legacy_sdk(prompt: str, model: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model_name = model if model.startswith("models/") else f"models/{model}"
    gemini = genai.GenerativeModel(model_name)
    response = gemini.generate_content(prompt)
    if response and hasattr(response, "text"):
        return response.text or ""
    return ""


def generate(prompt: str, model: str | None = None, system_instruction: str | None = None) -> str:
    from .config import GEMINI_MODEL
    model = model or GEMINI_MODEL
    if not GEMINI_API_KEY:
        return "[Gemini error: Set GEMINI_API_KEY or GOOGLE_API_KEY in environment or .env]"
    try:
        try:
            return _generate_new_sdk(prompt, model)
        except (ImportError, AttributeError):
            return _generate_legacy_sdk(prompt, model)
    except Exception as e:
        return f"[Gemini error: {e}]"


def parse_score_and_reasoning(text: str) -> tuple[int, str]:
    score = 0
    reasoning = text.strip()
    m = re.search(r"score\s*:\s*(\d+)", text, re.IGNORECASE)
    if m:
        score = min(100, max(0, int(m.group(1))))
    m = re.search(r"reasoning\s*:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
    if m:
        reasoning = m.group(1).strip()
    return score, reasoning
