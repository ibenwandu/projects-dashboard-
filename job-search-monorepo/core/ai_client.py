"""Unified AI client for Gemini and OpenAI."""
import os
from typing import Optional

from .config import AI_PROVIDER, GEMINI_MODEL, OPENAI_MODEL


def generate(prompt: str, model: Optional[str] = None) -> str:
    """
    Generate text using configured AI provider (Gemini or OpenAI).

    Falls back gracefully if provider not configured.
    """
    provider = AI_PROVIDER.lower()

    if provider == "openai":
        return _generate_openai(prompt, model or OPENAI_MODEL)
    else:
        # Default to Gemini
        return _generate_gemini(prompt, model or GEMINI_MODEL)


def _generate_gemini(prompt: str, model: str) -> str:
    """Generate using Google Gemini API."""
    try:
        from google import genai
    except ImportError:
        raise ImportError("google-genai not installed. Run: pip install google-genai")

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not set in .env")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt
    )
    return response.text


def _generate_openai(prompt: str, model: str) -> str:
    """Generate using OpenAI API."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai not installed. Run: pip install openai")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set in .env")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def parse_score_and_reasoning(text: str) -> tuple[int, str]:
    """
    Parse AI response for score and reasoning.

    Expects format:
    Score: 85
    Reasoning: Job is good fit because...
    """
    lines = text.strip().split("\n")
    score = 0
    reasoning = ""

    for line in lines:
        if line.startswith("Score:"):
            try:
                score = int(line.replace("Score:", "").strip())
            except ValueError:
                score = 0
        elif line.startswith("Reasoning:"):
            reasoning = line.replace("Reasoning:", "").strip()

    return score, reasoning
