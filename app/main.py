import os
import socket

import psycopg
import redis
from fastapi import FastAPI, HTTPException
from psycopg import OperationalError
from redis.exceptions import ConnectionError as RedisConnectionError

DATABASE_URL = os.environ["DATABASE_URL"]
REDIS_URL = os.environ["REDIS_URL"]

app = FastAPI()
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Gauge

Instrumentator().instrument(app).expose(app)

def _queue_length():
    try:
        return r.llen("jobs")
    except Exception:
        return -1

jobs_queue = Gauge("jobs_queue_length", "Jobs waiting in the Redis queue")
jobs_queue.set_function(_queue_length)
r = redis.from_url(REDIS_URL , decode_responses = True)


def db():
    return psycopg.connect(DATABASE_URL)



with db() as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS items (id SERIAL PRIMARY KEY, name TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS results (id SERIAL PRIMARY KEY, job TEXT, done_at TIMESTAMP DEFAULT now())")


@app.post("/items")
def add_itedm(name : str):
    with db() as conn:
        conn.execute("INSERT INTO items (name) VALUES (%s)", (name,))
    return {"addedd" : name}


@app.get("/items")
def get_items():
    hits = r.incr("hits")
    with db() as conn:
        rows = conn.execute("SELECT id , name FROM items").fetchall()
    return {"hits" : hits , "items" : rows}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/jobs")
def add_job(name: str):
    r.lpush("jobs", name)
    return {"queued": name}


@app.get("/results")
def get_results():
    with db() as conn:
        rows = conn.execute("SELECT id, job, done_at FROM results ORDER BY id").fetchall()
    return {"results": rows}