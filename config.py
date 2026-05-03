from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    app_name: str = "PackageGo API"
    database_url: str

    # JWT
    jwt_secret: str = "super-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # CORS
    cors_origins: str = "*"
    cors_allow_methods: str = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    cors_allow_headers: str = "*"
    cors_allow_credentials: bool = True

    # Trusted hosts
    trusted_hosts: str = "localhost,127.0.0.1"

    # Elasticsearch
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index: str = "packagego-logs"

    # Rate limiting
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 500
    rate_limit_write_per_hour: int = 50

    # Profiling
    enable_profiling: bool = True

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # SMTP (simulated)
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from_email: str = "noreply@packagego.local"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "packagego-images"
    minio_use_ssl: bool = False

    # Sync database URL (for Celery tasks that need DB access)
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/packagego"


@lru_cache
def get_settings() -> Settings:
    return Settings()
