# DevOps Task: FastAPI + Postgres + Redis

A small FastAPI service that stores items in **Postgres** and counts requests in **Redis**, containerized with Docker and run with Docker Compose.

## Run

```bash
cp .env.example .env
docker compose up -d --build
```

The `.env` file holds the database credentials. `.env.example` contains placeholder values and can be used as is.

Check that it works:

```bash
curl localhost:8000/health
curl -X POST "localhost:8000/items?name=test"
curl localhost:8000/items
```

Interactive API docs: http://localhost:8000/docs

Stop the system:

```bash
docker compose down        # stops containers, keeps data
docker compose down -v     # stops containers and deletes data
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Checks Postgres and Redis. Returns 200, or 503 with the failing dependency |
| POST | `/items?name=...` | Stores an item in Postgres |
| GET | `/items` | Lists items and increments a request counter in Redis |

## Project structure

```
.
├── app/
│   ├── __init__.py
│   └── main.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .dockerignore
└── .gitignore
```

## Shortcuts
`make up`, `make down`, `make logs`, `make ps`, `make clean`

## Technical decisions

- **`python:3.12-slim` base image:** much smaller than a full OS image. Final image size: 59.4 MB.
- **`requirements.txt` copied before the app code:** the dependency layer is cached, so code changes rebuild quickly.
- **Healthchecks and `depends_on: condition: service_healthy`:** the API starts only after Postgres and Redis are ready, regardless of the order in which they come up.
- **Named volume `pgdata`:** Postgres data survives `down` and `up`. Redis has no volume because it only holds a disposable counter.
- **Secrets in `.env`:** the file is git-ignored and never committed. `.env.example` has placeholders only.
- **`db` and `redis` publish no ports:** only the API is reachable from the host. The API reaches the others by service name (`db`, `redis`) over the Compose network.
- **`restart: unless-stopped`:** services come back after a crash.

## A problem I faced

After the first `docker compose up`, `/health` returned a generic 503 (`dependency down`) even though all containers were running. The message did not say which dependency had failed, so I changed `/health` to report Postgres and Redis separately. It showed `unexpected keyword argument 'decode_response'` for Redis, which was a typo in my code (`decode_response` instead of `decode_responses`).

I fixed the typo and rebuilt the image with `docker compose up -d --build`, because the code is copied into the image at build time and a plain restart would not pick up the change.
