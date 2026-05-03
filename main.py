"""PackageGo API – main application with middleware and background tasks."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from travelers.routes import router as travelers_router
from senders.routes import router as senders_router
from packages.routes import router as packages_router
from trips.routes import router as trips_router
from reviews.routes import router as reviews_router
from auth.routes import router as auth_router
from notifications.routes import router as notifications_router
from images import router as images_router
from admin import router as admin_router
from db import init_db
from errors.handlers import register_exception_handlers
from auth.redis_blocklist import close_redis

# ──────────────────────────────────────────────────────────
# Logging configuration
# ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s │ %(name)-30s │ %(levelname)-5s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


# ──────────────────────────────────────────────────────────
# Lifespan
# ──────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_redis()
    # Close the shared Elasticsearch client
    from middleware.logging_mw import close_es_client
    await close_es_client()


# ──────────────────────────────────────────────────────────
# App instance
# ──────────────────────────────────────────────────────────
app = FastAPI(
    title="PackageGo API",
    description=(
        "Connect travelers going from A to B with senders who need packages delivered. "
        "Features JWT authentication, role-based authorization, Redis token blocklist, "
        "middleware (CORS, logging, rate limiting, profiling), "
        "and Celery background tasks (email, image compression, digest)."
    ),
    version="4.0.0",
    lifespan=lifespan,
)

# ──────────────────────────────────────────────────────────
# Exception handlers
# ──────────────────────────────────────────────────────────
register_exception_handlers(app)

# ──────────────────────────────────────────────────────────
# Middleware (order matters – first added = outermost)
# ──────────────────────────────────────────────────────────

# 1. CORS & TrustedHost
from middleware.cors import setup_cors
setup_cors(app)

# 2. Custom Logging → Elasticsearch
from middleware.logging_mw import LoggingMiddleware
app.add_middleware(LoggingMiddleware)

# 3. Rate Limiting (SlowAPI global + write-method limiter)
from middleware.rate_limiter import get_limiter, rate_limit_exceeded_handler, WriteRateLimitMiddleware
from slowapi.errors import RateLimitExceeded

app.state.limiter = get_limiter()
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(WriteRateLimitMiddleware)

# 4. Profiling
from middleware.profiling import ProfilingMiddleware
app.add_middleware(ProfilingMiddleware)

# ──────────────────────────────────────────────────────────
# Routers
# ──────────────────────────────────────────────────────────

# Public + Auth routes
app.include_router(auth_router)
app.include_router(travelers_router)
app.include_router(senders_router)
app.include_router(packages_router)
app.include_router(trips_router)
app.include_router(reviews_router)
app.include_router(notifications_router)
app.include_router(images_router)

# Admin routes
app.include_router(admin_router)

# Profiling admin routes
from middleware.profiling import profiling_router
app.include_router(profiling_router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to PackageGo API",
        "docs": "/docs",
        "version": "4.0.0",
        "features": [
            "CORS & TrustedHost Middleware",
            "Structured Logging → Elasticsearch",
            "Rate Limiting (60/min, 500/hr, 50 writes/hr)",
            "On-demand Profiling (X-Profile header)",
            "Celery Background Tasks (email, images, digest)",
        ],
    }
