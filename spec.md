# PackageGo API – Middleware & Background Tasks Specification

## 1. Middleware

### 1a. CORS & TrustedHostMiddleware
- **CORS**: Allow configurable origins (default: `*` for dev), methods `GET, POST, PUT, PATCH, DELETE, OPTIONS`, headers `*`, and credentials.
- **TrustedHostMiddleware**: Restrict to configurable allowed hosts (default: `localhost`, `127.0.0.1`).
- All settings in `config.py` via environment variables.

### 1b. Custom Logging Middleware
**Basic (stdout)**:
- Format: `<IP>:<Port> - <Method> - <URL> - <Status Code> - <Processing Time>`
- Uses Python `logging` with structured output.

**Optional – Elasticsearch integration**:
- Split into **INFO**, **DEBUG**, **ERROR** log levels.
- Each log record stores: `timestamp`, `log` (the message), `log_type` (INFO/DEBUG/ERROR), `service_name` ("PackageGo"), `endpoint_name`.
- Stored in a local Elasticsearch index `packagego-logs`.
- Elasticsearch connection via `elasticsearch-py` async client.
- A utility endpoint `GET /admin/logs` to query sample logs from Elasticsearch.

### 1c. API Throttling & Rate Limiting
Using **SlowAPI** (a FastAPI rate-limiting library wrapping `limits`), backed by **Redis**:

| Rule | Scope | Applies to |
|---|---|---|
| 60 requests/min | Per IP | All endpoints |
| 500 requests/hr | Per IP | All endpoints |
| 50 write requests/hr | Per IP | POST, PUT, PATCH, DELETE only |
| No limit | – | GET (read) requests |

- Write-method limiting is implemented via a custom middleware that checks `request.method`.
- On limit exceeded → return `429 Too Many Requests` with `Retry-After` header.

### 1d. Profiling Middleware
- **Call Stack Profiling**: Using `pyinstrument` to profile each endpoint on-demand (enabled via `X-Profile: true` header or `?profile=true` query param).
- **Latency tracking**: Already captured by the logging middleware; additionally stored per-endpoint for aggregated stats.
- **Slow endpoint identification**: A `GET /admin/profiling/slow` endpoint that returns the top-N slowest endpoints with average response times and reasoning.
- **Profiler overhead mitigation**: Profiling is **disabled by default** and only activated on-demand via header/param. In production, profiling should be completely disabled via `ENABLE_PROFILING=false` env var. The profiler is lightweight (`pyinstrument` uses statistical sampling, not deterministic tracing, so overhead is ~2-5%).

---

## 2. Background Tasks (Celery)

### 2a. Email Confirmation & Password Reset
- **Celery** with **Redis** as broker.
- `send_confirmation_email` task: triggered on user registration; logs email content to console (simulated SMTP).
- `send_password_reset_email` task: new endpoint `POST /auth/forgot-password` triggers the task.
- New `email_confirmed` boolean field on User model.
- New `POST /auth/confirm-email/{token}` endpoint.

### 2b. Image Upload with Background Compression
- New `POST /packages/{package_id}/image` endpoint for image upload.
- Celery task `compress_and_store_image`:
  1. Accept raw image bytes.
  2. Compress using **Pillow** (resize + JPEG quality reduction).
  3. Log before/after file sizes.
  4. Store compressed binary in PostgreSQL (new `PackageImage` model with `image_data: bytes` column).
- **Optional MinIO**: Store compressed images in local MinIO S3, save URLs in PostgreSQL.

### 2c. Custom Background Task – Package Delivery Notifications Digest
- A periodic Celery **Beat** task that runs every hour.
- Aggregates all package status changes in the last hour and sends a summary notification to relevant users.
- This demonstrates scheduled/periodic tasks beyond simple on-demand tasks.

---

## Infrastructure Requirements

| Service | Purpose | Connection |
|---|---|---|
| **Redis** | Token blocklist, Celery broker, rate limiting backend | `redis://localhost:6379/0` |
| **Elasticsearch** | Log storage (optional) | `http://localhost:9200` |
| **PostgreSQL** | Primary database | Existing |
| **MinIO** (optional) | S3-compatible image storage | `http://localhost:9000` |

---

## 3. Docker & Deployment

### 3a. Dockerfile – Small & Fast Container

The application is containerized using a **multi-stage Docker build** based on `python:3.12-slim`.

**Optimization techniques used:**

| Technique | Description |
|---|---|
| **Multi-stage build** | Stage 1 (`builder`) installs build tools + compiles C extensions; Stage 2 (`runtime`) copies only the virtualenv — no gcc, no pip cache in final image |
| **`python:3.12-slim` base** | ~45 MB vs ~900 MB for full `python:3.12` — Debian-slim removes man pages, docs, unnecessary packages |
| **`.dockerignore`** | Excludes `venv/`, `__pycache__/`, `.git/`, test files, IDE files — reduces build context size and speeds up `COPY` |
| **Layer caching** | `COPY requirements.txt` before `COPY .` — code changes don't trigger dependency reinstall |
| **`--no-cache-dir`** | Prevents pip from storing wheel cache inside the image |
| **`--no-compile`** | Skips `.pyc` generation during pip install (Python JIT-compiles at runtime) |
| **Non-root user** | Runs as `appuser` (UID 1000) — security best practice |
| **Single `RUN` chains** | `apt-get update && install && rm` in one layer to avoid caching apt lists |
| **Runtime-only libs** | Final image has `libpq5` + `libjpeg` but NOT `gcc`, `libpq-dev`, or `-dev` headers |

### 3b. Docker Compose – Full Service Orchestration

All services start with a single command: `docker compose up -d`

**Services:**

| # | Service | Image | Port(s) | Purpose |
|---|---|---|---|---|
| 1 | **postgres** | `postgres:16-alpine` | `5432` | Primary database |
| 2 | **redis** | `redis:7-alpine` | `6379` | Cache, Celery broker, rate limiting |
| 3 | **elasticsearch** | `elasticsearch:8.12.0` | `9200` | Structured log storage |
| 4 | **minio** | `minio/minio:latest` | `9000`, `9001` | S3-compatible image storage |
| 5 | **mailhog** | `mailhog/mailhog:latest` | `1025`, `8025` | Fake SMTP server + email viewer UI |
| 6 | **app** | Custom (Dockerfile) | `8000` | FastAPI application |
| 7 | **celery-worker** | Custom (Dockerfile) | — | Background task execution |
| 8 | **celery-beat** | Custom (Dockerfile) | — | Periodic task scheduler |
| 9 | **flower** | `mher/flower:2.0` | `5555` | Celery task monitoring UI |
| 10 | **pgadmin** | `dpage/pgadmin4:latest` | `5050` | Database browser UI |
| 11 | **redis-commander** | `rediscommander/redis-commander` | `8081` | Redis data viewer UI |

### 3c. `depends_on` with Health Checks

All services declare dependency ordering using `depends_on` with `condition: service_healthy`:

- **postgres**: `pg_isready -U packagego`
- **redis**: `redis-cli ping`
- **elasticsearch**: `curl -fs http://localhost:9200/_cluster/health`
- **minio**: `curl -fs http://localhost:9000/minio/health/live`

The `app` service waits for postgres + redis + elasticsearch to be healthy before starting. Celery workers wait for postgres + redis. Flower waits for redis.

### 3d. Persistent Volumes

All stateful services use **named Docker volumes** so data survives container restarts:

| Volume | Service | What it stores |
|---|---|---|
| `postgres_data` | postgres | Database files (`/var/lib/postgresql/data`) |
| `redis_data` | redis | RDB snapshots + AOF logs (`/data`) |
| `es_data` | elasticsearch | Index shards (`/usr/share/elasticsearch/data`) |
| `minio_data` | minio | Uploaded objects (`/data`) |
| `pgadmin_data` | pgadmin | Saved servers, preferences (`/var/lib/pgadmin`) |

> **Note**: `docker compose down` preserves volumes. Only `docker compose down -v` deletes them.

### 3e. Monitoring & Admin UIs

| Tool | URL | Credentials | Purpose |
|---|---|---|---|
| **Swagger/Docs** | http://localhost:8000/docs | — | API documentation |
| **pgAdmin** | http://localhost:5050 | `admin@packagego.local` / `admin` | PostgreSQL browser |
| **Flower** | http://localhost:5555 | — | Celery task monitor |
| **Redis Commander** | http://localhost:8081 | — | Redis data viewer |
| **Mailhog** | http://localhost:8025 | — | Captured email viewer |
| **MinIO Console** | http://localhost:9001 | `minioadmin` / `minioadmin` | Object storage browser |

### 3f. Environment Configuration

A separate `.env.docker` file is used for Docker deployments where all hostnames reference **Docker Compose service names** (`postgres`, `redis`, `elasticsearch`, `minio`, `mailhog`) instead of `localhost`.

### 3g. Quick Reference Commands

```bash
# Start all services in background
docker compose up -d

# Rebuild after code changes
docker compose up -d --build

# View logs for a specific service
docker compose logs -f app

# Stop all services (data preserved)
docker compose down

# Stop + delete all data
docker compose down -v

# Check service status
docker compose ps
```
