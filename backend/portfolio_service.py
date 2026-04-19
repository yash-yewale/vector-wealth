"""
Portfolio Service — Goal-based portfolio management.

Analyzes user holdings per goal, calculates P&L, and generates
goal-specific AI suggestions using news sentiment.
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(ENV_PATH)

logger = logging.getLogger("vector_wealth.portfolio")


# ─── Data Helpers ────────────────────────────────────────────────────────────

def _years_until(target_date_str: str) -> float:
    """Calculate years remaining until target date."""
    try:
        target = datetime.fromisoformat(target_date_str.replace("Z", "+00:00"))
        # Ensure timezone-aware
        if target.tzinfo is None:
            target = target.replace(tzinfo=UTC)
    except (ValueError, AttributeError):
        # Try parsing as just a year
        try:
            year = int(target_date_str[:4])
            target = datetime(year, 1, 1, tzinfo=UTC)
        except Exception:
            return 10.0  # default
    now = datetime.now(UTC)
    delta = target - now
    return max(0.0, delta.days / 365.25)


def _risk_label(risk: str) -> str:
    r = (risk or "moderate").lower().strip()
    if r in ("conservative", "low"):
        return "conservative"
    if r in ("aggressive", "high"):
        return "aggressive"
    return "moderate"


# ─── Portfolio Analysis ──────────────────────────────────────────────────────

def analyze_goal(goal: dict[str, Any]) -> dict[str, Any]:
    """
    Analyze a single goal: calculate P&L for each holding using live prices.

    Args:
        goal: {
            "id": str,
            "name": str,
            "targetAmount": float,
            "targetDate": str (ISO or year),
            "riskTolerance": str,
            "holdings": [{"ticker": str, "quantity": float, "buyPrice": float, "buyDate": str}, ...]
        }

    Returns:
        Goal analysis with P&L per holding and overall progress.
    """
    from price_service import fetch_stock_price

    holdings = goal.get("holdings", [])
    total_invested = 0.0
    total_current = 0.0
    analyzed_holdings = []

    from concurrent.futures import ThreadPoolExecutor

    def analyze_holding(h):
        ticker = h.get("ticker", "").upper()
        qty = float(h.get("quantity", 0))
        buy_price = float(h.get("buyPrice", 0))
        invested = qty * buy_price
        price_data = fetch_stock_price(ticker)
        current_price = price_data.get("current_price") if price_data else None
        if current_price and current_price > 0:
            current_value = qty * current_price
            pnl = current_value - invested
            pnl_percent = (pnl / invested * 100) if invested > 0 else 0.0
        else:
            current_value = invested
            current_price = buy_price
            pnl = 0.0
            pnl_percent = 0.0
        return {
            "ticker": ticker,
            "quantity": qty,
            "buyPrice": buy_price,
            "currentPrice": current_price,
            "invested": round(invested, 2),
            "currentValue": round(current_value, 2),
            "pnl": round(pnl, 2),
            "pnlPercent": round(pnl_percent, 2),
            "priceChange": price_data.get("price_change") if price_data else None,
            "priceChangePercent": price_data.get("price_change_percent") if price_data else None,
            "_invested": invested,
            "_current_value": current_value,
        }

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(analyze_holding, holdings))

    for res in results:
        total_invested += res["_invested"]
        total_current += res["_current_value"]
        # Remove helper keys before appending
        res.pop("_invested", None)
        res.pop("_current_value", None)
        analyzed_holdings.append(res)

    target_amount = float(goal.get("targetAmount", 0))
    progress = (total_current / target_amount * 100) if target_amount > 0 else 0.0
    years_left = _years_until(goal.get("targetDate", ""))
    total_pnl = total_current - total_invested

    return {
        "goalId": goal.get("id", ""),
        "goalName": goal.get("name", ""),
        "targetAmount": target_amount,
        "targetDate": goal.get("targetDate", ""),
        "riskTolerance": _risk_label(goal.get("riskTolerance", "moderate")),
        "yearsLeft": round(years_left, 1),
        "totalInvested": round(total_invested, 2),
        "totalCurrentValue": round(total_current, 2),
        "totalPnl": round(total_pnl, 2),
        "totalPnlPercent": round((total_pnl / total_invested * 100) if total_invested > 0 else 0, 2),
        "progress": round(min(progress, 100), 1),
        "holdings": analyzed_holdings,
    }


def analyze_portfolio(goals: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze all goals in a portfolio."""
    from concurrent.futures import ThreadPoolExecutor
    analyzed_goals = []
    total_invested = 0.0
    total_current = 0.0

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(analyze_goal, goals))

    for result in results:
        analyzed_goals.append(result)
        total_invested += result["totalInvested"]
        total_current += result["totalCurrentValue"]

    return {
        "goals": analyzed_goals,
        "totalInvested": round(total_invested, 2),
        "totalCurrentValue": round(total_current, 2),
        "totalPnl": round(total_current - total_invested, 2),
        "goalCount": len(analyzed_goals),
    }


# ─── Goal-Specific Suggestions ──────────────────────────────────────────────

def _extract_recommended_stocks(text: str) -> tuple[str, list[dict]]:
    """
    Extract the RECOMMENDED_STOCKS JSON block from AI response.
    Returns (clean_suggestion_text, list_of_stock_dicts).
    """
    pattern = r"RECOMMENDED_STOCKS:\s*```json\s*(\[.*?\])\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        # Try without code fences
        pattern2 = r"RECOMMENDED_STOCKS:\s*(\[.*?\])"
        match = re.search(pattern2, text, re.DOTALL)

    stocks = []
    clean_text = text
    if match:
        try:
            stocks = json.loads(match.group(1))
            # Remove the JSON block from the display text
            clean_text = text[:match.start()].strip()
        except json.JSONDecodeError:
            pass

    return clean_text, stocks


def suggest_for_goal(goal_analysis: dict[str, Any]) -> dict[str, Any]:
    """
    Generate AI suggestions for a specific goal based on:
    - Holdings sentiment (from news)
    - Risk tolerance
    - Time horizon
    - Current progress

    Returns:
        {
            "suggestion": str,           # Human-readable advice
            "recommended_stocks": [       # Actionable stock picks
                {"ticker": str, "quantity": int, "buyPrice": float, "reasoning": str},
                ...
            ]
        }
    """
    from sentiment import compute_sentiment
    from agents import news_collection

    risk = goal_analysis.get("riskTolerance", "moderate")
    years_left = goal_analysis.get("yearsLeft", 10)
    progress = goal_analysis.get("progress", 0)
    holdings = goal_analysis.get("holdings", [])
    goal_name = goal_analysis.get("goalName", "Goal")
    target = goal_analysis.get("targetAmount", 0)

    if not holdings:
        return {
            "suggestion": f"No holdings assigned to '{goal_name}' yet. Add stocks to get personalized suggestions.",
            "recommended_stocks": [],
        }

    # Gather sentiment for each holding
    holding_insights = []
    for h in holdings:
        ticker = h["ticker"]
        # Query news for this ticker
        try:
            result = news_collection.query(
                query_texts=[ticker],
                n_results=5,
                include=["documents"],
            )
            docs = result.get("documents", [[]])[0] if result.get("documents") else []
            text = " ".join(docs) if docs else ""
            sentiment = compute_sentiment(text) if text else 0.0
        except Exception:
            sentiment = 0.0

        holding_insights.append({
            "ticker": ticker,
            "sentiment": round(sentiment, 2),
            "pnl": h.get("pnl", 0),
            "pnlPercent": h.get("pnlPercent", 0),
            "weight": h.get("currentValue", 0) / goal_analysis.get("totalCurrentValue", 1) * 100,
        })

    # Build suggestion prompt
    insights_text = "\n".join([
        f"- {hi['ticker']}: sentiment={hi['sentiment']:.2f}, P&L={hi['pnlPercent']:.1f}%, "
        f"weight={hi['weight']:.0f}%"
        for hi in holding_insights
    ])

    risk_guidance = {
        "conservative": "Prioritize capital preservation. Flag any holding with negative "
                        "sentiment immediately. Suggest blue-chip alternatives.",
        "moderate": "Balance growth and safety. Flag significant negative sentiment. "
                    "Suggest diversification if overweight in a sector.",
        "aggressive": "Focus on growth. Only flag severe negative sentiment. "
                      "Higher volatility is acceptable for better returns.",
    }

    prompt = f"""Analyze this investment goal and give 2–3 brief, actionable suggestions.

GOAL: {goal_name}
Target: ₹{target:,.0f} | Progress: {progress:.1f}% | Years left: {years_left:.1f}
Risk tolerance: {risk}
Amount remaining: ₹{max(0, target - goal_analysis.get('totalCurrentValue', 0)):,.0f}

HOLDINGS:
{insights_text}

GUIDELINES:
{risk_guidance.get(risk, risk_guidance['moderate'])}

Keep suggestions short (1-2 sentences each), specific to this goal. Use ₹ symbol.

IMPORTANT: After your suggestions text, you MUST also output a block of exactly 2-4 specific
Indian stock (NSE) recommendations that complement the existing holdings. Consider the risk
tolerance, remaining amount, and diversification. Use this EXACT format:

RECOMMENDED_STOCKS:
```json
[
  {{"ticker": "SYMBOL", "quantity": 10, "buyPrice": 1234.50, "reasoning": "Brief reason"}},
  ...
]
```

Rules for recommended stocks:
- Use NSE ticker symbols (e.g. TCS, RELIANCE, INFY, HDFCBANK, WIPRO, etc.)
- Do NOT recommend stocks already held in this goal: {', '.join(h['ticker'] for h in holdings)}
- quantity should be a whole number, affordable given the remaining target amount
- buyPrice should be approximate current market price in ₹
- reasoning should be 1 short sentence"""

    try:
        from google import genai
        api_key = os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        raw_text = response.text.strip()
        suggestion_text, recommended_stocks = _extract_recommended_stocks(raw_text)
        return {
            "suggestion": suggestion_text,
            "recommended_stocks": recommended_stocks,
        }
    except Exception as e:
        logger.error("Suggestion generation failed: %s", e)
        # Fallback: rule-based suggestions
        suggestions = []
        for hi in holding_insights:
            if hi["sentiment"] < -0.2 and risk == "conservative":
                suggestions.append(
                    f"⚠️ {hi['ticker']} shows negative sentiment ({hi['sentiment']:.2f}). "
                    f"Consider reviewing for your {risk} goal."
                )
            elif hi["weight"] > 40:
                suggestions.append(
                    f"📊 {hi['ticker']} is {hi['weight']:.0f}% of this goal — "
                    f"consider diversifying to reduce concentration risk."
                )
        if not suggestions:
            suggestions.append("✅ Your holdings look balanced for this goal. Keep monitoring.")
        return {
            "suggestion": "\n".join(suggestions),
            "recommended_stocks": [],
        }
