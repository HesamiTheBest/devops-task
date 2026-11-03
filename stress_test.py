#!/usr/bin/env python3
"""Hard stress test for the FastAPI app behind nginx on localhost:8080."""
import concurrent.futures
import requests
import time
import sys

URL = "http://localhost:8000"
ENDPOINTS = [
    ("GET", "/health", None),
    ("GET", "/items", None),
    ("POST", "/items", {"name": "load-item"}),
    ("POST", "/jobs", {"name": "load-job"}),
]

def hit(endpoint):
    method, path, data = endpoint
    try:
        if method == "GET":
            r = requests.get(URL + path, timeout=5)
        else:
            r = requests.post(URL + path, data=data, timeout=5)
        return r.status_code, path
    except Exception as e:
        return str(e), path

def main(duration=120, concurrency=50):
    end = time.time() + duration
    total = 0
    errors = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as ex:
        while time.time() < end:
            batch = [ex.submit(hit, ep) for ep in ENDPOINTS for _ in range(concurrency)]
            for f in concurrent.futures.as_completed(batch):
                status, path = f.result()
                total += 1
                if isinstance(status, str) or status >= 400:
                    errors += 1
            print(f"Sent {total} requests, {errors} errors", end="\r", flush=True)
    print(f"\nDone: {total} requests, {errors} errors in {duration}s with {concurrency} concurrency")

if __name__ == "__main__":
    dur = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    conc = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    main(dur, conc)
