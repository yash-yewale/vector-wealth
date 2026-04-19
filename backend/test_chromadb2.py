import sys
import traceback
from agents import news_collection

try:
    print("1. DB load...")
    sys.stdout.flush()

    try:
        print("Testing get(include=[])...")
        sys.stdout.flush()
        news_collection.get(limit=1, offset=0, include=[])
        print("get(include=[]) success")
        sys.stdout.flush()
    except Exception as e:
        print("get(include=[]) failed:", e)
        sys.stdout.flush()

    try:
        print("Testing get(include=['metadatas'])...")
        sys.stdout.flush()
        news_collection.get(limit=1, offset=0, include=["metadatas"])
        print("get(include=['metadatas']) success")
        sys.stdout.flush()
    except Exception as e:
        print("get(include=['metadatas']) failed:", e)
        sys.stdout.flush()
        
    try:
        print("Testing get(include=['documents'])...")
        sys.stdout.flush()
        news_collection.get(limit=1, offset=0, include=["documents"])
        print("get(include=['documents']) success")
        sys.stdout.flush()
    except Exception as e:
        print("get(include=['documents']) failed:", e)
        sys.stdout.flush()

except Exception as e:
    print("Exception", e)
    traceback.print_exc()
