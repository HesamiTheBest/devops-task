import os

import psycopg
import redis
from fastapi import FastAPI, HTTPException

DATABASE_URL = os.environ["DATABASE_URL"]
REDIS_URL = os.environ["REDIS_URL"]

app = FastAPI()
r = redis.from_url(REDIS_URL , decode_response = True)


def db():
    return psycopg.connect(DATABASE_URL)



with db() as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS items (id SERIAL PRIMARY KEY, name TEXT)")


@app.post("/items")
def add_itedm(name : str):
    with db() as conn:
        conn.execute("INSERT INTO items (name) VALUES (%s)", (name,))
    return {"added" : name}


@app.get("/items")
def get_items():
    hits = r.incr("hits")
    with db() as conn:
        rows = conn.execute("SELECT id , name FROM items").fetchall()
    return {"hits" : hits , "items" : rows}

@app.get("/health")
def health():
    try :
        with db() as conn:
            conn.execute("SELECT 1")
        r.ping()
    except  Exception :
        raise HTTPException(status_code=503 , detail = "dependency down")
    return {"status" : "ok"} 