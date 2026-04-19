"""
Opportunity Scanner - Hybrid Script + Agent for proactive stock discovery.

Runs after each news ingestion cycle during market hours.
Step 1: Script filters stocks with positive sentiment (> threshold)
Step 2: Agent (LLM) picks top opportunities with reasoning
"""

from __future__ import annotations

import json
import os
import re
import threading
from dataclasses import dataclass, asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import chromadb
from dotenv import load_dotenv
from google import genai

# Import from restructured modules
from agents import (
    news_collection,
    GENERATION_MODEL,
    API_MAX_RETRIES,
    DEFAULT_RETRY_DELAY_SECONDS,
)
from sentiment import compute_sentiment as _compute_sentiment
from stock_data import STOCK_ALIASES
from price_service import fetch_stock_price

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"
DB_PATH = Path(os.getenv("VECTOR_WEALTH_DB_PATH", str(Path(__file__).resolve().parent / "vector_wealth_db")))
OPPORTUNITIES_PATH = DB_PATH / "opportunities.json"

load_dotenv(ENV_PATH)

# Configuration
SCANNER_ENABLED = os.getenv("SCANNER_ENABLED", "true").strip().lower() in {"1", "true", "yes"}
SCANNER_SENTIMENT_THRESHOLD = float(os.getenv("SCANNER_SENTIMENT_THRESHOLD", "0.15"))
SCANNER_MAX_CANDIDATES = int(os.getenv("SCANNER_MAX_CANDIDATES", "20"))
SCANNER_TOP_OPPORTUNITIES = int(os.getenv("SCANNER_TOP_OPPORTUNITIES", "5"))
SCANNER_LOOKBACK_HOURS = int(os.getenv("SCANNER_LOOKBACK_HOURS", "48"))


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def _ist_now() -> datetime:
    """Get current time in IST (UTC+5:30)"""
    return datetime.now(UTC) + timedelta(hours=5, minutes=30)


def is_market_hours() -> bool:
    """Check if within Indian stock market hours (9:15 AM - 3:30 PM IST)"""
    now = _ist_now()
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    # Also check if it's a weekday (Monday=0 to Friday=4)
    is_weekday = now.weekday() < 5
    return is_weekday and market_open <= now <= market_close


def should_run_scanner() -> tuple[bool, str]:
    """
    Determine if scanner should run and why.
    Returns: (should_run, reason)
    """
    now = _ist_now()
    hour = now.hour
    minute = now.minute
    is_weekday = now.weekday() < 5
    
    if not is_weekday:
        return False, "weekend"
    
    # Pre-market prep (8:30 - 9:15 AM)
    if hour == 8 and minute >= 30:
        return True, "pre_market"
    if hour == 9 and minute < 15:
        return True, "pre_market"
    
    # Market hours (9:15 AM - 3:30 PM)
    if is_market_hours():
        return True, "market_hours"
    
    # Post-market digest (3:30 - 5:00 PM)
    if hour == 15 and minute >= 30:
        return True, "post_market"
    if hour == 16:
        return True, "post_market"
    
    # Outside actionable hours
    return False, "after_hours"


@dataclass
class Opportunity:
    """A stock opportunity identified by the scanner"""
    ticker: str
    sentiment: float
    news_count: int
    headlines: list[str]
    reasoning: str
    confidence: float
    scan_type: str  # pre_market, market_hours, post_market
    scanned_at: str
    current_price: float | None = None
    price_change: float | None = None
    price_change_percent: float | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScanResult:
    """Result of an opportunity scan"""
    success: bool
    scan_type: str
    candidates_found: int
    opportunities: list[Opportunity]
    scanned_at: str
    message: str
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "scan_type": self.scan_type,
            "candidates_found": self.candidates_found,
            "opportunities": [o.to_dict() for o in self.opportunities],
            "scanned_at": self.scanned_at,
            "message": self.message,
        }


class OpportunityScanner:
    """
    Hybrid opportunity scanner:
    1. Script: Fast sentiment filter across all stocks
    2. Agent: LLM picks top opportunities with reasoning
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self._last_scan: ScanResult | None = None
        self._opportunities: list[Opportunity] = []
        self._load_opportunities()
    
    def _load_opportunities(self) -> None:
        """Load previously stored opportunities"""
        if OPPORTUNITIES_PATH.exists():
            try:
                with open(OPPORTUNITIES_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._opportunities = [
                        Opportunity(**o) for o in data.get("opportunities", [])
                    ]
            except Exception:
                self._opportunities = []
    
    def _save_opportunities(self) -> None:
        """Persist opportunities to disk"""
        try:
            OPPORTUNITIES_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(OPPORTUNITIES_PATH, "w", encoding="utf-8") as f:
                json.dump({
                    "opportunities": [o.to_dict() for o in self._opportunities],
                    "updated_at": _utcnow_iso(),
                }, f, indent=2)
        except Exception:
            pass
    
    def _get_genai_client(self) -> genai.Client:
        """Get Gemini client"""
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not configured")
        return genai.Client(api_key=api_key)
    
    def _fetch_recent_news_by_ticker(self) -> dict[str, list[dict[str, str]]]:
        """
        Fetch all news from last N hours, grouped by ticker.
        Returns: {ticker: [{title, description, date}, ...]}
        """
        cutoff = datetime.now(UTC) - timedelta(hours=SCANNER_LOOKBACK_HOURS)
        cutoff_iso = cutoff.isoformat()
        
        # Get all documents from collection
        total_docs = news_collection.count()
        if total_docs == 0:
            return {}
        
        # Fetch in batches
        batch_size = 500
        all_docs: dict[str, list[dict[str, str]]] = {}
        offset = 0
        
        while offset < total_docs:
            result = news_collection.get(
                limit=batch_size,
                offset=offset,
                include=["documents", "metadatas"],
            )
            
            ids = result.get("ids", []) or []
            documents = result.get("documents", []) or []
            metadatas = result.get("metadatas", []) or []
            
            if not ids:
                break
            
            for idx, doc_id in enumerate(ids):
                metadata = metadatas[idx] if idx < len(metadatas) else {}
                document = documents[idx] if idx < len(documents) else ""
                
                # Check date
                ingested_at = metadata.get("ingested_at", "") or metadata.get("published_at", "")
                if ingested_at and ingested_at < cutoff_iso:
                    continue
                
                # Get ticker tags
                ticker_tags_raw = metadata.get("ticker_tags", "")
                if not ticker_tags_raw:
                    continue
                
                tickers = [t.strip().upper() for t in ticker_tags_raw.split(",") if t.strip()]
                
                # Handle both uppercase and lowercase field names
                title = metadata.get("Title", "") or metadata.get("title", "") or ""
                description = metadata.get("Description", "") or metadata.get("description", "") or ""
                date = metadata.get("published_at", "") or ingested_at
                
                for ticker in tickers:
                    if ticker not in all_docs:
                        all_docs[ticker] = []
                    all_docs[ticker].append({
                        "title": title,
                        "description": description,
                        "date": date,
                    })
            
            offset += len(ids)
        
        return all_docs
    
    def _calculate_sentiment_for_ticker(self, news_items: list[dict[str, str]]) -> float:
        """Calculate combined sentiment for a ticker's news"""
        if not news_items:
            return 0.0
        
        combined_text = " ".join([
            f"{item.get('title', '')} {item.get('description', '')}"
            for item in news_items
        ])
        
        return _compute_sentiment(combined_text)
    
    def _step1_filter_candidates(self) -> list[dict[str, Any]]:
        """
        Step 1: Script-based fast filter.
        Returns stocks with sentiment > threshold.
        """
        news_by_ticker = self._fetch_recent_news_by_ticker()
        
        if not news_by_ticker:
            return []
        
        candidates = []
        for ticker, news_items in news_by_ticker.items():
            sentiment = self._calculate_sentiment_for_ticker(news_items)
            
            if sentiment > SCANNER_SENTIMENT_THRESHOLD:
                headlines = [item.get("title", "") for item in news_items[:5]]
                candidates.append({
                    "ticker": ticker,
                    "sentiment": sentiment,
                    "news_count": len(news_items),
                    "headlines": headlines,
                })
        
        # Sort by sentiment descending, limit candidates
        candidates.sort(key=lambda x: x["sentiment"], reverse=True)
        return candidates[:SCANNER_MAX_CANDIDATES]
    
    def _step2_agent_select(
        self, 
        candidates: list[dict[str, Any]], 
        scan_type: str
    ) -> list[Opportunity]:
        """
        Step 2: LLM agent picks top opportunities with reasoning.
        Single API call with all candidates.
        """
        if not candidates:
            return []
        
        # Build prompt
        candidates_text = ""
        for idx, c in enumerate(candidates, 1):
            headlines_str = "; ".join(c["headlines"][:3])
            candidates_text += f"{idx}. {c['ticker']} (sentiment: {c['sentiment']:.2f}, {c['news_count']} articles)\n"
            candidates_text += f"   Headlines: {headlines_str}\n\n"
        
        scan_context = {
            "pre_market": "This is a PRE-MARKET scan (8:30 AM). Focus on stocks that could move at market open.",
            "market_hours": "This is during MARKET HOURS. Focus on immediate actionable opportunities.",
            "post_market": "This is a POST-MARKET scan. Identify stocks to watch for tomorrow.",
        }
        
        prompt = f"""You are a stock market analyst. Analyze these {len(candidates)} stocks with positive news sentiment and select the TOP {SCANNER_TOP_OPPORTUNITIES} best BUY opportunities.

{scan_context.get(scan_type, "")}

CANDIDATES:
{candidates_text}

For each selection, consider:
1. News strength and momentum
2. Sector diversification (avoid picking too many from same sector)
3. Confidence level based on news quality

Return ONLY valid JSON array (no markdown):
[
  {{"ticker": "SYMBOL", "reasoning": "brief 1-2 sentence reason", "confidence": 0.0-1.0}},
  ...
]

Pick exactly {SCANNER_TOP_OPPORTUNITIES} stocks, ordered by confidence (highest first).
"""

        try:
            client = self._get_genai_client()
            response = client.models.generate_content(
                model=GENERATION_MODEL,
                contents=prompt,
            )
            
            response_text = response.text.strip()
            # Clean markdown if present
            if response_text.startswith("```"):
                response_text = re.sub(r"```(?:json)?\n?", "", response_text)
                response_text = response_text.strip()
            
            selections = json.loads(response_text)
            
            # Build Opportunity objects
            opportunities = []
            candidate_map = {c["ticker"]: c for c in candidates}
            
            for sel in selections[:SCANNER_TOP_OPPORTUNITIES]:
                ticker = sel.get("ticker", "").upper()
                if ticker not in candidate_map:
                    continue
                
                c = candidate_map[ticker]
                price_data = fetch_stock_price(ticker)
                
                opportunities.append(Opportunity(
                    ticker=ticker,
                    sentiment=c["sentiment"],
                    news_count=c["news_count"],
                    headlines=c["headlines"],
                    reasoning=sel.get("reasoning", ""),
                    confidence=float(sel.get("confidence", 0.7)),
                    scan_type=scan_type,
                    scanned_at=_utcnow_iso(),
                    current_price=price_data.get("current_price"),
                    price_change=price_data.get("price_change"),
                    price_change_percent=price_data.get("price_change_percent"),
                ))
            
            return opportunities
            
        except Exception as e:
            # Fallback: Return top N by sentiment without LLM reasoning
            opportunities = []
            for c in candidates[:SCANNER_TOP_OPPORTUNITIES]:
                price_data = fetch_stock_price(c["ticker"])
                
                opportunities.append(Opportunity(
                    ticker=c["ticker"],
                    sentiment=c["sentiment"],
                    news_count=c["news_count"],
                    headlines=c["headlines"],
                    reasoning="High positive sentiment in recent news",
                    confidence=min(0.5 + c["sentiment"], 0.9),
                    scan_type=scan_type,
                    scanned_at=_utcnow_iso(),
                    current_price=price_data.get("current_price"),
                    price_change=price_data.get("price_change"),
                    price_change_percent=price_data.get("price_change_percent"),
                ))
            return opportunities
    
    def scan(self, scan_type: str = "market_hours") -> ScanResult:
        """
        Run the hybrid opportunity scan.
        
        Args:
            scan_type: "pre_market", "market_hours", or "post_market"
        
        Returns:
            ScanResult with opportunities
        """
        with self._lock:
            scanned_at = _utcnow_iso()
            
            if not SCANNER_ENABLED:
                return ScanResult(
                    success=False,
                    scan_type=scan_type,
                    candidates_found=0,
                    opportunities=[],
                    scanned_at=scanned_at,
                    message="Scanner is disabled",
                )
            
            try:
                # Step 1: Fast filter
                candidates = self._step1_filter_candidates()
                
                if not candidates:
                    result = ScanResult(
                        success=True,
                        scan_type=scan_type,
                        candidates_found=0,
                        opportunities=[],
                        scanned_at=scanned_at,
                        message="No positive candidates found",
                    )
                    self._last_scan = result
                    return result
                
                # Step 2: LLM selection
                opportunities = self._step2_agent_select(candidates, scan_type)
                
                # Update stored opportunities
                self._opportunities = opportunities
                self._save_opportunities()
                
                result = ScanResult(
                    success=True,
                    scan_type=scan_type,
                    candidates_found=len(candidates),
                    opportunities=opportunities,
                    scanned_at=scanned_at,
                    message=f"Found {len(opportunities)} opportunities from {len(candidates)} candidates",
                )
                self._last_scan = result
                return result
                
            except Exception as e:
                return ScanResult(
                    success=False,
                    scan_type=scan_type,
                    candidates_found=0,
                    opportunities=[],
                    scanned_at=scanned_at,
                    message=str(e),
                )
    
    def get_opportunities(self) -> list[dict[str, Any]]:
        """Get current opportunities for API response"""
        with self._lock:
            return [o.to_dict() for o in self._opportunities]
    
    def get_status(self) -> dict[str, Any]:
        """Get scanner status"""
        should_run, reason = should_run_scanner()
        return {
            "enabled": SCANNER_ENABLED,
            "sentiment_threshold": SCANNER_SENTIMENT_THRESHOLD,
            "max_candidates": SCANNER_MAX_CANDIDATES,
            "top_opportunities": SCANNER_TOP_OPPORTUNITIES,
            "lookback_hours": SCANNER_LOOKBACK_HOURS,
            "is_market_hours": is_market_hours(),
            "should_run_now": should_run,
            "current_mode": reason,
            "last_scan": self._last_scan.to_dict() if self._last_scan else None,
            "opportunities_count": len(self._opportunities),
        }


# Singleton instance
opportunity_scanner = OpportunityScanner()
