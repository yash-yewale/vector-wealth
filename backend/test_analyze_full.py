import urllib.request
import json
import traceback

try:
    req = urllib.request.Request(
        'http://127.0.0.1:8000/analyze',
        data=json.dumps({"ticker": "JINDALSTEL"}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as response:
        payload = response.read().decode('utf-8')
        result = json.loads(payload)
        print("FULL JSON KEYS:", list(result.keys()))
        print(f"current_price: {result.get('current_price')}")
        print(f"price_change: {result.get('price_change')}")
        print(f"price_change_percent: {result.get('price_change_percent')}")
except Exception as e:
    print("FAILED")
    traceback.print_exc()
