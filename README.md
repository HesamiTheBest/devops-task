# DevOps Task: FastAPI + Postgres + Redis

A small FastAPI service that stores items in **Postgres**, counts requests in **Redis**, and processes background jobs with a **worker**. It runs behind an **Nginx** reverse proxy with three API replicas, all managed by Docker Compose.

## Architecture

```
                         +--> api (replica 1) --+
client --> nginx :8080 --+--> api (replica 2) --+--> db (Postgres)
                         +--> api (replica 3) --+--> redis
                                                      ^
                          worker  <-- jobs queue -----+
                          worker  --> db (results)
```

| Service | Image | Role | Published port |
|---------|-------|------|----------------|
| `nginx` | `nginx:alpine` | Reverse proxy and load balancer | 8080 |
| `api` (x3) | built from `Dockerfile` | FastAPI app | none |
| `worker` | same image as `api` | Processes queued jobs | none |
| `db` | `postgres:16-alpine` | Persistent storage | none |
| `redis` | `redis:7-alpine` | Request counter and job queue | none |

## Run

```bash
cp .env.example .env
docker compose up -d --build
docker compose restart nginx
```

Or use the shortcut, which does all three steps:

```bash
make up
```

`.env` holds the database credentials. `.env.example` contains placeholder values and can be used as is.

Check that it works:

```bash
curl localhost:8080/health
curl -X POST "localhost:8080/items?name=test"
curl localhost:8080/items
```

Interactive API docs: http://localhost:8080/docs

Stop the system:

```bash
make down      # stops containers, keeps data
make clean     # stops containers and deletes data
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Checks Postgres and Redis. Returns 200, or 503 with the failing dependency. Includes the `instance` that answered |
| POST | `/items?name=...` | Stores an item in Postgres |
| GET | `/items` | Lists items and increments a request counter in Redis |
| POST | `/jobs?name=...` | Queues a background job and returns immediately |
| GET | `/results` | Lists jobs finished by the worker |

## Project structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py                 # API
│   └── worker.py               # background worker
├── Dockerfile
├── docker-compose.yml
├── docker-compose.dev.yml      # development overrides
├── nginx.conf
├── Makefile
├── requirements.txt
├── .env.example
├── .dockerignore
└── .gitignore
```

## Technical decisions

- **Multi-stage build on `python:3.12-slim`:** dependencies are installed in a builder stage and only the installed packages are copied into the final image, so build leftovers stay out of it.
- **`requirements.txt` copied before the app code:** the dependency layer is cached, so code changes rebuild quickly.
- **Healthchecks and `depends_on: condition: service_healthy`:** the API and worker start only after Postgres and Redis are ready, regardless of startup order.
- **Named volume `pgdata`:** Postgres data survives `down` and `up`. Redis has no volume because it only holds a disposable counter and a job queue.
- **Secrets in `.env`:** the file is git-ignored and never committed. `.env.example` has placeholders only.
- **`db` and `redis` publish no ports:** they are reachable only inside the Compose network, by service name (`db`, `redis`).
- **Stateless API:** all state lives in Postgres and Redis, so any replica can answer any request.
- **`restart: unless-stopped`:** services come back after a crash.

## Image size and security

- The first single-stage image was **59.4 MB**. The multi-stage image is **<NEW SIZE> MB** (check with `docker images task-api` and fill in).
- The container runs as a **non-root user** (`appuser`) to limit the impact of a compromise:

```bash
docker compose exec api whoami     # appuser
```

- `.dockerignore` keeps `.env`, `.venv` and `.git` out of the image.

## Reverse proxy and replicas

Nginx is the only service reachable from the host (port 8080). It forwards requests to the three `api` replicas using round-robin.

- The `api` service publishes no ports. Several replicas cannot share one host port, and this keeps the API private (`curl localhost:8000` fails by design).
- Compose DNS resolves the name `api` to the IP addresses of all replicas, and Nginx balances across them.
- `/health` returns the `instance` field so the balancing is visible:

```bash
for i in 1 2 3 4 5 6; do curl -s localhost:8080/health; echo; done
```

- Limitation: Nginx resolves `api` when it starts. After the API containers are recreated, Nginx needs a restart or it returns 502, so `make up` restarts it automatically.

## Background worker

`POST /jobs?name=...` pushes a job onto a Redis list and returns immediately. A separate `worker` container (same image, different command) takes jobs from the list, processes them, and stores the result in Postgres. `GET /results` lists finished jobs.

```
POST /jobs -> api -> Redis list "jobs" -> worker -> Postgres (results table)
```

Try it:

```bash
curl -X POST "localhost:8080/jobs?name=job1"
docker compose logs -f worker
curl localhost:8080/results
```

## Development

```bash
make dev
```

This adds `docker-compose.dev.yml` on top of the base file:

- the `app/` folder is bind-mounted, so code changes show up immediately
- uvicorn runs with `--reload`
- Postgres is published on host port 5433 for local inspection

The dev file is not named `docker-compose.override.yml`, because Compose would load that automatically and the normal run would no longer match production. A dev run uses local files, so test with `make up` to verify the image itself.

## Makefile shortcuts

| Command | Description |
|---------|-------------|
| `make up` | Create `.env` if missing, build, start, restart Nginx |
| `make dev` | Same, with the development overrides |
| `make down` | Stop containers, keep data |
| `make logs` | Follow the API logs |
| `make ps` | Show container status |
| `make clean` | Stop containers and delete volumes (data is lost) |
| `make push` | Build, tag and push the image to Docker Hub |

## Registry and versioning

Image: `hesammardani/devops-task`

Each release is tagged three ways:

- `1.0.0`: the release version (semantic versioning, never overwritten)
- `<git-sha>`: the commit the image was built from
- `latest`: the newest release

Pull: `docker pull hesammardani/devops-task:1.0.0`

Note: `1.0.0` was the first published version and predates the non-root user, the Nginx proxy and the worker. Those changes are in the repository but not in a pushed image yet.

## A problem I faced

After the first `docker compose up`, `/health` returned a generic 503 (`dependency down`) even though all containers were running. The message did not say which dependency had failed, so I changed `/health` to report Postgres and Redis separately. It showed `unexpected keyword argument 'decode_response'` for Redis, which was a typo in my code (`decode_response` instead of `decode_responses`).

I fixed the typo and rebuilt the image with `docker compose up -d --build`, because the code is copied into the image at build time and a plain restart would not pick up the change.

## Other problems and fixes

- **Nginx returned 502 after rebuilding:** Nginx kept the old IP addresses of the recreated API containers. Restarting Nginx fixes it, and `make up` now does this automatically.
- **The worker kept restarting with a Redis `TimeoutError`:** the client gave up while waiting on an empty queue. Fixed with `socket_timeout=None` and a `brpop` timeout so the loop keeps running.