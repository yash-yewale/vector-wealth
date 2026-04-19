"""
Vector Wealth analysis pipeline and LangGraph agents.

Slim orchestration layer — delegates to:
  - sentiment.py for scoring
  - price_service.py for stock prices and peers
  - ai_summary.py for Gemini summaries
  - stock_data.py for shared data
"""
from __future__ import annotations

import csv
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, TypedDict

import chromadb
import requests
from dotenv import load_dotenv
from google import genai
from langgraph.graph import END, StateGraph

from ai_summary import generate_ai_summary
from price_service import fetch_peer_comparison, fetch_stock_price
from sentiment import (
    average_sentiment,
    build_explanation,
    compute_confidence,
    compute_sentiment,
    extract_drivers,
    latest_news_date,
    parse_datetime_text,
    weighted_pattern_sentiment,
)
from stock_data import (
    GENERIC_STOCK_TERMS,
    QUERY_STOPWORDS,
    SOURCE_QUALITY_WEIGHTS,
    STOCK_ALIASES,
    TICKER_SUFFIX_SPLITS,
)

# ─── Configuration ───────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"
DB_PATH = Path(os.getenv("VECTOR_WEALTH_DB_PATH", str(Path(__file__).resolve().parent / "vector_wealth_db")))
NEWS_CSV_PATH = ROOT_DIR / "data" / "IndianFinancialNews.csv"
COLLECTION_NAME = "market_news"
EMBEDDING_MODELS = ("text-embedding-004", "gemini-embedding-001")
GENERATION_MODEL = "gemini-2.5-flash"
API_MAX_RETRIES = 4
DEFAULT_RETRY_DELAY_SECONDS = 20.0
USE_GENAI_ANALYSIS = os.getenv("USE_GENAI_ANALYSIS", "false").strip().lower() in {
    "1", "true", "yes",
}
ENABLE_AI_SUMMARY = os.getenv("ENABLE_AI_SUMMARY", "true").strip().lower() in {
    "1", "true", "yes",
}
FAST_NEWS_MAX_AGE_DAYS = max(1, int(os.getenv("FAST_NEWS_MAX_AGE_DAYS", "30")))
FAST_NEWS_MAX_CANDIDATES = max(20, int(os.getenv("FAST_NEWS_MAX_CANDIDATES", "120")))

ONDEMAND_FETCH_TIMEOUT = 15
ONDEMAND_MAX_ARTICLES = 10


class VectorWealthState(TypedDict, total=False):
    query: str
    retrieved_docs: list[dict[str, Any]]
    sentiment: float
    now_sentiment: float
    pattern_sentiment: float
    confidence: float
    recent_news_count: int
    pattern_news_count: int
    latest_news_date: str
    stale_data: bool
    stale_reason: str
    explanation: str
    positive_drivers: list[str]
    negative_drivers: list[str]
    final_decision: str
    current_price: float | None
    price_change: float | None
    price_change_percent: float | None
    ai_summary: str | None
    peers: list[dict[str, Any]] | None


load_dotenv(ENV_PATH)
chroma_client = chromadb.PersistentClient(path=str(DB_PATH))
news_collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)


# ─── Ticker Extraction & Search ─────────────────────────────────────────────

def _extract_ticker(query: str) -> str:
    upper_query = query.upper()
    match = re.search(r"\bON\s+([A-Z][A-Z0-9._-]{1,14})\b", upper_query)
    if match:
        return match.group(1)
    candidates = re.findall(r"\b[A-Z][A-Z0-9._-]{1,14}\b", upper_query)
    if candidates:
        return candidates[-1]
    return "MARKET"


def _extract_search_phrase(query: str) -> str:
    upper_query = (query or "").upper().strip()
    if not upper_query:
        return ""
    phrase_match = re.search(r"\bON\s+(.+?)(?:\?|$)", upper_query)
    if phrase_match:
        return phrase_match.group(1).strip()
    return _extract_ticker(upper_query)


def _normalize_term(term: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (term or "").lower()).strip()


def _contains_term(haystack: str, term: str) -> bool:
    normalized_term = _normalize_term(term)
    if not normalized_term:
        return False
    if " " in normalized_term:
        return normalized_term in haystack
    return re.search(rf"\b{re.escape(normalized_term)}\b", haystack) is not None


def _parse_ticker_tags(raw_value: Any) -> set[str]:
    if raw_value is None:
        return set()
    if isinstance(raw_value, str):
        parts = [part.strip().upper() for part in raw_value.split(",") if part.strip()]
        return set(parts)
    return set()


def _build_ticker_terms(ticker: str) -> list[str]:
    raw = (ticker or "").strip()
    if not raw:
        return []

    upper = raw.upper()
    if upper == "MARKET":
        return []

    normalized_input = _normalize_term(raw)
    normalized_compact = re.sub(r"[^A-Z0-9]+", "", upper)
    is_single_word = " " not in normalized_input
    alias_input_match = False

    terms: set[str] = set()

    if normalized_input:
        terms.add(normalized_input)
    if normalized_compact:
        terms.add(normalized_compact.lower())

    for part in normalized_input.split():
        if len(part) > 2 and part not in GENERIC_STOCK_TERMS:
            terms.add(part)

    for suffix in TICKER_SUFFIX_SPLITS:
        if normalized_compact.endswith(suffix) and len(normalized_compact) > len(suffix) + 1:
            prefix = normalized_compact[: -len(suffix)].strip()
            if prefix:
                terms.add(f"{prefix.lower()} {suffix.lower()}")

    if normalized_compact in STOCK_ALIASES:
        for alias in STOCK_ALIASES[normalized_compact]:
            alias_norm = _normalize_term(alias)
            if alias_norm:
                terms.add(alias_norm)

    for symbol, aliases in STOCK_ALIASES.items():
        for alias in aliases:
            alias_norm = _normalize_term(alias)
            if alias_norm and alias_norm == normalized_input:
                alias_input_match = True
                terms.add(symbol.lower())
                for other_alias in aliases:
                    other_norm = _normalize_term(other_alias)
                    if other_norm:
                        terms.add(other_norm)

    if is_single_word and not alias_input_match and normalized_compact not in STOCK_ALIASES:
        if len(normalized_compact) > 6:
            return []

    filtered = [
        term
        for term in terms
        if len(term) > 1 and not (len(term) <= 4 and term in GENERIC_STOCK_TERMS)
    ]

    return sorted(filtered, key=len, reverse=True)


# ─── On-Demand News Fetching ────────────────────────────────────────────────

def _build_search_terms_for_ticker(ticker: str) -> list[str]:
    terms = [ticker]
    normalized = ticker.upper().strip()
    if normalized in STOCK_ALIASES:
        terms.extend(STOCK_ALIASES[normalized])
    for suffix in TICKER_SUFFIX_SPLITS:
        if normalized.endswith(suffix) and len(normalized) > len(suffix):
            base = normalized[:-len(suffix)]
            if len(base) >= 2:
                terms.append(base)
                break
    return list(set(terms))


def _fetch_news_ondemand(ticker: str, limit: int = ONDEMAND_MAX_ARTICLES) -> list[dict[str, str]]:
    newsapi_key = os.getenv("NEWSAPI_KEY", "").strip()
    if not newsapi_key:
        return []

    search_terms = _build_search_terms_for_ticker(ticker)
    query_parts = [f'"{term}"' if " " in term else term for term in search_terms[:5]]
    query_string = " OR ".join(query_parts)
    full_query = f"({query_string}) AND (India OR NSE OR BSE OR stock OR shares OR Sensex OR Nifty)"

    try:
        from_dt = datetime.now(UTC) - timedelta(days=30)
        response = requests.get(
            "https://newsapi.org/v2/everything",
            headers={"X-Api-Key": newsapi_key},
            params={
                "q": full_query,
                "from": from_dt.strftime("%Y-%m-%d"),
                "language": "en",
                "sortBy": "relevancy",
                "pageSize": min(limit * 3, 100),
            },
            timeout=ONDEMAND_FETCH_TIMEOUT,
        )

        if response.status_code >= 400:
            return []

        payload = response.json()
        if payload.get("status") != "ok":
            return []

        raw_articles = payload.get("articles", [])
        parsed: list[dict[str, str]] = []
        match_terms_lower = [t.lower() for t in search_terms]

        for item in raw_articles:
            if len(parsed) >= limit:
                break
            title = str(item.get("title") or "").strip()
            description = str(item.get("description") or "").strip()
            content = str(item.get("content") or "").strip()
            published_at = str(item.get("publishedAt") or "").strip()
            source_name = str((item.get("source") or {}).get("name") or "").strip()

            if not title or len(title) < 10:
                continue

            merged_description = description or content
            if len(merged_description) < 20:
                merged_description = title

            combined_text = f"{title} {merged_description}".lower()
            is_relevant = any(term in combined_text for term in match_terms_lower)

            if not is_relevant:
                continue

            date_str = published_at[:10] if published_at else ""
            parsed.append({
                "Date": date_str,
                "Title": title,
                "Description": merged_description,
                "Source": source_name or "NewsAPI",
            })

        return parsed

    except Exception:
        return []


# ─── News Retrieval ──────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_news_rows() -> list[dict[str, str]]:
    if not NEWS_CSV_PATH.exists():
        return []
    rows: list[dict[str, str]] = []
    with NEWS_CSV_PATH.open("r", encoding="utf-8-sig", errors="ignore", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            rows.append({
                "Date": str(row.get("Date", "") or "").strip(),
                "Title": str(row.get("Title", "") or "").strip(),
                "Description": str(row.get("Description", "") or "").strip(),
            })
    return rows


def _retrieve_local_news(query: str, ticker: str, limit: int = 5) -> list[dict[str, str]]:
    rows = _load_news_rows()
    if not rows:
        return []

    query_terms = [
        term for term in re.findall(r"[A-Za-z0-9]+", query.lower())
        if len(term) > 2 and term not in QUERY_STOPWORDS
    ]
    ticker_terms = _build_ticker_terms(ticker)
    require_ticker_match = ticker != "MARKET"

    scored: list[tuple[int, float, dict[str, str]]] = []
    for row in rows:
        row_dt = parse_datetime_text(str(row.get("Date", "") or ""))
        row_ts = row_dt.timestamp() if row_dt is not None else 0.0
        haystack = _normalize_term(f"{row.get('Title', '')} {row.get('Description', '')}")
        score = 0
        ticker_matched = False

        for ticker_term in ticker_terms:
            if _contains_term(haystack, ticker_term):
                score += 5
                ticker_matched = True
                break

        if require_ticker_match and not ticker_matched:
            continue

        for term in query_terms:
            if term in haystack:
                score += 1

        if score > 0:
            enriched = dict(row)
            enriched["Source"] = "historical_csv"
            scored.append((score, row_ts, enriched))

    if not scored:
        return []

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [row for _, _, row in scored[:limit]]


def _parse_metadata_timestamp(metadata: dict[str, Any]) -> float:
    published_at = str(metadata.get("published_at", "") or "").strip()
    parsed = parse_datetime_text(published_at)
    if parsed is None:
        date_value = str(metadata.get("Date", "") or "").strip()
        parsed = parse_datetime_text(date_value)
    if parsed is None:
        return 0.0
    return parsed.timestamp()


def _retrieve_chroma_news(query: str, ticker: str, limit: int = 5) -> list[dict[str, str]]:
    query_terms = [
        term for term in re.findall(r"[A-Za-z0-9]+", query.lower())
        if len(term) > 2 and term not in QUERY_STOPWORDS
    ]
    ticker_terms = _build_ticker_terms(ticker)
    require_ticker_match = ticker != "MARKET"

    try:
        response = news_collection.get(limit=1500, include=["documents", "metadatas"])
    except Exception:
        return []

    ids = response.get("ids", []) or []
    documents = response.get("documents", []) or []
    metadatas = response.get("metadatas", []) or []

    if not ids:
        return []

    scored: list[tuple[int, float, dict[str, str]]] = []
    for idx, _ in enumerate(ids):
        metadata_raw = metadatas[idx] if idx < len(metadatas) else {}
        metadata = metadata_raw if isinstance(metadata_raw, dict) else {}

        title = str(metadata.get("Title", "") or "").strip()
        description = str(metadata.get("Description", "") or "").strip()
        if not description and idx < len(documents):
            description = str(documents[idx] or "").strip()
        date_value = str(metadata.get("Date", "") or "").strip()
        source_value = str(metadata.get("source", "") or "").strip()
        ticker_tags = _parse_ticker_tags(metadata.get("ticker_tags"))

        haystack = _normalize_term(f"{title} {description}")
        score = 0
        ticker_matched = False

        for ticker_term in ticker_terms:
            compact_term = re.sub(r"[^a-z0-9]+", "", ticker_term.lower())
            if compact_term and compact_term.upper() in ticker_tags:
                score += 6
                ticker_matched = True
                break
            if _contains_term(haystack, ticker_term):
                score += 5
                ticker_matched = True
                break

        if require_ticker_match and not ticker_matched:
            continue

        for term in query_terms:
            if term in haystack:
                score += 1

        if score > 0:
            row = {
                "Date": date_value,
                "Title": title,
                "Description": description,
                "Source": source_value,
            }
            recency_score = _parse_metadata_timestamp(metadata)
            scored.append((score, recency_score, row))

    if not scored:
        return []

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [row for _, _, row in scored[:limit]]


# ─── Deduplication & Splitting ───────────────────────────────────────────────

def _dedupe_news_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    def _dedupe_key(row: dict[str, str]) -> str:
        title = str(row.get("Title", "") or "").strip().lower()
        title = re.sub(r"[^a-z0-9 ]+", " ", title)
        title = re.sub(r"\b\d+(?:\.\d+)?\b", " ", title)
        title = re.sub(r"\s+", " ", title).strip()
        title_tokens = [tok for tok in title.split(" ") if tok]
        compact_title = " ".join(title_tokens[:12])
        date_value = str(row.get("Date", "") or "").strip().lower()
        return f"{compact_title}|{date_value}"

    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for row in rows:
        title = str(row.get("Title", "") or "").strip().lower()
        key = _dedupe_key(row)
        if not title:
            continue
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _split_recent_and_historical(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    cutoff_dt = datetime.now(UTC) - timedelta(days=FAST_NEWS_MAX_AGE_DAYS)
    recent_rows: list[dict[str, str]] = []
    historical_rows: list[dict[str, str]] = []

    for row in rows:
        parsed_dt = parse_datetime_text(str(row.get("Date", "") or ""))
        if parsed_dt is not None and parsed_dt >= cutoff_dt:
            recent_rows.append(row)
        else:
            historical_rows.append(row)

    return recent_rows, historical_rows


# ─── Fast Analysis Pipeline (no LLM) ────────────────────────────────────────

def run_fast_analysis(query: str) -> VectorWealthState:
    search_phrase = _extract_search_phrase(query)
    ticker = _extract_ticker(query)
    match_key = search_phrase or ticker

    chroma_rows = _retrieve_chroma_news(query=query, ticker=match_key, limit=FAST_NEWS_MAX_CANDIDATES)
    local_rows = _retrieve_local_news(query=query, ticker=match_key, limit=FAST_NEWS_MAX_CANDIDATES)
    all_rows = _dedupe_news_rows(chroma_rows + local_rows)

    ondemand_fetched = False
    if not all_rows and match_key and match_key != "MARKET":
        ondemand_rows = _fetch_news_ondemand(match_key, limit=ONDEMAND_MAX_ARTICLES)
        if ondemand_rows:
            all_rows = ondemand_rows
            ondemand_fetched = True

    recent_rows, historical_rows = _split_recent_and_historical(all_rows)
    recent_rows = recent_rows[:5]
    historical_rows = historical_rows[:5]
    pattern_rows = (recent_rows + historical_rows)[:FAST_NEWS_MAX_CANDIDATES]
    recent_news_count = len(recent_rows)
    pattern_news_count = len(pattern_rows)
    latest_date = latest_news_date(pattern_rows)

    no_data_at_all = recent_news_count == 0 and pattern_news_count == 0
    stale_data = recent_news_count == 0 and pattern_news_count > 0

    if no_data_at_all:
        stale_reason = f"No news data found for '{match_key}'. This stock may not have recent coverage in our data sources."
    elif stale_data:
        stale_reason = f"No recent matched headlines in last {FAST_NEWS_MAX_AGE_DAYS} days."
    else:
        stale_reason = ""

    if ondemand_fetched:
        stale_reason = f"Live news fetched for '{match_key}' (no cached data)." if not stale_reason else stale_reason

    news_rows = recent_rows if recent_rows else historical_rows

    retrieved_docs: list[dict[str, Any]] = [
        {
            "content": row.get("Description", ""),
            "metadata": {
                "Date": row.get("Date", ""),
                "Title": row.get("Title", ""),
            },
            "distance": None,
        }
        for row in news_rows
    ]

    now_sentiment = average_sentiment(recent_rows)
    pattern_sentiment = weighted_pattern_sentiment(pattern_rows)
    if recent_rows:
        sentiment = (0.7 * now_sentiment) + (0.3 * pattern_sentiment)
    else:
        sentiment = pattern_sentiment * 0.35

    if not recent_rows:
        final_decision = "HOLD"
    elif sentiment >= 0.2:
        final_decision = "BUY"
    elif sentiment <= -0.2:
        final_decision = "SELL"
    else:
        final_decision = "HOLD"

    positive_drivers, negative_drivers = extract_drivers(pattern_rows)
    explanation = build_explanation(
        sentiment=sentiment,
        now_sentiment=now_sentiment,
        pattern_sentiment=pattern_sentiment,
        recent_count=recent_news_count,
        pattern_count=pattern_news_count,
        latest_news_date=latest_date,
        recommendation=final_decision,
        ondemand_fetched=ondemand_fetched,
        ticker=match_key,
        fast_news_max_age_days=FAST_NEWS_MAX_AGE_DAYS,
    )

    display_stale = stale_data or no_data_at_all

    sentiment = max(-1.0, min(1.0, sentiment))
    state = {
        "query": query,
        "retrieved_docs": retrieved_docs,
        "sentiment": sentiment,
        "now_sentiment": max(-1.0, min(1.0, now_sentiment)),
        "pattern_sentiment": max(-1.0, min(1.0, pattern_sentiment)),
        "confidence": compute_confidence(recent_news_count, pattern_news_count),
        "recent_news_count": recent_news_count,
        "pattern_news_count": pattern_news_count,
        "latest_news_date": latest_date,
        "stale_data": display_stale,
        "stale_reason": stale_reason,
        "explanation": explanation,
        "positive_drivers": positive_drivers,
        "negative_drivers": negative_drivers,
        "final_decision": final_decision,
    }
    return _enrich_state(state, match_key)


def _enrich_state(state: VectorWealthState, ticker: str) -> VectorWealthState:
    """Add price, peers, and AI summary to state."""
    if not ticker or ticker == "MARKET":
        state["current_price"] = None
        state["price_change"] = None
        state["price_change_percent"] = None
        state["peers"] = None
        state["ai_summary"] = None
        return state

    headlines = [doc.get("metadata", {}).get("Title", "") for doc in state.get("retrieved_docs", [])]
    headlines = [h for h in headlines if h]
    sentiment = state.get("sentiment", 0.0)

    price_data = {"current_price": None, "price_change": None, "price_change_percent": None}
    ai_summary = None

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {}
        futures["price"] = executor.submit(fetch_stock_price, ticker)
        if ENABLE_AI_SUMMARY and headlines:
            futures["ai"] = executor.submit(generate_ai_summary, ticker, headlines, sentiment)

        for key, future in futures.items():
            try:
                if key == "price":
                    price_data = future.result(timeout=10)
                elif key == "ai":
                    ai_summary = future.result(timeout=15)
            except Exception:
                pass

    state["current_price"] = price_data.get("current_price")
    state["price_change"] = price_data.get("price_change")
    state["price_change_percent"] = price_data.get("price_change_percent")
    state["ai_summary"] = ai_summary
    state["peers"] = fetch_peer_comparison(ticker)
    return state


# ─── LLM Agents (GenAI mode) ────────────────────────────────────────────────

def _extract_retry_delay_seconds(error: Exception) -> float:
    message = str(error)
    decimal_match = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", message, flags=re.IGNORECASE)
    if decimal_match:
        return float(decimal_match.group(1))
    int_match = re.search(r"retryDelay['\"]?\s*[:=]\s*['\"]?([0-9]+)s", message, flags=re.IGNORECASE)
    if int_match:
        return float(int_match.group(1))
    return DEFAULT_RETRY_DELAY_SECONDS


def _is_quota_error(error: Exception) -> bool:
    message = str(error)
    return "429" in message or "RESOURCE_EXHAUSTED" in message


def _call_with_quota_retry(callable_fn, operation_name: str):
    attempt = 1
    backoff_seconds = 1.5
    while attempt <= API_MAX_RETRIES:
        try:
            return callable_fn()
        except Exception as exc:
            if not _is_quota_error(exc):
                raise RuntimeError(f"{operation_name} failed: {exc}") from exc
            if attempt == API_MAX_RETRIES:
                raise RuntimeError(f"{operation_name} failed due to API quota: {exc}") from exc
            retry_delay = _extract_retry_delay_seconds(exc)
            sleep_for = max(retry_delay + 0.5, backoff_seconds)
            time.sleep(sleep_for)
            backoff_seconds = min(backoff_seconds * 2, 45.0)
            attempt += 1


def get_genai_client() -> genai.Client:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is missing in root .env.")
    return genai.Client(api_key=api_key)


def embed_texts(genai_client: genai.Client, texts: list[str]):
    last_error: Exception | None = None
    for model_name in EMBEDDING_MODELS:
        try:
            return _call_with_quota_retry(
                lambda: genai_client.models.embed_content(model=model_name, contents=texts),
                operation_name=f"Embedding ({model_name})",
            )
        except Exception as exc:
            last_error = exc
            continue
    if last_error:
        raise RuntimeError(f"Embedding failed for all configured models: {last_error}") from last_error
    raise RuntimeError("Embedding failed: no models configured.")


def scout_agent(state: VectorWealthState) -> VectorWealthState:
    genai_client = get_genai_client()
    query = state.get("query", "")
    if not query:
        return {"retrieved_docs": []}

    emb = embed_texts(genai_client, [query])
    query_vector = emb.embeddings[0].values

    result = news_collection.query(
        query_embeddings=[query_vector],
        n_results=5,
        include=["documents", "metadatas", "distances"],
    )

    docs: list[dict[str, Any]] = []
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    for idx, doc in enumerate(documents):
        metadata = metadatas[idx] if idx < len(metadatas) else {}
        distance = distances[idx] if idx < len(distances) else None
        docs.append({"content": doc, "metadata": metadata or {}, "distance": distance})

    return {"retrieved_docs": docs}


def analyst_advisor_agent(state: VectorWealthState) -> VectorWealthState:
    """Merged Analyst + Advisor agent. Single LLM call."""
    genai_client = get_genai_client()
    docs = state.get("retrieved_docs", [])

    if not docs:
        return {
            "sentiment": 0.0,
            "final_decision": "HOLD",
            "explanation": "No news data available for analysis.",
        }

    joined_news = "\n\n".join([
        f"Title: {doc.get('metadata', {}).get('Title', '')}\n"
        f"Date: {doc.get('metadata', {}).get('Date', '')}\n"
        f"Content: {doc.get('content', '')}"
        for doc in docs
    ])

    prompt = (
        "You are a financial analyst and investment advisor for Indian equities.\n\n"
        "Analyze the following news and provide:\n"
        "1. A sentiment score between -1 (very negative) and 1 (very positive)\n"
        "2. An investment decision: BUY, HOLD, or SELL\n"
        "3. A brief explanation (1-2 sentences)\n\n"
        "Respond with JSON only using this format:\n"
        '{"sentiment": <float>, "decision": "<BUY|HOLD|SELL>", "explanation": "<string>"}\n\n'
        f"User query: {state.get('query', '')}\n\n"
        f"News:\n{joined_news}"
    )

    response = _call_with_quota_retry(
        lambda: genai_client.models.generate_content(model=GENERATION_MODEL, contents=prompt),
        operation_name="Analysis and decision generation",
    )

    text = (response.text or "").strip()
    sentiment = 0.0
    decision = "HOLD"
    explanation = ""

    try:
        parsed = json.loads(text)
        sentiment = float(parsed.get("sentiment", 0.0))
        proposed = str(parsed.get("decision", "HOLD")).upper()
        if proposed in {"BUY", "HOLD", "SELL"}:
            decision = proposed
        explanation = str(parsed.get("explanation", ""))
    except Exception:
        try:
            sent_match = re.search(r'"sentiment":\s*(-?[\d.]+)', text)
            if sent_match:
                sentiment = float(sent_match.group(1))
            if "BUY" in text.upper():
                decision = "BUY"
            elif "SELL" in text.upper():
                decision = "SELL"
        except Exception:
            pass

    sentiment = max(-1.0, min(1.0, sentiment))
    return {"sentiment": sentiment, "final_decision": decision, "explanation": explanation}


def build_vector_wealth_graph():
    """Build optimized 2-agent workflow: Scout → Analyst+Advisor"""
    graph_builder = StateGraph(VectorWealthState)
    graph_builder.add_node("scout", scout_agent)
    graph_builder.add_node("analyst_advisor", analyst_advisor_agent)
    graph_builder.set_entry_point("scout")
    graph_builder.add_edge("scout", "analyst_advisor")
    graph_builder.add_edge("analyst_advisor", END)
    return graph_builder.compile()


vector_wealth_workflow = build_vector_wealth_graph()


def run_analysis(query: str) -> VectorWealthState:
    if not USE_GENAI_ANALYSIS:
        return run_fast_analysis(query)
    initial_state: VectorWealthState = {"query": query}
    try:
        result = vector_wealth_workflow.invoke(initial_state)
        ticker = _extract_ticker(query)
        return _enrich_state(result, ticker)
    except Exception:
        return run_fast_analysis(query)
