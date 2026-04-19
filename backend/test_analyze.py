import urllib.request
import json

req = urllib.request.Request(
    'http://127.0.0.1:8000/analyze',
    data=json.dumps({"ticker": "JINDALSTEL"}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req) as response:
    result = json.loads(response.read().decode('utf-8'))
    print(f"Price: {result.get('current_price')}")
    print(f"Change: {result.get('price_change')}")
    print(f"Decision: {result.get('final_decision')}")
