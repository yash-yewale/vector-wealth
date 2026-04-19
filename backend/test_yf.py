import yfinance as yf
import traceback
import json

try:
    ticker = yf.Ticker("JINDALSTEL.NS")
    info = ticker.info
    print("KEYS:", list(info.keys())[:20] if info else "Empty dict")
    
    current_price = info.get("currentPrice")
    regular_price = info.get("regularMarketPrice")
    print(f"currentPrice: {current_price}")
    print(f"regularMarketPrice: {regular_price}")
    
except Exception as e:
    print("FAILED")
    traceback.print_exc()
