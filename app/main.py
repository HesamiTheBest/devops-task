import os

import psycopg
import redis
import socket
from fastapi import FastAPI, HTTPException


DATABASE_URL = os.environ["DATABASE_URL"]
REDIS_URL = os.environ["REDIS_URL"]

app = FastAPI()
r = redis.from_url(REDIS_URL , decode_responses = True)


def db():
    return psycopg.connect(DATABASE_URL)



with db() as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS items (id SERIAL PRIMARY KEY, name TEXT)")


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
    status = {}
    try:
        with db() as conn:
            conn.execute("SELECT 1")
        status["postgres"] = "ok"
    except Exception as e:
        status["postgres"] = f"error: {e}"
    try:
        r.ping()
        status["redis"] = "ok"
    except Exception as e:
        status["redis"] = f"error: {e}"
    if all(v == "ok" for v in status.values()):
        return {"status": "ok", "instance": socket.gethostname(), **status}
    raise HTTPException(status_code=503, detail=status)
