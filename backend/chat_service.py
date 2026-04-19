"""
Chat Service — Stock Research Assistant powered by Groq.

Groq handles conversation / intent detection / response formatting.
Existing backend pipeline (Gemini + ChromaDB) handles actual data retrieval.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(ENV_PATH, override=True)

logger = logging.getLogger("vector_wealth.chat")

# ─── LLM Configuration ──────────────────────────────────────────────────────

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash").strip()

MAX_CONVERSATION_HISTORY = 20  # Keep last N messages per session


# ─── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class ChatMessage:
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = ""
    data: dict[str, Any] | None = None  # Attached analysis data, if any

    def to_dict(self) -> dict[str, Any]:
        d = {"role": self.role, "content": self.content, "timestamp": self.timestamp}
        if self.data:
            d["data"] = self.data
        return d


@dataclass
class ChatSession:
    session_id: str
    messages: list[ChatMessage] = field(default_factory=list)
    created_at: str = ""

    def add_message(self, msg: ChatMessage) -> None:
        self.messages.append(msg)
        # Trim to max history
        if len(self.messages) > MAX_CONVERSATION_HISTORY:
            self.messages = self.messages[-MAX_CONVERSATION_HISTORY:]


# ─── Intent Detection ───────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Vector Wealth's Stock Research Assistant — a helpful, concise expert on the Indian stock market.

CAPABILITIES:
- Analyze individual stocks (sentiment, price, news)
- Compare stocks or sectors
- Explain market concepts
- Discuss watchlist stocks
- Surface opportunities from recent scans

RULES:
1. When the user asks about a specific stock, respond with "[ANALYZE:TICKER]" FIRST, then I'll inject real data for you to discuss.
2. When comparing stocks, respond with "[COMPARE:TICKER1,TICKER2]".
3. When asked about watchlist, respond with "[WATCHLIST]".
4. When asked about their portfolio or financial goals, respond with "[PORTFOLIO]".
5. When asked about opportunities/discoveries, respond with "[OPPORTUNITIES]".
6. For general market questions or concepts, answer directly from your knowledge.
6. Keep responses concise — 2-4 short paragraphs max.
7. Use ₹ for Indian rupee prices.
8. Be conversational but professional.
9. If you don't know something specific, say so honestly.
10. IMPORTANT: Only output the intent tag when you need real-time data. For general questions, just answer directly."""


def _detect_intent(response_text: str) -> tuple[str, str | None]:
    """
    Parse LLM response for intent tags.
    Returns: (intent, payload)
    """
    analyze_match = re.search(r"\[ANALYZE:([A-Z0-9._&-]+)\]", response_text)
    if analyze_match:
        return "analyze", analyze_match.group(1)

    compare_match = re.search(r"\[COMPARE:([A-Z0-9._&,-]+)\]", response_text)
    if compare_match:
        return "compare", compare_match.group(1)

    if "[WATCHLIST]" in response_text:
        return "watchlist", None

    if "[PORTFOLIO]" in response_text:
        return "portfolio", None

    if "[OPPORTUNITIES]" in response_text:
        return "opportunities", None

    return "direct", None


# ─── LLM Client (Groq → Gemini fallback) ────────────────────────────────────

def _call_groq(messages: list[dict[str, str]], temperature: float = 0.7) -> str:
    """Call Groq API using OpenAI-compatible endpoint."""
    print(f"[DEBUG] Calling Groq API with model: {GROQ_MODEL}")
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 1024,
    }
    resp = requests.post(
        f"{GROQ_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"[DEBUG] Groq API Error: {resp.status_code} - {resp.text}")
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _call_gemini(messages: list[dict[str, str]], temperature: float = 0.7) -> str:
    """Call Gemini API for chat (lightweight model)."""
    from google import genai

    client = genai.Client(api_key=GOOGLE_API_KEY)

    # Convert OpenAI-style messages to Gemini format
    # System prompt goes into system_instruction, rest as contents
    system_text = ""
    contents = []
    for msg in messages:
        if msg["role"] == "system":
            system_text = msg["content"]
        elif msg["role"] == "user":
            contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
        elif msg["role"] == "assistant":
            contents.append({"role": "model", "parts": [{"text": msg["content"]}]})

    config = {"temperature": temperature, "max_output_tokens": 1024}
    if system_text:
        config["system_instruction"] = system_text

    response = client.models.generate_content(
        model=GEMINI_CHAT_MODEL,
        contents=contents,
        config=config,
    )
    return response.text


def _call_llm(messages: list[dict[str, str]], temperature: float = 0.7) -> str:
    """
    Call the best available LLM:
    """
    # Try Groq first
    print(f"[DEBUG] Attempting LLM call. Groq Key Length: {len(GROQ_API_KEY)}")
    if GROQ_API_KEY and "PASTE_YOUR_GRO" not in GROQ_API_KEY:
        try:
            return _call_groq(messages, temperature)
        except Exception as e:
            print(f"[DEBUG] Groq failed: {e}")
            logger.warning("Groq failed, falling back to Gemini: %s", e)

    # Fall back to Gemini
    print("[DEBUG] Falling back to Gemini...")
    if GOOGLE_API_KEY:
        try:
            return _call_gemini(messages, temperature)
        except Exception as e:
            print(f"[DEBUG] Gemini also failed: {e}")
            logger.error("Gemini also failed: %s", e)
            raise RuntimeError(f"Chat service unavailable: {e}") from e

    raise RuntimeError(
        "No chat LLM configured. Set GROQ_API_KEY (Groq) or GOOGLE_API_KEY (Gemini) in .env"
    )


# ─── Data Fetchers (use existing pipeline) ───────────────────────────────────

def _fetch_analysis(ticker: str) -> dict[str, Any]:
    """Run the existing analysis pipeline for a ticker."""
    from agents import run_analysis

    query = f"What is the sentiment on {ticker}?"
    result = run_analysis(query)

    return {
        "ticker": ticker,
        "sentiment": result.get("sentiment", 0.0),
        "now_sentiment": result.get("now_sentiment", 0.0),
        "confidence": result.get("confidence", 0.0),
        "recommendation": result.get("final_decision", "HOLD"),
        "current_price": result.get("current_price"),
        "price_change": result.get("price_change"),
        "price_change_percent": result.get("price_change_percent"),
        "recent_news_count": result.get("recent_news_count", 0),
        "positive_drivers": result.get("positive_drivers", [])[:3],
        "negative_drivers": result.get("negative_drivers", [])[:3],
        "ai_summary": result.get("ai_summary"),
        "explanation": result.get("explanation", ""),
    }


def _fetch_opportunities() -> list[dict[str, Any]]:
    """Fetch current opportunities from scanner."""
    from opportunity_scanner import opportunity_scanner

    return opportunity_scanner.get_opportunities()


def _format_data_context(intent: str, data: Any) -> str:
    """Format fetched data as context for Groq to discuss."""
    if intent == "analyze" and isinstance(data, dict):
        price_str = f"₹{data['current_price']:.2f}" if data.get("current_price") else "N/A"
        change_str = ""
        if data.get("price_change") is not None:
            sign = "+" if data["price_change"] >= 0 else ""
            change_str = f" ({sign}{data['price_change']:.2f}, {sign}{data.get('price_change_percent', 0):.2f}%)"

        pos = ", ".join(data.get("positive_drivers", [])[:3]) or "None"
        neg = ", ".join(data.get("negative_drivers", [])[:3]) or "None"

        return f"""[LIVE DATA for {data['ticker']}]
Price: {price_str}{change_str}
Sentiment: {data['sentiment']:.2f} (Confidence: {data['confidence']:.0%})
Recommendation: {data['recommendation']}
Recent articles: {data['recent_news_count']}
Positive drivers: {pos}
Negative drivers: {neg}
{f"AI Summary: {data['ai_summary']}" if data.get('ai_summary') else ""}"""

    if intent == "compare" and isinstance(data, list):
        parts = []
        for d in data:
            price_str = f"₹{d['current_price']:.2f}" if d.get("current_price") else "N/A"
            parts.append(
                f"- {d['ticker']}: Price {price_str}, Sentiment {d['sentiment']:.2f}, "
                f"Rec: {d['recommendation']}"
            )
        return "[COMPARISON DATA]\n" + "\n".join(parts)

    if intent == "opportunities" and isinstance(data, list):
        if not data:
            return "[OPPORTUNITIES] No opportunities found in the latest scan."
        parts = []
        for opp in data[:5]:
            parts.append(
                f"- {opp['ticker']}: Sentiment {opp.get('sentiment', 0):.2f}, "
                f"{opp.get('reasoning', '')}"
            )
        return "[OPPORTUNITIES DATA]\n" + "\n".join(parts)

    return ""


# ─── Session Store ───────────────────────────────────────────────────────────
# Simple in-memory sessions (sufficient for single-server deployment)

_sessions: dict[str, ChatSession] = {}


def get_or_create_session(session_id: str) -> ChatSession:
    if session_id not in _sessions:
        _sessions[session_id] = ChatSession(
            session_id=session_id,
            created_at=datetime.now(UTC).isoformat(),
        )
    return _sessions[session_id]


# ─── Main Chat Function ─────────────────────────────────────────────────────

def chat(
    session_id: str,
    user_message: str,
    context_data: dict[str, Any] | None = None,
) -> ChatMessage:
    """
    Process a user chat message and return an assistant response.

    Flow:
    1. Send user message + history to Grok for intent detection
    2. If intent requires data, fetch from existing pipeline
    3. Send data context back to Grok for formatting
    4. Return conversational response
    """
    session = get_or_create_session(session_id)
    now = datetime.now(UTC).isoformat()

    # Add user message
    user_msg = ChatMessage(role="user", content=user_message, timestamp=now)
    session.add_message(user_msg)

    # Build messages for Groq
    system_content = SYSTEM_PROMPT

    # Inject portfolio context into system prompt so the LLM always knows
    # what the user holds (avoids needing [PORTFOLIO] tag for basic questions)
    if context_data and context_data.get("portfolio"):
        portfolio_goals = context_data["portfolio"]
        portfolio_summary_parts = ["\n\nUSER'S PORTFOLIO (always available to you):"]
        for g in portfolio_goals:
            goal_name = g.get("name", "Unnamed")
            target = g.get("targetAmount", 0)
            risk = g.get("riskTolerance", "moderate")
            target_date = g.get("targetDate", "")
            holdings = g.get("holdings", [])
            portfolio_summary_parts.append(
                f"- Goal '{goal_name}': Target ₹{target:,.0f}, "
                f"Risk: {risk}, Target date: {target_date}"
            )
            if holdings:
                h_strs = [
                    f"  {h.get('ticker', '?')} (qty: {h.get('quantity', 0)}, "
                    f"buy ₹{h.get('buyPrice', 0):.0f})"
                    for h in holdings
                ]
                portfolio_summary_parts.extend(h_strs)
        system_content += "\n".join(portfolio_summary_parts)

    groq_messages = [{"role": "system", "content": system_content}]
    for msg in session.messages:
        groq_messages.append({"role": msg.role, "content": msg.content})

    # Step 1: Get intent from Groq
    intent_response = _call_llm(groq_messages, temperature=0.3)
    intent, payload = _detect_intent(intent_response)

    response_data = None

    if intent == "analyze" and payload:
        # Fetch real data
        try:
            analysis_data = _fetch_analysis(payload)
            response_data = analysis_data
            data_context = _format_data_context("analyze", analysis_data)

            # Step 2: Send data back to Groq for conversational formatting
            groq_messages.append({"role": "assistant", "content": intent_response})
            groq_messages.append({
                "role": "user",
                "content": f"Here is the live data. Now give me a helpful, conversational summary "
                           f"based on this data. Do NOT include raw numbers dump — weave them naturally "
                           f"into your response:\n\n{data_context}",
            })
            final_response = _call_llm(groq_messages, temperature=0.7)
        except Exception as e:
            final_response = f"I tried to fetch data for {payload} but ran into an issue: {e}. Would you like me to try again?"

    elif intent == "compare" and payload:
        tickers = [t.strip() for t in payload.split(",")]
        try:
            results = []
            for ticker in tickers[:3]:  # Max 3 comparisons
                results.append(_fetch_analysis(ticker))
            response_data = results
            data_context = _format_data_context("compare", results)

            groq_messages.append({"role": "assistant", "content": intent_response})
            groq_messages.append({
                "role": "user",
                "content": f"Here is the comparison data. Provide a helpful comparison:\n\n{data_context}",
            })
            final_response = _call_llm(groq_messages, temperature=0.7)
        except Exception as e:
            final_response = f"I couldn't fetch comparison data: {e}. Want me to try again?"

    elif intent == "opportunities":
        try:
            opps = _fetch_opportunities()
            response_data = opps
            data_context = _format_data_context("opportunities", opps)

            groq_messages.append({"role": "assistant", "content": intent_response})
            groq_messages.append({
                "role": "user",
                "content": f"Here are the latest opportunities. Summarize them conversationally:\n\n{data_context}",
            })
            final_response = _call_llm(groq_messages, temperature=0.7)
        except Exception as e:
            final_response = f"Couldn't fetch opportunities: {e}"

    elif intent == "watchlist":
        final_response = (
            "I can see your watchlist! To analyze a specific stock from it, "
            "just tell me the ticker — for example, 'How is TCS doing?'"
        )

    elif intent == "portfolio":
        if not context_data or not context_data.get("portfolio"):
            final_response = (
                "I don't have access to your portfolio data right now. "
                "Please add some goals and holdings in the Portfolio tab first!"
            )
        else:
            try:
                # context_data["portfolio"] is the list of goals sent from Flutter
                from portfolio_service import analyze_portfolio
                portfolio_analysis = analyze_portfolio(context_data["portfolio"])
                
                # Format for Grok/Gemini
                p_text = f"Total Invested: ₹{portfolio_analysis['totalInvested']}\n"
                p_text += f"Total Value: ₹{portfolio_analysis['totalCurrentValue']}\n"
                p_text += f"Total P&L: ₹{portfolio_analysis['totalPnl']}\n\nGoals:\n"
                
                for g in portfolio_analysis["goals"]:
                    p_text += f"- {g['goalName']}: Target ₹{g['targetAmount']}, Progress {g['progress']}%, Risk: {g['riskTolerance']}\n"
                    if g["holdings"]:
                        p_text += f"  Holdings: {', '.join(h['ticker'] for h in g['holdings'])}\n"

                groq_messages.append({"role": "assistant", "content": intent_response})
                groq_messages.append({
                    "role": "user",
                    "content": f"Here is the user's live portfolio data. Give a conversational, helpful overview, "
                               f"highlighting their progress and any risks based on their goals:\n\n{p_text}",
                })
                final_response = _call_llm(groq_messages, temperature=0.7)
            except Exception as e:
                logger.error("Portfolio chat failed: %s", e)
                final_response = "I hit an error trying to analyze your portfolio."

    else:
        # Direct response (general questions, concepts, etc.)
        final_response = intent_response

    # Clean any leftover intent tags from the response
    final_response = re.sub(r"\[(?:ANALYZE|COMPARE|WATCHLIST|OPPORTUNITIES|PORTFOLIO)[^\]]*\]\s*", "", final_response).strip()

    # Store assistant response
    assistant_msg = ChatMessage(
        role="assistant",
        content=final_response,
        timestamp=datetime.now(UTC).isoformat(),
        data=response_data,
    )
    session.add_message(assistant_msg)

    return assistant_msg
