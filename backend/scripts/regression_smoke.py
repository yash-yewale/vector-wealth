from __future__ import annotations

import json
import sys
from typing import Any

import requests


BASE_URL = "http://127.0.0.1:8000"
ANALYZE_ENDPOINT = f"{BASE_URL}/analyze"

KNOWN_TICKERS = [
    "HDFCBANK",
    "ICICIBANK",
    "RELIANCE",
    "TATA MOTORS",
    "IRFC",
    "SBIN",
    "INFY",
    "TCS",
    "LT",
    "ITC",
]

RANDOM_INPUTS = ["SJFJ", "ZZZZQ", "ABCXYZ", "QWERTY", "NONSENSE"]


def analyze(ticker: str) -> dict[str, Any]:
    response = requests.post(ANALYZE_ENDPOINT, json={"ticker": ticker}, timeout=60)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected response type for {ticker}: {type(payload)}")
    return payload


def validate_payload(ticker: str, payload: dict[str, Any]) -> None:
    required_keys = {
        "ticker",
        "sentiment",
        "now_sentiment",
        "pattern_sentiment",
        "confidence",
        "recent_news_count",
        "pattern_news_count",
        "latest_news_date",
        "stale_data",
        "stale_reason",
        "explanation",
        "positive_drivers",
        "negative_drivers",
        "news_references",
        "recommendation",
    }
    missing = required_keys - set(payload.keys())
    if missing:
        raise RuntimeError(f"{ticker}: missing keys {sorted(missing)}")

    if payload["recommendation"] not in {"BUY", "HOLD", "SELL"}:
        raise RuntimeError(f"{ticker}: invalid recommendation {payload['recommendation']}")


def run() -> int:
    print("Running backend regression smoke checks...")

    for ticker in KNOWN_TICKERS:
        payload = analyze(ticker)
        validate_payload(ticker, payload)
        print(
            f"[KNOWN] {ticker:12} rec={payload['recommendation']:4} "
            f"sent={payload['sentiment']:.2f} "
            f"recent={payload['recent_news_count']} pattern={payload['pattern_news_count']}"
        )

    random_failures = []
    for ticker in RANDOM_INPUTS:
        payload = analyze(ticker)
        validate_payload(ticker, payload)
        refs = payload.get("news_references", [])
        if refs:
            random_failures.append({"ticker": ticker, "headline_count": len(refs)})
        print(
            f"[RANDOM] {ticker:12} rec={payload['recommendation']:4} "
            f"headlines={len(refs)}"
        )

    if random_failures:
        print("\nRandom-input guardrail failures:")
        print(json.dumps(random_failures, indent=2))
        return 1

    print("\nRegression smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
