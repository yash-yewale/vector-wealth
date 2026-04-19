from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import chromadb
import requests
from dotenv import load_dotenv
from google import genai

from stock_data import SECTOR_QUERIES, STOCK_ALIASES


ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"
DB_PATH = Path(os.getenv("VECTOR_WEALTH_DB_PATH", str(Path(__file__).resolve().parent / "vector_wealth_db")))
STATE_PATH = DB_PATH / "live_ingest_state.json"

COLLECTION_NAME = "market_news"
EMBEDDING_MODELS = ("text-embedding-004", "gemini-embedding-001")

# India-focused news domains for NewsAPI
INDIA_NEWS_DOMAINS: list[str] = [
    "economictimes.indiatimes.com",
    "moneycontrol.com",
    "livemint.com",
    "business-standard.com",
    "thehindubusinessline.com",
    "financialexpress.com",
    "ndtvprofit.com",
    "zeebiz.com",
    "cnbctv18.com",
    "businesstoday.in",
]

# RSS feeds for Indian financial news (free, unlimited)
INDIA_RSS_FEEDS: list[tuple[str, str]] = [
    ("ET Markets", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    ("ET Stocks", "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms"),
    ("Moneycontrol News", "https://www.moneycontrol.com/rss/marketreports.xml"),
    ("Moneycontrol Stocks", "https://www.moneycontrol.com/rss/results.xml"),
    ("Business Standard Markets", "https://www.business-standard.com/rss/markets-106.rss"),
    ("Livemint Markets", "https://www.livemint.com/rss/markets"),
    ("Hindu BL Markets", "https://www.thehindubusinessline.com/markets/feeder/default.rss"),
    ("NDTV Profit", "https://feeds.feedburner.com/ndtvprofit-latest"),
]


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_iso_datetime(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except ValueError:
        return None


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _build_article_id(url: str, title: str, published_at: str) -> str:
    unique_source = url or f"{title}|{published_at}"
    digest = hashlib.sha256(unique_source.encode("utf-8", errors="ignore")).hexdigest()
    return f"live_news_{digest[:32]}"


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (value or "").lower()).strip()


def _contains_alias(haystack: str, alias: str) -> bool:
    normalized_alias = _normalize_text(alias)
    if not normalized_alias:
        return False
    if " " in normalized_alias:
        return normalized_alias in haystack
    return re.search(rf"\b{re.escape(normalized_alias)}\b", haystack) is not None


def _detect_ticker_tags(title: str, description: str) -> list[str]:
    haystack = _normalize_text(f"{title} {description}")
    if not haystack:
        return []

    detected: list[str] = []
    for symbol, aliases in STOCK_ALIASES.items():
        if _contains_alias(haystack, symbol.lower()):
            detected.append(symbol)
            continue

        for alias in aliases:
            if _contains_alias(haystack, alias):
                detected.append(symbol)
                break

    return sorted(set(detected))


def _build_document_text(title: str, description: str, ticker_tags: list[str]) -> str:
    if ticker_tags:
        tags = ", ".join(ticker_tags)
        return f"Title: {title}\nDescription: {description}\nTickerTags: {tags}"
    return f"Title: {title}\nDescription: {description}"


def _extract_title_description(metadata: dict[str, Any], document: str) -> tuple[str, str]:
    title = _safe_str(metadata.get("Title"))
    description = _safe_str(metadata.get("Description"))

    if title and description:
        return title, description

    text = str(document or "")
    if not text:
        return title, description

    if not title:
        title_match = re.search(r"^Title:\s*(.*)$", text, flags=re.IGNORECASE | re.MULTILINE)
        if title_match:
            title = _safe_str(title_match.group(1))

    if not description:
        description_match = re.search(
            r"^Description:\s*(.*)$",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        if description_match:
            description = _safe_str(description_match.group(1))

    return title, description


@dataclass
class IngestSummary:
    provider: str
    fetched: int
    candidate: int
    inserted: int
    skipped_existing: int
    failed: bool
    message: str
    run_started_at: str
    run_finished_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "fetched": self.fetched,
            "candidate": self.candidate,
            "inserted": self.inserted,
            "skipped_existing": self.skipped_existing,
            "failed": self.failed,
            "message": self.message,
            "run_started_at": self.run_started_at,
            "run_finished_at": self.run_finished_at,
        }


class LiveNewsIngestor:
    def __init__(self) -> None:
        load_dotenv(ENV_PATH)

        self.enabled = _to_bool(os.getenv("LIVE_NEWS_ENABLED"), default=False)
        provider_raw = _safe_str(os.getenv("LIVE_NEWS_PROVIDER") or "newsapi,rss")
        self.providers = [part.strip().lower() for part in provider_raw.split(",") if part.strip()]
        if not self.providers:
            self.providers = ["newsapi", "rss"]
        self.provider = self.providers[0]
        self.newsapi_key = _safe_str(os.getenv("NEWSAPI_KEY"))
        self.finnhub_key = _safe_str(os.getenv("FINNHUB_API_KEY"))
        self.finnhub_category = _safe_str(os.getenv("FINNHUB_NEWS_CATEGORY") or "general")
        self.news_query = _safe_str(
            os.getenv(
                "NEWS_QUERY",
                "Indian stock market OR NSE OR BSE OR Sensex OR Nifty OR earnings",
            )
        )
        self.interval_minutes = max(5, int(os.getenv("LIVE_NEWS_INTERVAL_MINUTES", "30")))
        self.lookback_hours = max(1, int(os.getenv("LIVE_NEWS_LOOKBACK_HOURS", "24")))
        self.page_size = max(10, min(100, int(os.getenv("LIVE_NEWS_PAGE_SIZE", "50"))))
        self.max_articles_per_run = max(10, int(os.getenv("LIVE_NEWS_MAX_ARTICLES_PER_RUN", "100")))
        
        # Sector rotation settings
        self.use_sector_rotation = _to_bool(os.getenv("USE_SECTOR_ROTATION"), default=True)
        self.use_india_domains = _to_bool(os.getenv("USE_INDIA_DOMAINS"), default=True)
        self.rss_enabled = _to_bool(os.getenv("RSS_ENABLED"), default=True)

        self._lock = threading.Lock()
        self._state = self._load_state()

        from agents import chroma_client, news_collection
        self._chroma_client = chroma_client
        self._collection = news_collection

    def _load_state(self) -> dict[str, Any]:
        if not STATE_PATH.exists():
            return {
                "last_successful_ingest_at": None,
                "last_status": "never_run",
                "last_summary": None,
                "sector_index": 0,
            }

        try:
            raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                return {
                    "last_successful_ingest_at": raw.get("last_successful_ingest_at"),
                    "last_status": raw.get("last_status", "unknown"),
                    "last_summary": raw.get("last_summary"),
                    "sector_index": raw.get("sector_index", 0),
                }
        except Exception:
            pass

        return {
            "last_successful_ingest_at": None,
            "last_status": "state_read_error",
            "last_summary": None,
            "sector_index": 0,
        }

    def _save_state(self) -> None:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(self._state, ensure_ascii=False, indent=2), encoding="utf-8")

    def _get_genai_client(self) -> genai.Client:
        api_key = _safe_str(os.getenv("GOOGLE_API_KEY"))
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY is missing in root .env.")
        return genai.Client(api_key=api_key)

    def _embed_texts(self, genai_client: genai.Client, texts: list[str]):
        last_error: Exception | None = None
        for model_name in EMBEDDING_MODELS:
            try:
                return genai_client.models.embed_content(model=model_name, contents=texts)
            except Exception as exc:
                last_error = exc
                continue
        if last_error:
            raise RuntimeError(f"Embedding failed for all configured models: {last_error}") from last_error
        raise RuntimeError("Embedding failed: no models configured.")

    def _resolve_from_dt(self) -> datetime:
        now_utc = datetime.now(UTC)
        default_since = now_utc - timedelta(hours=self.lookback_hours)
        state_since = _parse_iso_datetime(_safe_str(self._state.get("last_successful_ingest_at", "")))
        from_dt = state_since or default_since
        if from_dt > now_utc:
            return default_since
        return from_dt

    def _get_current_sector_query(self) -> str:
        """Get the current sector query based on rotation state."""
        if not self.use_sector_rotation or not SECTOR_QUERIES:
            return self.news_query
        
        sector_index = self._state.get("sector_index", 0) % len(SECTOR_QUERIES)
        return SECTOR_QUERIES[sector_index]
    
    def _advance_sector_index(self) -> None:
        """Advance to the next sector for the next ingestion cycle."""
        if self.use_sector_rotation and SECTOR_QUERIES:
            current_index = self._state.get("sector_index", 0)
            self._state["sector_index"] = (current_index + 1) % len(SECTOR_QUERIES)

    def _fetch_newsapi_articles(self) -> list[dict[str, str]]:
        if not self.newsapi_key:
            raise RuntimeError("NEWSAPI_KEY is not configured.")

        from_dt = self._resolve_from_dt()
        
        # Use sector rotation query instead of generic query
        query = self._get_current_sector_query()
        
        # Build request params
        params: dict[str, Any] = {
            "q": query,
            "from": from_dt.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": self.page_size,
        }
        
        # Add India-focused domains for better relevance
        if self.use_india_domains and INDIA_NEWS_DOMAINS:
            params["domains"] = ",".join(INDIA_NEWS_DOMAINS[:10])  # NewsAPI limits domains

        response = requests.get(
            "https://newsapi.org/v2/everything",
            headers={"X-Api-Key": self.newsapi_key},
            params=params,
            timeout=30,
        )

        if response.status_code >= 400:
            body_preview = response.text[:400]
            raise RuntimeError(f"NewsAPI request failed: {response.status_code} {body_preview}")

        payload = response.json()
        if payload.get("status") != "ok":
            raise RuntimeError(f"NewsAPI returned non-ok status: {payload}")

        raw_articles = payload.get("articles", [])
        parsed: list[dict[str, str]] = []
        for item in raw_articles[: self.max_articles_per_run]:
            title = _safe_str(item.get("title"))
            description = _safe_str(item.get("description"))
            content = _safe_str(item.get("content"))
            published_at = _safe_str(item.get("publishedAt"))
            url = _safe_str(item.get("url"))
            source_name = _safe_str((item.get("source") or {}).get("name"))

            if not title:
                continue

            merged_description = description or content
            if len(merged_description) < 20:
                continue

            parsed.append(
                {
                    "title": title,
                    "description": merged_description,
                    "published_at": published_at,
                    "url": url,
                    "source": source_name,
                }
            )
        
        # Advance sector index for next cycle
        self._advance_sector_index()

        return parsed

    def _fetch_finnhub_articles(self) -> list[dict[str, str]]:
        if not self.finnhub_key:
            raise RuntimeError("FINNHUB_API_KEY is not configured.")

        from_dt = self._resolve_from_dt()

        response = requests.get(
            "https://finnhub.io/api/v1/news",
            params={
                "category": self.finnhub_category,
                "token": self.finnhub_key,
            },
            timeout=30,
        )

        if response.status_code >= 400:
            body_preview = response.text[:400]
            raise RuntimeError(f"Finnhub request failed: {response.status_code} {body_preview}")

        payload = response.json()
        if not isinstance(payload, list):
            raise RuntimeError(f"Finnhub returned unexpected payload: {payload}")

        parsed: list[dict[str, str]] = []
        for item in payload[: self.max_articles_per_run]:
            title = _safe_str(item.get("headline"))
            description = _safe_str(item.get("summary"))
            url = _safe_str(item.get("url"))
            source_name = _safe_str(item.get("source"))

            raw_dt = item.get("datetime")
            published_at = ""
            if isinstance(raw_dt, (int, float)):
                published_at = datetime.fromtimestamp(float(raw_dt), tz=UTC).isoformat().replace(
                    "+00:00", "Z"
                )

            parsed_dt = _parse_iso_datetime(published_at)
            if parsed_dt is not None and parsed_dt < from_dt:
                continue

            if not title:
                continue

            if len(description) < 20:
                continue

            parsed.append(
                {
                    "title": title,
                    "description": description,
                    "published_at": published_at,
                    "url": url,
                    "source": source_name,
                    "provider": "finnhub",
                }
            )

        return parsed

    def _fetch_rss_articles(self) -> list[dict[str, str]]:
        """Fetch articles from Indian financial news RSS feeds."""
        if not self.rss_enabled or not INDIA_RSS_FEEDS:
            return []
        
        from_dt = self._resolve_from_dt()
        parsed: list[dict[str, str]] = []
        
        for source_name, feed_url in INDIA_RSS_FEEDS:
            try:
                response = requests.get(feed_url, timeout=15, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; VectorWealth/1.0)"
                })
                if response.status_code >= 400:
                    continue
                
                # Simple RSS parsing without external dependency
                content = response.text
                
                # Extract items using regex (works for most RSS feeds)
                items = re.findall(
                    r"<item[^>]*>(.*?)</item>",
                    content,
                    flags=re.DOTALL | re.IGNORECASE,
                )
                
                for item_xml in items[:20]:  # Limit per feed
                    # Extract title
                    title_match = re.search(
                        r"<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>",
                        item_xml,
                        flags=re.DOTALL | re.IGNORECASE,
                    )
                    title = _safe_str(title_match.group(1)) if title_match else ""
                    
                    # Extract description
                    desc_match = re.search(
                        r"<description[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>",
                        item_xml,
                        flags=re.DOTALL | re.IGNORECASE,
                    )
                    description = _safe_str(desc_match.group(1)) if desc_match else ""
                    # Strip HTML tags from description
                    description = re.sub(r"<[^>]+>", " ", description).strip()
                    description = re.sub(r"\s+", " ", description)
                    
                    # Extract link
                    link_match = re.search(
                        r"<link[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>",
                        item_xml,
                        flags=re.DOTALL | re.IGNORECASE,
                    )
                    url = _safe_str(link_match.group(1)) if link_match else ""
                    
                    # Extract pubDate
                    pubdate_match = re.search(
                        r"<pubDate[^>]*>(.*?)</pubDate>",
                        item_xml,
                        flags=re.DOTALL | re.IGNORECASE,
                    )
                    pub_date_str = _safe_str(pubdate_match.group(1)) if pubdate_match else ""
                    
                    # Parse pubDate (RFC 822 format typically)
                    published_at = ""
                    if pub_date_str:
                        try:
                            # Try parsing RFC 822 format
                            from email.utils import parsedate_to_datetime
                            parsed_dt = parsedate_to_datetime(pub_date_str)
                            if parsed_dt.tzinfo is None:
                                parsed_dt = parsed_dt.replace(tzinfo=UTC)
                            published_at = parsed_dt.isoformat()
                            
                            # Skip if older than lookback period
                            if parsed_dt < from_dt:
                                continue
                        except Exception:
                            pass
                    
                    if not title or len(title) < 10:
                        continue
                    
                    if not description:
                        description = title
                    
                    if len(description) < 20:
                        continue
                    
                    parsed.append({
                        "title": title,
                        "description": description,
                        "published_at": published_at,
                        "url": url,
                        "source": source_name,
                        "provider": "rss",
                    })
                    
                    if len(parsed) >= self.max_articles_per_run:
                        break
                        
            except Exception:
                # Skip failed feeds silently, try others
                continue
            
            if len(parsed) >= self.max_articles_per_run:
                break
        
        return parsed[:self.max_articles_per_run]

    def _fetch_articles(self) -> tuple[str, list[dict[str, str]]]:
        """
        Fetch articles from all configured providers.
        RSS is always fetched and combined with the primary provider (NewsAPI/Finnhub).
        """
        errors: list[str] = []
        all_articles: list[dict[str, str]] = []
        primary_provider = ""
        
        # First, always try to fetch RSS articles (free, supplementary)
        if "rss" in self.providers:
            try:
                rss_articles = self._fetch_rss_articles()
                for article in rss_articles:
                    article["provider"] = "rss"
                all_articles.extend(rss_articles)
            except Exception as exc:
                errors.append(f"rss: {exc}")
        
        # Then try primary providers (NewsAPI/Finnhub)
        primary_providers = [p for p in self.providers if p != "rss"]
        
        for provider_name in primary_providers:
            try:
                if provider_name == "newsapi":
                    articles = self._fetch_newsapi_articles()
                elif provider_name == "finnhub":
                    articles = self._fetch_finnhub_articles()
                else:
                    raise RuntimeError(
                        f"Unsupported provider '{provider_name}'. Supported providers: newsapi, finnhub, rss"
                    )

                normalized = [
                    {
                        **article,
                        "provider": _safe_str(article.get("provider") or provider_name),
                    }
                    for article in articles
                ]
                all_articles.extend(normalized)
                primary_provider = provider_name
                break  # Use first successful primary provider
                    
            except Exception as exc:
                errors.append(f"{provider_name}: {exc}")
        
        if all_articles:
            return primary_provider or "rss", all_articles

        raise RuntimeError("All live news providers failed. " + " | ".join(errors))

    def _get_existing_ids(self, ids: list[str]) -> set[str]:
        if not ids:
            return set()

        # Deduplicate IDs before querying ChromaDB (it throws error on duplicate IDs)
        unique_ids = list(set(ids))
        
        existing: set[str] = set()
        batch_size = 100
        for start in range(0, len(unique_ids), batch_size):
            batch_ids = unique_ids[start : start + batch_size]
            try:
                response = self._collection.get(ids=batch_ids, include=[])
                for found_id in response.get("ids", []) or []:
                    if found_id:
                        existing.add(str(found_id))
            except Exception:
                # If batch fails, check IDs one by one
                for single_id in batch_ids:
                    try:
                        response = self._collection.get(ids=[single_id], include=[])
                        if response.get("ids"):
                            existing.add(single_id)
                    except Exception:
                        pass
        return existing

    def _build_metadata(self, article: dict[str, Any]) -> dict[str, Any]:
        published_at = _safe_str(article.get("published_at"))
        date_for_ui = published_at.split("T", 1)[0] if "T" in published_at else published_at
        ticker_tags = article.get("ticker_tags", [])
        if isinstance(ticker_tags, list):
            ticker_tags_csv = ",".join([_safe_str(item).upper() for item in ticker_tags if _safe_str(item)])
        else:
            ticker_tags_csv = ""

        primary_ticker = ticker_tags_csv.split(",", 1)[0] if ticker_tags_csv else ""

        return {
            "Date": date_for_ui,
            "Title": _safe_str(article.get("title")),
            "Description": _safe_str(article.get("description")),
            "published_at": published_at,
            "source": _safe_str(article.get("source")),
            "url": _safe_str(article.get("url")),
            "ingested_at": _utcnow_iso(),
            "provider": _safe_str(article.get("provider") or self.provider),
            "ticker_tags": ticker_tags_csv,
            "primary_ticker": primary_ticker,
        }

    def ingest_once(self) -> IngestSummary:
        run_started_at = _utcnow_iso()
        with self._lock:
            if not self.enabled:
                summary = IngestSummary(
                    provider=self.provider,
                    fetched=0,
                    candidate=0,
                    inserted=0,
                    skipped_existing=0,
                    failed=True,
                    message="LIVE_NEWS_ENABLED is false.",
                    run_started_at=run_started_at,
                    run_finished_at=_utcnow_iso(),
                )
                self._state["last_status"] = "disabled"
                self._state["last_summary"] = summary.to_dict()
                self._save_state()
                return summary

            fetched_articles: list[dict[str, str]] = []
            active_provider = self.provider
            try:
                active_provider, fetched_articles = self._fetch_articles()

                article_ids = [
                    _build_article_id(
                        url=_safe_str(item.get("url")),
                        title=_safe_str(item.get("title")),
                        published_at=_safe_str(item.get("published_at")),
                    )
                    for item in fetched_articles
                ]

                existing_ids = self._get_existing_ids(article_ids)

                candidate_payloads = []
                skipped_existing = 0
                seen_ids_in_batch: set[str] = set()  # Track duplicates within this batch
                for idx, article in enumerate(fetched_articles):
                    article_id = article_ids[idx]
                    # Skip if already in DB
                    if article_id in existing_ids:
                        skipped_existing += 1
                        continue
                    # Skip if duplicate within this batch
                    if article_id in seen_ids_in_batch:
                        skipped_existing += 1
                        continue
                    seen_ids_in_batch.add(article_id)
                    candidate_payloads.append((article_id, article))

                if not candidate_payloads:
                    summary = IngestSummary(
                        provider=active_provider,
                        fetched=len(fetched_articles),
                        candidate=0,
                        inserted=0,
                        skipped_existing=skipped_existing,
                        failed=False,
                        message="No new articles to ingest.",
                        run_started_at=run_started_at,
                        run_finished_at=_utcnow_iso(),
                    )
                    self._state["last_status"] = "ok"
                    self._state["last_successful_ingest_at"] = _utcnow_iso()
                    self._state["last_summary"] = summary.to_dict()
                    self._save_state()
                    return summary

                genai_client = self._get_genai_client()

                ids: list[str] = []
                documents: list[str] = []
                metadatas: list[dict[str, Any]] = []

                for article_id, article in candidate_payloads:
                    title = _safe_str(article.get("title"))
                    description = _safe_str(article.get("description"))
                    ticker_tags = _detect_ticker_tags(title=title, description=description)
                    article["ticker_tags"] = ticker_tags
                    ids.append(article_id)
                    documents.append(
                        _build_document_text(
                            title=title,
                            description=description,
                            ticker_tags=ticker_tags,
                        )
                    )
                    metadatas.append(self._build_metadata(article))

                embedding_response = self._embed_texts(genai_client, documents)
                embeddings = [item.values if hasattr(item, "values") else item for item in embedding_response.embeddings]

                self._collection.add(
                    ids=ids,
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas,
                )

                summary = IngestSummary(
                    provider=active_provider,
                    fetched=len(fetched_articles),
                    candidate=len(candidate_payloads),
                    inserted=len(ids),
                    skipped_existing=skipped_existing,
                    failed=False,
                    message="Live news ingestion completed.",
                    run_started_at=run_started_at,
                    run_finished_at=_utcnow_iso(),
                )
                self._state["last_status"] = "ok"
                self._state["last_successful_ingest_at"] = _utcnow_iso()
                self._state["last_summary"] = summary.to_dict()
                self._save_state()
                return summary

            except Exception as exc:
                summary = IngestSummary(
                    provider=active_provider,
                    fetched=len(fetched_articles),
                    candidate=0,
                    inserted=0,
                    skipped_existing=0,
                    failed=True,
                    message=str(exc),
                    run_started_at=run_started_at,
                    run_finished_at=_utcnow_iso(),
                )
                self._state["last_status"] = "error"
                self._state["last_summary"] = summary.to_dict()
                self._save_state()
                return summary

    def get_status(self) -> dict[str, Any]:
        sector_index = self._state.get("sector_index", 0)
        current_sector_query = ""
        total_sectors = len(SECTOR_QUERIES)
        if self.use_sector_rotation and total_sectors > 0:
            current_sector_query = SECTOR_QUERIES[sector_index % total_sectors]
        
        return {
            "enabled": self.enabled,
            "provider": self.provider,
            "providers": self.providers,
            "interval_minutes": self.interval_minutes,
            "lookback_hours": self.lookback_hours,
            "page_size": self.page_size,
            "max_articles_per_run": self.max_articles_per_run,
            "last_successful_ingest_at": self._state.get("last_successful_ingest_at"),
            "last_status": self._state.get("last_status"),
            "last_summary": self._state.get("last_summary"),
            # Sector rotation info
            "sector_rotation_enabled": self.use_sector_rotation,
            "sector_index": sector_index,
            "total_sectors": total_sectors,
            "current_sector_query": current_sector_query,
            # India-focused settings
            "india_domains_enabled": self.use_india_domains,
            "rss_enabled": self.rss_enabled,
            "rss_feeds_count": len(INDIA_RSS_FEEDS),
        }

    def retag_existing_records(self, batch_size: int = 200) -> dict[str, Any]:
        run_started_at = _utcnow_iso()
        processed = 0
        updated = 0
        tagged = 0
        untagged = 0

        with self._lock:
            try:
                total_records = int(self._collection.count())
                offset = 0

                while offset < total_records:
                    response = self._collection.get(
                        limit=batch_size,
                        offset=offset,
                        include=["documents", "metadatas"],
                    )

                    ids = response.get("ids", []) or []
                    documents = response.get("documents", []) or []
                    metadatas = response.get("metadatas", []) or []

                    if not ids:
                        break

                    update_ids: list[str] = []
                    update_metadatas: list[dict[str, Any]] = []

                    for idx, doc_id in enumerate(ids):
                        metadata_raw = metadatas[idx] if idx < len(metadatas) else {}
                        metadata = dict(metadata_raw) if isinstance(metadata_raw, dict) else {}
                        document = str(documents[idx]) if idx < len(documents) else ""

                        title, description = _extract_title_description(metadata, document)
                        ticker_tags = _detect_ticker_tags(title=title, description=description)

                        if ticker_tags:
                            tagged += 1
                        else:
                            untagged += 1

                        ticker_tags_csv = ",".join(ticker_tags)
                        primary_ticker = ticker_tags[0] if ticker_tags else ""

                        current_tags = _safe_str(metadata.get("ticker_tags"))
                        current_primary = _safe_str(metadata.get("primary_ticker"))

                        if ticker_tags_csv != current_tags or primary_ticker != current_primary:
                            metadata["ticker_tags"] = ticker_tags_csv
                            metadata["primary_ticker"] = primary_ticker
                            update_ids.append(str(doc_id))
                            update_metadatas.append(metadata)

                    if update_ids:
                        self._collection.update(ids=update_ids, metadatas=update_metadatas)
                        updated += len(update_ids)

                    processed += len(ids)
                    offset += len(ids)

                return {
                    "failed": False,
                    "message": "Retag completed.",
                    "processed": processed,
                    "updated": updated,
                    "tagged": tagged,
                    "untagged": untagged,
                    "run_started_at": run_started_at,
                    "run_finished_at": _utcnow_iso(),
                }
            except Exception as exc:
                return {
                    "failed": True,
                    "message": str(exc),
                    "processed": processed,
                    "updated": updated,
                    "tagged": tagged,
                    "untagged": untagged,
                    "run_started_at": run_started_at,
                    "run_finished_at": _utcnow_iso(),
                }
