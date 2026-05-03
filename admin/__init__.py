"""Admin routes for accessing logs and profiling data."""

from fastapi import APIRouter
from config import get_settings

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/logs",
    summary="Query sample logs from Elasticsearch",
)
async def get_logs(
    log_type: str | None = None,
    endpoint: str | None = None,
    limit: int = 20,
):
    """Return sample log entries from Elasticsearch.

    Optional filters:
      - ``log_type``: INFO, DEBUG, or ERROR
      - ``endpoint``: filter by endpoint path
      - ``limit``: number of records to return (default 20)
    """
    settings = get_settings()
    try:
        from elasticsearch import AsyncElasticsearch

        es = AsyncElasticsearch(
            hosts=[settings.elasticsearch_url],
            request_timeout=5,
        )

        # Build query
        must_clauses = []
        if log_type:
            must_clauses.append({"match": {"log_type": log_type}})
        if endpoint:
            must_clauses.append({"match": {"endpoint_name": endpoint}})

        body = {
            "query": {
                "bool": {"must": must_clauses} if must_clauses else {"match_all": {}}
            },
            "sort": [{"timestamp": {"order": "desc"}}],
            "size": limit,
        }

        result = await es.search(index=settings.elasticsearch_index, body=body)
        await es.close()

        hits = result.get("hits", {}).get("hits", [])
        logs = [hit["_source"] for hit in hits]

        return {
            "total": result.get("hits", {}).get("total", {}).get("value", 0),
            "logs": logs,
            "example_log_format": {
                "timestamp": "2026-04-05T14:30:00+00:00",
                "log": "127.0.0.1:54321 - GET - http://localhost:8000/packages - 200 - 12.5ms",
                "log_type": "INFO",
                "service_name": "PackageGo API",
                "endpoint_name": "/packages",
                "process_time_ms": 12.5,
            },
        }
    except Exception as exc:
        return {
            "error": f"Elasticsearch unavailable: {str(exc)}",
            "hint": "Make sure Elasticsearch is running on the configured URL",
            "example_logs": [
                {
                    "timestamp": "2026-04-05T14:30:00+00:00",
                    "log": "127.0.0.1:54321 - GET - http://localhost:8000/ - 200 - 5.23ms",
                    "log_type": "INFO",
                    "service_name": "PackageGo API",
                    "endpoint_name": "/",
                    "process_time_ms": 5.23,
                },
                {
                    "timestamp": "2026-04-05T14:30:01+00:00",
                    "log": "127.0.0.1:54322 - POST - http://localhost:8000/auth/login - 401 - 15.67ms",
                    "log_type": "DEBUG",
                    "service_name": "PackageGo API",
                    "endpoint_name": "/auth/login",
                    "process_time_ms": 15.67,
                },
                {
                    "timestamp": "2026-04-05T14:30:02+00:00",
                    "log": "127.0.0.1:54323 - GET - http://localhost:8000/missing - 500 - 2.11ms",
                    "log_type": "ERROR",
                    "service_name": "PackageGo API",
                    "endpoint_name": "/missing",
                    "process_time_ms": 2.11,
                },
            ],
        }
