import time
import sys
from live_news_ingest import LiveNewsIngestor

if __name__ == "__main__":
    t = time.time()
    print("1. Initializing...")
    sys.stdout.flush()
    try:
        ingestor = LiveNewsIngestor()
        print(f"2. Init took {time.time() - t:.2f}s")
        sys.stdout.flush()
        
        t = time.time()
        print("3. Starting fetch...")
        sys.stdout.flush()
        provider, articles = ingestor._fetch_articles()
        print(f"4. Fetched {len(articles)} in {time.time() - t:.2f}s")
        sys.stdout.flush()
        
        print("5. Embedding texts...")
        sys.stdout.flush()
        client = ingestor._get_genai_client()
        docs = [a["title"] for a in articles[:2]]
        res = ingestor._embed_texts(client, docs)
        print("6. Embedded successfully!")
        sys.stdout.flush()

    except Exception as e:
        import traceback
        print("Exception caught:", e)
        traceback.print_exc()
        sys.exit(1)
