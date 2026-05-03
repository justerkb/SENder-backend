"""Custom logging middleware with Elasticsearch integration.

Log format: <IP>:<Port> - <Method> - <URL> - <Status Code> - <Processing Time>

Log levels:
  - INFO:  2xx / 3xx responses
  - DEBUG: 4xx responses
  - ERROR: 5xx responses

Each log record is also pushed asynchronously to Elasticsearch (index
``packagego-logs``) with fields: timestamp, log, log_type, service_name,
endpoint_name.
"""

import logging
import time
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from config import get_settings

logger = logging.getLogger("packagego.access")

# ---------------------------------------------------------------------------
# Elasticsearch async client – created lazily to avoid import errors when ES
# is not available.
# ---------------------------------------------------------------------------
_es_client = None


async def _get_es_client():
    """Return (or create) a shared async Elasticsearch client."""
    global _es_client
    if _es_client is None:
        try:
            from elasticsearch import AsyncElasticsearch

            settings = get_settings()
            _es_client = AsyncElasticsearch(
                hosts=[settings.elasticsearch_url],
                request_timeout=5,
            )
        except Exception as exc:
            logger.warning("Elasticsearch client init failed: %s", exc)
    return _es_client


async def close_es_client():
    """Close the shared Elasticsearch client – call on app shutdown."""
    global _es_client
    if _es_client is not None:
        await _es_client.close()
        _es_client = None


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request with timing, then replicates to Elasticsearch."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Capture client info
        client = request.client
        client_host = client.host if client else "unknown"
        client_port = client.port if client else 0

        method = request.method
        url = str(request.url)
        endpoint_name = request.url.path

        start = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start
        process_time_ms = round(process_time * 1000, 2)

        status_code = response.status_code

        # Determine log level
        if status_code >= 500:
            log_type = "ERROR"
        elif status_code >= 400:
            log_type = "DEBUG"
        else:
            log_type = "INFO"

        log_message = (
            f"{client_host}:{client_port} - {method} - {url} "
            f"- {status_code} - {process_time_ms}ms"
        )

        # Log to stdout
        log_func = {
            "INFO": logger.info,
            "DEBUG": logger.debug,
            "ERROR": logger.error,
        }.get(log_type, logger.info)
        log_func(log_message)

        # Add timing header
        response.headers["X-Process-Time"] = str(process_time_ms)

        # Push to Elasticsearch (fire-and-forget)
        try:
            await self._push_to_es(
                log_message, log_type, endpoint_name, process_time_ms
            )
        except Exception:
            pass  # never let ES failures affect the response

        return response

    async def _push_to_es(
        self,
        log_message: str,
        log_type: str,
        endpoint_name: str,
        process_time_ms: float,
    ) -> None:
        es = await _get_es_client()
        if es is None:
            return

        settings = get_settings()
        doc = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "log": log_message,
            "log_type": log_type,
            "service_name": settings.app_name,
            "endpoint_name": endpoint_name,
            "process_time_ms": process_time_ms,
        }
        try:
            await es.index(index=settings.elasticsearch_index, document=doc)
        except Exception as exc:
            logger.debug("ES index error: %s", exc)
