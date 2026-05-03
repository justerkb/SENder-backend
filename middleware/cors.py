"""CORS and TrustedHostMiddleware configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from config import get_settings


def setup_cors(app: FastAPI) -> None:
    """Add CORS and TrustedHost middleware to the application."""
    settings = get_settings()

    # Parse comma-separated origins and hosts
    origins = [o.strip() for o in settings.cors_origins.split(",")]
    methods = [m.strip() for m in settings.cors_allow_methods.split(",")]
    headers = [h.strip() for h in settings.cors_allow_headers.split(",")]
    trusted = [h.strip() for h in settings.trusted_hosts.split(",")]

    # CORS – must be added before TrustedHost so preflight responses include
    # the correct headers even when the host header is checked.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=methods,
        allow_headers=headers,
    )

    # TrustedHostMiddleware – blocks requests whose Host header is not in the
    # allowed list.  Use "*" during development to allow any host.
    if "*" not in trusted:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted)
