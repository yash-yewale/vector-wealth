import sys
import traceback
from datetime import UTC, datetime, timedelta
from agents import news_collection

try:
    print("1. DB load...")
    sys.stdout.flush()
    total_docs = news_collection.count()
    print(f"2. DB count: {total_docs}")
    sys.stdout.flush()

    batch_size = 500
    all_docs = {}
    offset = 0

    print("3. Starting while loop...")
    sys.stdout.flush()
    while offset < total_docs:
        print(f"4. Fetching batch offset {offset}...")
        sys.stdout.flush()
        result = news_collection.get(
            limit=batch_size,
            offset=offset,
            include=["documents", "metadatas"],
        )
        print("5. Fetched!")
        sys.stdout.flush()

        ids = result.get("ids", []) or []
        if not ids:
            print("6. No ids, breaking")
            break
        print(f"7. Batch has {len(ids)} ids")
        offset += len(ids)

    print("8. Loop finished!")

except Exception as e:
    print("Exception", e)
    traceback.print_exc()
