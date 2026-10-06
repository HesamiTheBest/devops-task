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
├── Makefile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .dockerignore
└── .gitignore
```
## Development

`make dev` enables live reloading, bind mounting and a port for the database.

## Shortcuts

`make up`, `make down`, `make logs`, `make ps`, `make clean`, `make dev`, `make size`

`make size` prints a size report: image sizes, the per-layer breakdown of `task-api` (`docker history`), and overall Docker disk usage.

## Technical decisions

- **Multi-stage Dockerfile:** stage 1 (`python:3.12`, named `builder`) installs only the pip dependencies into a separate prefix (`--prefix=/install`); the final image starts fresh from `python:3.12-slim` and pulls in just those packages with `COPY --from=builder /install /usr/local`. Pip caches and anything the builder pulled in never enter the final image. Measured with `make size`: the old single-stage image was 59.5 MB, the multi-stage one is 56.1 MB. See [Multi-stage build: how it works](#multi-stage-build-how-it-works) for the full explanation.
- **`python:3.12-slim` final base image:** much smaller than a full OS image.
- **`requirements.txt` copied before the app code:** the dependency layer is cached, so code changes rebuild quickly.
- **Healthchecks and `depends_on: condition: service_healthy`:** the API starts only after Postgres and Redis are ready, regardless of the order in which they come up.
- **Named volume `pgdata`:** Postgres data survives `down` and `up`. Redis has no volume because it only holds a disposable counter.
- **Secrets in `.env`:** the file is git-ignored and never committed. `.env.example` has placeholders only.
- **`db` and `redis` publish no ports:** only the API is reachable from the host. The API reaches the others by service name (`db`, `redis`) over the Compose network.
- **`restart: unless-stopped`:** services come back after a crash.

## Multi-stage build: how it works

The Dockerfile has two stages. Each `FROM` starts a completely separate, temporary environment, and files only cross over if you explicitly copy them with `COPY --from=<stage-name>`.

**Stage 1 — the builder (the "fat" environment):**

```dockerfile
FROM python:3.12 AS builder        # full image, ~1 GB unpacked. "AS builder" names the stage
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
```

`--prefix=/install` tells pip to install everything under `/install` instead of the usual `/usr/local`. That gives the dependencies one clean, known location to copy from later.

**Stage 2 — the final image (clean start):**

```dockerfile
FROM python:3.12-slim              # fresh filesystem, ~45 MB, nothing from stage 1
WORKDIR /app
COPY --from=builder /install /usr/local   # reach INTO the builder and copy only this folder
COPY app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`COPY --from=builder` copies from the stage **by its name** (`AS builder`), not by a filesystem path. Because the final stage is a brand-new filesystem, whatever was not copied over physically does not exist in the final image — pip's temp files, the full Debian toolchain, everything.

**Why not just install and delete in one stage?** Image layers are append-only. If a `RUN` installs gcc and a later `RUN` removes it, the removal is just a new layer on top — gcc still exists in the layer below, so the image never shrinks. Multi-stage works because it is not a deletion, it is a selective copy.

**Notes from doing it:**
- Keeping `COPY requirements.txt .` before any other `COPY` inside the stage preserves the layer cache: code changes don't re-download dependencies.
- `python:3.12` (full) in the builder is a one-time ~237 MB compressed download, cached forever after. The final image still only contains slim + the copied packages: **56.1 MB** (old single-stage: 59.5 MB), verified with `make size` and by running `python -c "import fastapi, uvicorn, redis, psycopg"` inside the new image.
- Since `psycopg[binary]` ships precompiled wheels, no compiler is ever needed — `python:3.12-slim` would also work as the builder base. The full base is kept because it is the safe default if a dependency ever needs compiling.

## A problem I faced

After the first `docker compose up`, `/health` returned a generic 503 (`dependency down`) even though all containers were running. The message did not say which dependency had failed, so I changed `/health` to report Postgres and Redis separately. It showed `unexpected keyword argument 'decode_response'` for Redis, which was a typo in my code (`decode_response` instead of `decode_responses`).

I fixed the typo and rebuilt the image with `docker compose up -d --build`, because the code is copied into the image at build time and a plain restart would not pick up the change.

### Second problem: the multi-stage build refused to build, then "hung" on a 236 MB download

Two separate issues, and only one of them was a real bug.

**Bug 1 — `COPY --from` syntax.** I wrote the copy from the builder stage across two lines with a wrong `--from` value (`COPY --from=y` on one line, `builder /install /usr/local` on the next). Docker reads a Dockerfile line by line, so this fails to parse, and `--from` expects the *stage name* from `AS builder` anyway — not a path (the leading `/` is a giveaway something is off: paths point into a filesystem, stage names are labels). Fixed as one line: `COPY --from=builder /install /usr/local`.

**Not a bug — the 236 MB "hang".** While testing the build, it sat for minutes downloading one 236 MB layer and I assumed something was broken. What was actually happening: the builder stage uses full `python:3.12` (~1 GB unpacked, ~237 MB compressed), which had never been pulled before, and the connection was slow (~0.5 MB/s). The final `python:3.12-slim` base was already local, which is why only the builder triggered a download. Watching `docker build` output closely (layer digests + progress in bytes) instead of just waiting blindly made this obvious. It is a one-time cost — the layer is cached, and subsequent builds skip it.

Lesson: distinguish "the build is doing something expensive but expected" from "the build is failing". The first shows steady progress on a recognizable layer; the second shows an error with a step number (`#11` etc.) that you can look up in the same log.
