"""
Stock price fetching via Yahoo Finance and peer comparison.

Extracted from agents.py for modularity.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import yfinance as yf

from stock_data import PEER_GROUPS


# ─── Constants ───────────────────────────────────────────────────────────────

NSE_TICKER_SUFFIX = ".NS"
BSE_TICKER_SUFFIX = ".BO"
PRICE_CACHE_TTL_SECONDS = 300  # 5 minutes
FAIL_CACHE_TTL_SECONDS = 15    # 15 seconds for transient yfinance failures

_price_cache: dict[str, tuple[float, dict[str, float | None]]] = {}


# ─── Price Fetching ──────────────────────────────────────────────────────────

def fetch_stock_price(ticker: str) -> dict[str, float | None]:
    """
    Fetch current stock price and change from Yahoo Finance.
    Uses 5-minute cache. Tries NSE (.NS) first, then BSE (.BO).
    """
    if not ticker or ticker.upper() == "MARKET":
        return {"current_price": None, "price_change": None, "price_change_percent": None}

    ticker_upper = ticker.upper().strip()

    # Check cache first
    if ticker_upper in _price_cache:
        cached_time, cached_data = _price_cache[ticker_upper]
        is_failure = cached_data.get("current_price") is None
        ttl = FAIL_CACHE_TTL_SECONDS if is_failure else PRICE_CACHE_TTL_SECONDS
        if time.time() - cached_time < ttl:
            return cached_data

    suffixes_to_try = [NSE_TICKER_SUFFIX, BSE_TICKER_SUFFIX]

    for suffix in suffixes_to_try:
        yf_ticker = f"{ticker_upper}{suffix}"
        try:
            stock = yf.Ticker(yf_ticker)
            info = stock.info

            current_price = info.get("currentPrice") or info.get("regularMarketPrice")
            if current_price is None:
                continue

            prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")

            price_change = None
            price_change_percent = None
            if prev_close and prev_close > 0:
                price_change = round(current_price - prev_close, 2)
                price_change_percent = round((price_change / prev_close) * 100, 2)

            result = {
                "current_price": round(current_price, 2),
                "price_change": price_change,
                "price_change_percent": price_change_percent,
            }

            _price_cache[ticker_upper] = (time.time(), result)
            return result

        except Exception:
            continue

    empty_result = {"current_price": None, "price_change": None, "price_change_percent": None}
    _price_cache[ticker_upper] = (time.time(), empty_result)
    return empty_result


# ─── Peer Comparison ─────────────────────────────────────────────────────────

def get_peer_stocks(ticker: str) -> list[str]:
    """Get peer stocks for a given ticker."""
    return PEER_GROUPS.get(ticker.upper().strip(), [])


def fetch_peer_comparison(ticker: str, limit: int = 2) -> list[dict[str, Any]]:
    """
    Get peer stocks with price data for comparison.
    Limited to 2 peers by default to keep response times reasonable.
    """
    peers = get_peer_stocks(ticker)
    if not peers:
        return []

    results: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=limit) as executor:
        future_to_ticker = {
            executor.submit(fetch_stock_price, peer_ticker): peer_ticker
            for peer_ticker in peers[:limit]
        }

        for future in as_completed(future_to_ticker, timeout=10):
            peer_ticker = future_to_ticker[future]
            try:
                price_data = future.result(timeout=5)
                results.append({
                    "ticker": peer_ticker,
                    "current_price": price_data.get("current_price"),
                    "price_change": price_data.get("price_change"),
                    "price_change_percent": price_data.get("price_change_percent"),
                })
            except Exception:
                results.append({
                    "ticker": peer_ticker,
                    "current_price": None,
                    "price_change": None,
                    "price_change_percent": None,
                })

    return results
