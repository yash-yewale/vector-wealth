"""
AI summary generation using Google Gemini.

Extracted from agents.py for modularity.
"""
from __future__ import annotations

import os

from google import genai


GENERATION_MODEL = "gemini-2.5-flash"
AI_SUMMARY_MAX_HEADLINES = 10


def generate_ai_summary(ticker: str, headlines: list[str], sentiment: float) -> str | None:
    """
    Generate a concise AI summary of news headlines using Gemini.
    Returns a 2-3 sentence summary or None on failure.
    """
    if not headlines:
        return None

    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        client = genai.Client(api_key=api_key)

        limited_headlines = headlines[:AI_SUMMARY_MAX_HEADLINES]
        headlines_text = "\n".join(f"- {h}" for h in limited_headlines)

        sentiment_desc = "positive" if sentiment > 0.1 else "negative" if sentiment < -0.1 else "neutral"

        prompt = f"""Analyze these news headlines for {ticker} stock and provide a concise 2-3 sentence summary for an investor. Focus on:
1. Key developments or events
2. Market sentiment drivers
3. Potential impact on stock

Headlines:
{headlines_text}

Overall sentiment: {sentiment_desc} ({sentiment:.2f})

Provide a brief, actionable summary (max 3 sentences):"""

        response = client.models.generate_content(
            model=GENERATION_MODEL,
            contents=prompt,
        )

        summary = response.text.strip() if response.text else None
        return summary

    except Exception:
        return None
