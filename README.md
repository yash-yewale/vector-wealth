# Vector Wealth

AI-powered multi-agent investment research system for the Indian market.

## Stack

- Backend: Python 3.13, LangGraph, ChromaDB, Gemini 2.5 Flash
- Frontend: Flutter
- Data: Historical Indian financial news CSV + embeddings

## Guardrails implemented

- Uses 2026 SDK style: `from google import genai` and `genai.Client()`.
- Loads root `.env` via: `Path(__file__).resolve().parent.parent / '.env'`.
- Uses local ChromaDB `PersistentClient` at `backend/vector_wealth_db`.
- Backend now defaults to a fast local analysis fallback (no external API dependency) for reliable UI responses.
- To force Gemini-powered analysis, set `USE_GENAI_ANALYSIS=true` in root `.env`.
- Optional live news ingestion can continuously add fresh market articles to ChromaDB.

## Backend setup

1. Create environment and install dependencies:
   - `cd backend`
   - `python -m venv .venv`
   - `.venv\\Scripts\\activate`
   - `pip install -r requirements.txt`
2. Create root `.env` from `.env.example` and set `GOOGLE_API_KEY`.
3. Place dataset at `data/IndianFinancialNews.csv` with columns:
   - `Date`, `Title`, `Description`

### Ingest data

- `python ingest_data.py`

### Run API

- `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
- Optional for deployed frontend: set `ALLOWED_ORIGINS` in root `.env` (comma-separated), for example:
  - `ALLOWED_ORIGINS=https://your-frontend-domain.com`

### Live news auto-ingestion (optional)

Set in root `.env`:

- `LIVE_NEWS_ENABLED=true`
- `LIVE_NEWS_PROVIDER=newsapi,finnhub`
- `NEWSAPI_KEY=...`
- `FINNHUB_API_KEY=...`
- `FINNHUB_NEWS_CATEGORY=general`
- `NEWS_QUERY=Indian stock market OR NSE OR BSE OR Sensex OR Nifty OR earnings`
- `LIVE_NEWS_INTERVAL_MINUTES=30`
- `LIVE_NEWS_LOOKBACK_HOURS=24`
- `LIVE_NEWS_PAGE_SIZE=50`
- `LIVE_NEWS_MAX_ARTICLES_PER_RUN=100`

When enabled, backend starts a scheduler on startup and ingests fresh articles into `market_news` collection.
`LIVE_NEWS_PROVIDER` accepts a comma-separated fallback order (for example `newsapi,finnhub`).

Manual controls:

- `GET /admin/live-news/status`
- `POST /admin/live-news/refresh`
- `POST /admin/live-news/retag-existing` (one-time historical ticker tag backfill)

## API contract

- POST `/analyze`
- Request JSON:
  - `{"ticker": "HDFCBANK"}`
- Response JSON includes:
  - `sentiment`
  - `now_sentiment`
  - `pattern_sentiment`
  - `confidence`
  - `recent_news_count`
  - `pattern_news_count`
  - `latest_news_date`
  - `stale_data`
  - `stale_reason`
  - `explanation`
  - `positive_drivers`
  - `negative_drivers`
  - `news_references`
  - `recommendation`

## Production notes

- Ingestion runs only while backend is running.
- To keep data updating continuously, deploy backend to an always-on host.
- Structured request telemetry is printed as JSON logs for each `/analyze` call.

## Regression smoke test

From `backend` folder:

- `C:/Users/ASUS/vector_wealth/.venv/Scripts/python.exe scripts/regression_smoke.py`

This validates response schema for known tickers and checks random-input guardrails.

## Flutter setup

1. `cd frontend`
2. `flutter pub get`
3. `flutter run`

For non-localhost environments, pass backend URL explicitly:

- `flutter run --dart-define=API_BASE_URL=https://your-backend-domain.com`

Ensure backend API is running on `http://127.0.0.1:8000`.
