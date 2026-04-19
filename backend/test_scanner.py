import time
import sys
import traceback

if __name__ == "__main__":
    t = time.time()
    print("1. Initializing OpportunityScanner...")
    sys.stdout.flush()
    try:
        from opportunity_scanner import opportunity_scanner
        print(f"2. Init took {time.time() - t:.2f}s")
        sys.stdout.flush()
        
        t = time.time()
        print("3. Starting scan...")
        sys.stdout.flush()
        res = opportunity_scanner.scan("market_hours")
        print(f"4. Scan finished in {time.time() - t:.2f}s")
        print(f"Found {res.candidates_found} candidates, {len(res.opportunities)} opportunities")
        sys.stdout.flush()

    except Exception as e:
        print("Exception caught:", e)
        traceback.print_exc()
        sys.exit(1)
