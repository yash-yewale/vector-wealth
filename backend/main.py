from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import traceback
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agents import run_analysis
from chat_service import chat as chat_handler, get_or_create_session
from live_news_ingest import LiveNewsIngestor
from opportunity_scanner import opportunity_scanner, should_run_scanner, is_market_hours
from portfolio_service import analyze_portfolio, analyze_goal, suggest_for_goal
from storage_service import (
    save_portfolio,
    load_portfolio,
    save_chat_history,
    load_chat_history,
)

logger = logging.getLogger("vector_wealth")

app = FastAPI(title="Vector Wealth API", version="1.2.0")
live_news_ingestor = LiveNewsIngestor()

_raw_origins = os.getenv("ALLOWED_ORIGINS", "").strip()

if _raw_origins == "*":
    # Cloud deployment: allow all origins (mobile app, any domain)
    allowed_origins = ["*"]
    _origin_regex = None
else:
    allowed_origins = [
        origin.strip()
        for origin in _raw_origins.split(",")
        if origin.strip()
    ]
    _origin_regex = r"https?://(localhost|127\.0\.0\.1)(:\d+)?$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Security: Admin API Key ────────────────────────────────────────────────

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "").strip()


def verify_admin_key(request: Request):
    """Dependency that verifies the X-Admin-Key header for admin endpoints."""
    if not ADMIN_API_KEY:
        return  # No key configured = skip auth (dev mode)
    provided_key = request.headers.get("X-Admin-Key", "")
    if provided_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing admin API key")


# ─── Security: Rate Limiting ────────────────────────────────────────────────
# Simple in-memory rate limiter (no external dependency needed)

_rate_limit_store: dict[str, list[float]] = {}
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX", "10"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW", "60"))


def _check_rate_limit(client_ip: str) -> None:
    """Raise 429 if client exceeds rate limit."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS

    if client_ip not in _rate_limit_store:
        _rate_limit_store[client_ip] = []

    # Prune old entries
    _rate_limit_store[client_ip] = [
        ts for ts in _rate_limit_store[client_ip] if ts > window_start
    ]

    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {RATE_LIMIT_MAX_REQUESTS} requests per {RATE_LIMIT_WINDOW_SECONDS}s.",
        )

    _rate_limit_store[client_ip].append(now)


# ─── Security: Global Exception Handler ─────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return structured JSON instead of raw 500."""
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again later.",
            "detail": str(exc) if os.getenv("DEBUG", "").lower() in ("1", "true") else None,
        },
    )


class AnalyzeRequest(BaseModel):
    ticker: str


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    context_data: dict[str, Any] | None = None


class HoldingInput(BaseModel):
    ticker: str
    quantity: float
    buyPrice: float
    buyDate: str = ""


class GoalInput(BaseModel):
    id: str = ""
    name: str
    targetAmount: float
    targetDate: str
    riskTolerance: str = "moderate"
    holdings: list[HoldingInput] = []


class PortfolioRequest(BaseModel):
    goals: list[GoalInput]


class GoalSuggestRequest(BaseModel):
    goal: GoalInput


async def _live_news_scheduler_loop() -> None:
    while True:
        summary = await asyncio.to_thread(live_news_ingestor.ingest_once)

        should_scan, scan_reason = should_run_scanner()
        if should_scan and not summary.failed:
            try:
                scan_result = await asyncio.to_thread(
                    opportunity_scanner.scan,
                    scan_reason
                )
                telemetry = {
                    "event": "opportunity_scan",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "scan_type": scan_reason,
                    "candidates_found": scan_result.candidates_found,
                    "opportunities_found": len(scan_result.opportunities),
                    "success": scan_result.success,
                }
                print(json.dumps(telemetry, ensure_ascii=False))
            except Exception as e:
                print(json.dumps({"event": "opportunity_scan_error", "error": str(e)}))

        sleep_seconds = live_news_ingestor.interval_minutes * 60
        if summary.failed:
            sleep_seconds = min(300, sleep_seconds)
        await asyncio.sleep(max(10, sleep_seconds))


@app.on_event("startup")
async def _startup_live_news_scheduler() -> None:
    if live_news_ingestor.enabled:
        app.state.live_news_task = asyncio.create_task(_live_news_scheduler_loop())


@app.on_event("shutdown")
async def _shutdown_live_news_scheduler() -> None:
    task = getattr(app.state, "live_news_task", None)
    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@app.get("/")
async def root():
    """Health check / API info"""
    return {
        "name": "Vector Wealth API",
        "version": "1.3.0",
        "status": "running",
        "endpoints": {
            "POST /analyze": "Analyze a stock ticker",
            "POST /chat": "Stock research chat assistant (Groq)",
            "GET /opportunities": "Get AI-identified opportunities",
            "POST /opportunities/scan": "Trigger opportunity scan",
            "GET /opportunities/status": "Scanner status",
            "GET /admin/live-news/status": "News ingestion status (requires X-Admin-Key)",
        }
    }


@app.post("/analyze")
def analyze_ticker(payload: AnalyzeRequest, request: Request):
    # Rate limit check
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    started_at = time.perf_counter()
    ticker = payload.ticker.strip().upper()
    query = f"What is the sentiment on {ticker}?"

    try:
        result = run_analysis(query)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    retrieved_docs = result.get("retrieved_docs", [])

    references = [
        {
            "date": doc.get("metadata", {}).get("Date", ""),
            "title": doc.get("metadata", {}).get("Title", ""),
        }
        for doc in retrieved_docs
    ]

    response_body = {
        "ticker": ticker,
        "query": query,
        "sentiment": result.get("sentiment", 0.0),
        "now_sentiment": result.get("now_sentiment", result.get("sentiment", 0.0)),
        "pattern_sentiment": result.get("pattern_sentiment", result.get("sentiment", 0.0)),
        "confidence": result.get("confidence", 0.0),
        "recent_news_count": result.get("recent_news_count", len(references)),
        "pattern_news_count": result.get("pattern_news_count", len(references)),
        "latest_news_date": result.get("latest_news_date", ""),
        "stale_data": result.get("stale_data", False),
        "stale_reason": result.get("stale_reason", ""),
        "explanation": result.get("explanation", ""),
        "positive_drivers": result.get("positive_drivers", []),
        "negative_drivers": result.get("negative_drivers", []),
        "news_references": references,
        "recommendation": result.get("final_decision", "HOLD"),
        "current_price": result.get("current_price"),
        "price_change": result.get("price_change"),
        "price_change_percent": result.get("price_change_percent"),
        "ai_summary": result.get("ai_summary"),
        "peers": result.get("peers"),
    }

    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
    telemetry = {
        "event": "analyze_request",
        "timestamp": datetime.now(UTC).isoformat(),
        "ticker": ticker,
        "recommendation": response_body["recommendation"],
        "sentiment": response_body["sentiment"],
        "recent_news_count": response_body["recent_news_count"],
        "pattern_news_count": response_body["pattern_news_count"],
        "stale_data": response_body["stale_data"],
        "latency_ms": latency_ms,
    }
    print(json.dumps(telemetry, ensure_ascii=False))

    return response_body


# ─── Admin Endpoints (require X-Admin-Key) ──────────────────────────────────

@app.get("/admin/live-news/status", dependencies=[Depends(verify_admin_key)])
def live_news_status():
    return live_news_ingestor.get_status()


@app.post("/admin/live-news/refresh", dependencies=[Depends(verify_admin_key)])
async def refresh_live_news():
    summary = await asyncio.to_thread(live_news_ingestor.ingest_once)
    if summary.failed:
        raise HTTPException(status_code=503, detail=summary.message)
    return summary.to_dict()


@app.post("/admin/live-news/retag-existing", dependencies=[Depends(verify_admin_key)])
async def retag_existing_live_news():
    result = await asyncio.to_thread(live_news_ingestor.retag_existing_records)
    if result.get("failed"):
        raise HTTPException(status_code=503, detail=result.get("message", "Retagging failed"))
    return result


# ============== Opportunity Scanner Endpoints ==============

@app.get("/opportunities")
async def get_opportunities():
    """Get current stock opportunities (for Discover tab)"""
    return {
        "opportunities": opportunity_scanner.get_opportunities(),
        "is_market_hours": is_market_hours(),
    }


@app.get("/opportunities/status")
async def get_scanner_status():
    """Get opportunity scanner status"""
    return opportunity_scanner.get_status()


@app.post("/opportunities/scan")
async def trigger_scan():
    """Manually trigger an opportunity scan"""
    should_scan, scan_reason = should_run_scanner()
    if not should_scan:
        scan_reason = "manual"

    scan_result = await asyncio.to_thread(opportunity_scanner.scan, scan_reason)

    if not scan_result.success:
        raise HTTPException(status_code=503, detail=scan_result.message)

    return scan_result.to_dict()


# ============== Chat Endpoints ==============

@app.post("/chat")
async def chat_endpoint(payload: ChatRequest, request: Request):
    """Stock Research Assistant — powered by Groq/Gemini"""
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    try:
        result = await asyncio.to_thread(
            chat_handler, payload.session_id, payload.message, payload.context_data
        )
        return result.to_dict()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/chat/history/{session_id}")
def chat_history(session_id: str):
    """Get chat history for a session"""
    session = get_or_create_session(session_id)
    return {
        "session_id": session.session_id,
        "messages": [m.to_dict() for m in session.messages],
    }


# ============== Portfolio Endpoints ==============

@app.post("/portfolio/analyze")
async def portfolio_analyze(payload: PortfolioRequest, request: Request):
    """Analyze all goals — returns P&L per holding and progress"""
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    goals_dicts = [g.model_dump() for g in payload.goals]
    try:
        result = await asyncio.to_thread(analyze_portfolio, goals_dicts)
        return result
    except Exception as exc:
        import traceback
        print("[ERROR] Exception in /portfolio/analyze:")
        traceback.print_exc()
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/portfolio/suggest")
async def portfolio_suggest(payload: GoalSuggestRequest, request: Request):
    """Get AI suggestions for a specific goal"""
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    goal_dict = payload.goal.model_dump()
    try:
        analysis = await asyncio.to_thread(analyze_goal, goal_dict)
        result = await asyncio.to_thread(suggest_for_goal, analysis)
        return {
            "goalId": goal_dict.get("id", ""),
            "suggestion": result.get("suggestion", ""),
            "recommended_stocks": result.get("recommended_stocks", []),
        }
    except Exception as exc:
        import traceback
        print("[ERROR] Exception in /portfolio/suggest:")
        traceback.print_exc()
        raise HTTPException(status_code=503, detail=str(exc)) from exc


# ============== Storage Endpoints (persistent goals & chat) ==================

class SavePortfolioRequest(BaseModel):
    user_id: str = "default"
    goals: list[GoalInput]


class SaveChatRequest(BaseModel):
    session_id: str
    messages: list[dict[str, Any]]


@app.post("/storage/portfolio/save")
def storage_save_portfolio(payload: SavePortfolioRequest):
    """Save portfolio goals to backend file storage."""
    goals_dicts = [g.model_dump() for g in payload.goals]
    return save_portfolio(payload.user_id, goals_dicts)


@app.get("/storage/portfolio/load")
def storage_load_portfolio(user_id: str = "default"):
    """Load portfolio goals from backend file storage."""
    return load_portfolio(user_id)


@app.post("/storage/chat/save")
def storage_save_chat(payload: SaveChatRequest):
    """Save chat history to backend file storage."""
    return save_chat_history(payload.session_id, payload.messages)


@app.get("/storage/chat/load")
def storage_load_chat(session_id: str):
    """Load chat history from backend file storage."""
    return load_chat_history(session_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
