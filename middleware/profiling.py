"""Profiling middleware using pyinstrument.

Activation:
  - Header ``X-Profile: true``   OR
  - Query parameter ``?profile=true``

When activated the response includes:
  - ``X-Profile-Results`` header with a short text summary
  - The full HTML profiling report is available at ``GET /admin/profiling/last``

Additionally every request's latency is recorded in an in-memory dict so
that ``GET /admin/profiling/slow`` can report the top-N slowest endpoints.

Production safety:
  - Set ``ENABLE_PROFILING=false`` to completely disable.
  - pyinstrument uses *statistical sampling* (not deterministic tracing),
    so overhead is only ~2-5 %.
  - When even that is too much, disable via the env var above. The
    middleware then becomes a pure pass-through with near-zero cost.
"""

import logging
import time
from collections import defaultdict
from typing import Dict, List

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, HTMLResponse, JSONResponse

from config import get_settings

logger = logging.getLogger("packagego.profiling")

settings = get_settings()

# ---------------------------------------------------------------------------
# In-memory stats store
# ---------------------------------------------------------------------------

# endpoint -> list of latencies in ms
_latency_store: Dict[str, List[float]] = defaultdict(list)
_MAX_SAMPLES = 500  # keep last N samples per endpoint

# last profile HTML (for /admin/profiling/last)
_last_profile_html: str = ""


def get_latency_store():
    return _latency_store


def get_last_profile_html():
    return _last_profile_html


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class ProfilingMiddleware(BaseHTTPMiddleware):

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        endpoint = request.url.path

        # Should we profile this request?
        should_profile = False
        if settings.enable_profiling:
            should_profile = (
                request.headers.get("x-profile", "").lower() == "true"
                or request.query_params.get("profile", "").lower() == "true"
            )

        start = time.perf_counter()

        if should_profile:
            response = await self._profiled_call(request, call_next)
        else:
            response = await call_next(request)

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        # Record latency
        samples = _latency_store[endpoint]
        samples.append(elapsed_ms)
        if len(samples) > _MAX_SAMPLES:
            _latency_store[endpoint] = samples[-_MAX_SAMPLES:]

        return response

    async def _profiled_call(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        global _last_profile_html
        try:
            from pyinstrument import Profiler
        except ImportError:
            logger.warning("pyinstrument not installed – profiling skipped")
            return await call_next(request)

        profiler = Profiler(async_mode="enabled")
        profiler.start()
        response = await call_next(request)
        profiler.stop()

        # Store HTML report
        _last_profile_html = profiler.output_html()

        # Attach short text summary in header
        text_output = profiler.output_text(unicode=False, color=False)
        # Truncate for header (keep first 500 chars)
        short = text_output[:500].replace("\n", " | ")
        response.headers["X-Profile-Results"] = short

        return response


# ---------------------------------------------------------------------------
# Admin routes  (registered in main.py)
# ---------------------------------------------------------------------------

from fastapi import APIRouter

profiling_router = APIRouter(prefix="/admin/profiling", tags=["admin"])


@profiling_router.get(
    "/last",
    summary="Last profiling HTML report",
    response_class=HTMLResponse,
)
async def last_profile():
    html = get_last_profile_html()
    if not html:
        return HTMLResponse("<p>No profiling data yet. Send a request with X-Profile: true header.</p>")
    return HTMLResponse(html)


@profiling_router.get(
    "/slow",
    summary="Top-10 slowest endpoints with avg/max latency",
)
async def slow_endpoints():
    """Return the top-10 slowest endpoints sorted by average latency.

    Also provides reasoning hints (e.g. high variance → possible cold start,
    consistently slow → DB or I/O bottleneck).
    """
    stats = []
    for endpoint, samples in _latency_store.items():
        if not samples:
            continue
        avg = round(sum(samples) / len(samples), 2)
        mx = round(max(samples), 2)
        mn = round(min(samples), 2)
        count = len(samples)
        variance = round(
            sum((s - avg) ** 2 for s in samples) / count, 2
        ) if count > 1 else 0.0

        # Heuristic reasoning
        reasons = []
        if avg > 500:
            reasons.append("Consistently slow – likely DB query or external I/O bottleneck")
        if mx > 3 * avg and avg < 200:
            reasons.append("High max vs avg – possible cold-start or GC pause")
        if variance > avg * avg:
            reasons.append("High variance – inconsistent performance, check caching or connection pooling")
        if not reasons:
            reasons.append("Within acceptable range")

        suggestions = []
        if avg > 200:
            suggestions.append("Consider adding DB query caching or pagination")
        if avg > 1000:
            suggestions.append("Offload heavy work to a Celery background task")
        if mx > 2000:
            suggestions.append("Investigate individual slow requests via X-Profile header")

        stats.append({
            "endpoint": endpoint,
            "sample_count": count,
            "avg_ms": avg,
            "max_ms": mx,
            "min_ms": mn,
            "variance": variance,
            "reasons": reasons,
            "optimization_suggestions": suggestions,
        })

    stats.sort(key=lambda s: s["avg_ms"], reverse=True)
    top_10 = stats[:10]

    return {
        "profiler_overhead_note": (
            "pyinstrument uses statistical sampling (~2-5% overhead). "
            "To eliminate overhead entirely, set ENABLE_PROFILING=false in production. "
            "The latency stats shown here are collected WITHOUT profiling active "
            "(unless you explicitly trigger it with X-Profile header)."
        ),
        "slow_endpoints": top_10,
    }
