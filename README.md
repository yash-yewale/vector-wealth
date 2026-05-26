<p align="center">
  <img src="assets/banner.png" alt="Vector Wealth Banner" width="100%"/>
</p>

<h1 align="center">Vector Wealth</h1>

<p align="center">
  <b>AI-Powered Investment Research for the Indian Stock Market</b><br/>
  <sub>Multi-agent sentiment analysis · Portfolio intelligence · Real-time market insights</sub>
</p>

<p align="center">
  <a href="https://github.com/yash-yewale/vector-wealth/releases/latest">
    <img src="https://img.shields.io/badge/📱_Download_APK-Latest_Release-818CF8?style=for-the-badge&logoColor=white" alt="Download APK"/>
  </a>
  &nbsp;
  <img src="https://img.shields.io/badge/Backend-Render_(Live)-2DD4BF?style=for-the-badge&logo=render&logoColor=white" alt="Backend Status"/>
  &nbsp;
  <img src="https://img.shields.io/badge/Flutter-3.x-02569B?style=for-the-badge&logo=flutter&logoColor=white" alt="Flutter"/>
  &nbsp;
  <img src="https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
</p>

---

## 📱 Try It Now

> **The fastest way to try Vector Wealth is to download the Android APK — no setup required!**

### Step-by-step

1. **Download** the latest APK from [**GitHub Releases**](https://github.com/yash-yewale/vector-wealth/releases/latest)
2. **Install** — open the downloaded `.apk` file on your Android device
   - You may need to enable **"Install from unknown sources"** in your phone's settings
   - Go to `Settings → Security → Install unknown apps → Allow from browser/files`
3. **Open** the app — it connects to the live backend automatically 🚀

> [!NOTE]
> The backend is deployed on Render's free tier. The **first request may take ~30–50 seconds** as the server wakes up from sleep. Subsequent requests will be fast.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **Ticker Analysis** | Enter any NSE/BSE ticker and get AI-powered sentiment analysis with confidence scores |
| 📊 **Sentiment Dashboard** | Visual breakdown of bullish/bearish/neutral sentiment with historical trends |
| 🌐 **Discover** | Browse sector-wise market opportunities with rotation analysis |
| 💼 **Portfolio Builder** | Add stocks, set investment goals, and get AI-powered portfolio analysis |
| 🤖 **AI Chat** | Natural-language research assistant — ask questions about stocks, sectors, market trends |
| 📰 **News Intelligence** | Real-time aggregation from NewsAPI, Finnhub, and RSS feeds with auto-ticker-tagging |
| 🔄 **Live Data** | Continuous news ingestion keeps analysis fresh and up-to-date |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Flutter Mobile App                       │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────┐          │
│  │ Analyze  │ │ Discover │ │ Portfolio │ │ AI Chat  │          │
│  └────┬─────┘ └────┬─────┘ └─────┬─────┘ └────┬─────┘          │
│       └─────────────┴─────────────┴─────────────┘               │
│                          HTTP/REST                               │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   FastAPI Backend  │  ← Deployed on Render
                    │   (Python 3.13)   │
                    └─────────┬─────────┘
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
    ┌──────▼──────┐   ┌──────▼──────┐   ┌───────▼──────┐
    │  Gemini AI  │   │  ChromaDB   │   │ News Ingest  │
    │  2.5 Flash  │   │  Vectors    │   │ (Live/RSS)   │
    └─────────────┘   └─────────────┘   └──────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Flutter 3.x, Provider state management, Material 3, Glassmorphism UI |
| **Backend** | Python 3.13, FastAPI, LangGraph multi-agent orchestration |
| **AI/ML** | Google Gemini 2.5 Flash, ChromaDB vector embeddings |
| **Data** | Historical Indian financial news, live NewsAPI/Finnhub/RSS feeds |
| **Deployment** | Render (backend), GitHub Releases (APK) |

---

## 🛠️ Developer Setup

<details>
<summary><b>Backend</b></summary>

### Prerequisites
- Python 3.13+
- A Google Gemini API key

### Quick Start

```bash
# Clone the repo
git clone https://github.com/yash-yewale/vector-wealth.git
cd vector-wealth

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Mac/Linux

# Install dependencies
cd backend
pip install -r requirements.txt

# Configure environment
cp ../.env.example ../.env
# Edit .env and set GOOGLE_API_KEY=your_key_here

# Ingest dataset (one-time)
python ingest_data.py

# Start the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Place the dataset at `data/IndianFinancialNews.csv` with columns: `Date`, `Title`, `Description`.

</details>

<details>
<summary><b>Frontend (Flutter)</b></summary>

### Prerequisites
- Flutter SDK 3.3+
- Android Studio or VS Code with Flutter extension

### Quick Start

```bash
cd frontend
flutter pub get

# Run on connected device (uses localhost by default)
flutter run

# Build APK pointing to a custom backend
flutter build apk --release --dart-define=API_BASE_URL=https://your-backend.onrender.com
```

The app has a built-in **Settings** page where you can change the backend URL at runtime — no rebuild needed.

</details>

<details>
<summary><b>Live News Ingestion (Optional)</b></summary>

Set these in your root `.env`:

```env
LIVE_NEWS_ENABLED=true
LIVE_NEWS_PROVIDER=newsapi,rss
NEWSAPI_KEY=your_key
NEWS_QUERY=Indian stock market OR NSE OR BSE OR Sensex OR Nifty
LIVE_NEWS_INTERVAL_MINUTES=30
```

Admin endpoints:
- `GET /admin/live-news/status` — check ingestion status
- `POST /admin/live-news/refresh` — trigger manual refresh
- `POST /admin/live-news/retag-existing` — backfill ticker tags

</details>

---

## 📡 API Reference

### `POST /analyze`

Analyze sentiment for a stock ticker.

**Request:**
```json
{ "ticker": "HDFCBANK" }
```

**Response includes:**
`sentiment`, `confidence`, `explanation`, `recommendation`, `positive_drivers`, `negative_drivers`, `news_references`, `now_sentiment`, `pattern_sentiment`, `recent_news_count`, `stale_data`, and more.

---

## 🚀 Deployment

### Backend (Render)

The backend is configured via `render.yaml` for one-click deployment:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

### APK Release

To build and publish a new APK:

```bash
cd frontend
flutter build apk --release \
  --dart-define=API_BASE_URL=https://vector-wealth-api.onrender.com
```

Then create a [GitHub Release](https://github.com/yash-yewale/vector-wealth/releases/new) and attach the APK from `frontend/build/app/outputs/flutter-apk/app-release.apk`.

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

---

## 📄 License

This project is for educational and research purposes.

---

<p align="center">
  <sub>Built with ❤️ using Flutter, FastAPI, Gemini AI & LangGraph</sub>
</p>
