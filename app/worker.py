import os
import time

import psycopg
import redis

DATABASE_URL = os.environ["DATABASE_URL"]
REDIS_URL = os.environ["REDIS_URL"]

r = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=None)
with psycopg.connect(DATABASE_URL) as conn:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS results ("
        "id SERIAL PRIMARY KEY, job TEXT, done_at TIMESTAMP DEFAULT now())"
    )

print("worker started, waiting for jobs", flush=True)

while True:
    item = r.brpop("jobs", timeout=5)  # returns None if nothing arrived in 5s
    if item is None:
        continue
    _, job = item
    print(f"processing: {job}", flush=True)
    time.sleep(2)  # pretend to do slow work
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("INSERT INTO results (job) VALUES (%s)", (job,))
    print(f"done: {job}", flush=True)