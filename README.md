# PackageGo API

A FastAPI backend that connects **travelers** going from city A to B with **senders** who need packages delivered. Built with async PostgreSQL, JWT authentication, Redis, Celery, and Elasticsearch.

---

## Assignment 4 Features

### 1a · CORS & TrustedHostMiddleware
Configured in `middleware/cors.py` and registered in `main.py`.

- Allows configurable origins, methods, and headers via `.env`
- `TrustedHostMiddleware` restricts requests to allowed hostnames

### 1b · Custom Logging → Elasticsearch
Implemented in `middleware/logging_mw.py`.

```
127.0.0.1:54321 - GET - http://localhost:8000/packages - 200 - 12.5ms
```

| Status Range | Log Level |
|---|---|
| 2xx / 3xx | `INFO` |
| 4xx | `DEBUG` |
| 5xx | `ERROR` |

Each log is stored in Elasticsearch with: `timestamp`, `log`, `log_type`, `service_name`, `endpoint_name`.  
Query logs at: `GET /admin/logs?log_type=ERROR&limit=10`

### 1c · Rate Limiting (SlowAPI + Redis)
Implemented in `middleware/rate_limiter.py`.

| Rule | Scope | Applies to |
|---|---|---|
| **60 requests/min** | Per IP | All endpoints |
| **500 requests/hr** | Per IP | All endpoints |
| **50 writes/hr** | Per IP | POST / PUT / PATCH / DELETE |
| No limit | — | GET (read) requests |

Returns `429 Too Many Requests` with `Retry-After` header on violation.

### 1d · Profiling (pyinstrument)
Implemented in `middleware/profiling.py`.

- Activate on any request: `X-Profile: true` header or `?profile=true`
- Full HTML report: `GET /admin/profiling/last`
- Slow endpoint analysis: `GET /admin/profiling/slow` (avg/max latency + reasoning + suggestions)
- **Profiler overhead**: pyinstrument uses statistical sampling (~2-5%). Disable entirely with `ENABLE_PROFILING=false` in production.

### 2a · Email Confirmation & Password Reset (Celery)
Tasks in `tasks/email_tasks.py`, routes in `auth/routes.py`.

| Endpoint | Description |
|---|---|
| `POST /auth/register` | Creates user, triggers `send_confirmation_email` task |
| `POST /auth/confirm-email/{token}` | Confirms email address |
| `POST /auth/forgot-password` | Triggers `send_password_reset_email` task |

### 2b · Image Upload & Compression (Celery + Pillow)
Routes in `images/__init__.py`, task in `tasks/image_tasks.py`.

| Endpoint | Description |
|---|---|
| `POST /packages/{id}/image` | Upload image → queued for compression |
| `GET /packages/{id}/image` | Retrieve compressed image |

Compression pipeline:
1. Log **original size**
2. Resize if width > 1920px
3. Convert to JPEG quality=70
4. Log **compressed size + % reduction**
5. Store in PostgreSQL (`PackageImage` table)
6. Optionally upload to MinIO (local S3)

### 2c · Periodic Delivery Digest (Celery Beat)
Task in `tasks/digest_tasks.py`, scheduled in `celery_app.py`.

- Runs **every hour** automatically
- Aggregates all package status changes from the last hour
- Creates summary `Notification` for each affected sender/traveler

---

## Project Structure

```
├── admin/              # Admin routes (logs, profiling)
├── auth/               # JWT auth, login, register, email confirm
├── celery_app.py       # Celery instance + Beat schedule
├── config.py           # All settings via environment variables
├── db.py               # Async SQLAlchemy engine
├── docker-compose.yml  # Redis + Elasticsearch + MinIO
├── errors/             # Custom exceptions and handlers
├── images/             # Image upload and retrieval routes
├── main.py             # App entry point + middleware registration
├── middleware/
│   ├── cors.py         # CORS + TrustedHostMiddleware
│   ├── logging_mw.py   # Structured logging + Elasticsearch
│   ├── profiling.py    # pyinstrument profiling middleware
│   └── rate_limiter.py # SlowAPI + write-limit middleware
├── migrate.py          # DB migration helper
├── models/             # SQLModel table definitions
├── notifications/      # In-app notification system
├── packages/           # Package CRUD + status management
├── reviews/            # Review system
├── senders/            # Sender profile management
├── spec.md             # Full assignment specification
├── tasks/
│   ├── digest_tasks.py # Hourly delivery digest (Celery Beat)
│   ├── email_tasks.py  # Email confirmation + reset
│   └── image_tasks.py  # Image compression + storage
├── travelers/          # Traveler profile management
└── trips/              # Trip CRUD
```

---

## Setup & Running

### 1. Install dependencies
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your database URL and secrets
```

### 3. Start infrastructure
```bash
docker-compose up -d    # Redis · Elasticsearch · MinIO
```

### 4. Start the API
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Start Celery (background tasks)
```bash
# Worker (email + image tasks)
celery -A celery_app worker --loglevel=info

# Beat scheduler (hourly digest)
celery -A celery_app beat --loglevel=info
```

### 6. API Docs
Open `http://localhost:8000/docs`

---

## Testing

```bash
python test_assignment4.py   # Assignment 4 verification (26 tests)
python test_all.py            # Full suite
```

---

## Key Admin Endpoints

| Endpoint | Description |
|---|---|
| `GET /admin/logs` | Query logs from Elasticsearch |
| `GET /admin/profiling/slow` | Top-10 slowest endpoints |
| `GET /admin/profiling/last` | Last profiling HTML report |
