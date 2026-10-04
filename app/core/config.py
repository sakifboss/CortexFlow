"""
Strongly-typed application configuration.

All settings are loaded from environment variables (or `.env`).
A single `Settings` instance is shared app-wide via dependency injection
(`app.core.deps.get_settings`).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, PostgresDsn, RedisDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────
    env: Literal["dev", "staging", "prod", "test"] = "dev"
    app_name: str = "CortexFlow"
    version: str = "0.1.0"
    secret_key: str = Field(min_length=16)
    api_prefix: str = "/api/v1"
    cors_origins: list[AnyHttpUrl] | str = "http://localhost:3000"

    # ── JWT / Auth ────────────────────────────────────────────
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 14
    verification_token_ttl_hours: int = 24

    # ── Postgres ──────────────────────────────────────────────
    database_url: str
    database_sync_url: str | None = None
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_echo: bool = False

    # ── Redis / Celery ───────────────────────────────────────
    redis_url: RedisDsn
    redis_cache_url: RedisDsn | None = None
    celery_broker_url: str
    celery_result_backend: str

    # ── Vector DB ─────────────────────────────────────────────
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "cortexflow_chunks"
    qdrant_vector_size: int = 768

    # ── Neo4j ─────────────────────────────────────────────────
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "cortexneo4j"

    # ── MinIO / S3 ────────────────────────────────────────────
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "cortexminio"
    minio_secret_key: str = "cortexminio"
    minio_bucket: str = "cortexflow"
    minio_secure: bool = False

    # ── ElasticSearch ─────────────────────────────────────────
    elasticsearch_url: str = "http://elasticsearch:9200"

    # ── LLM ───────────────────────────────────────────────────
    llm_provider: str = "ollama"
    llm_model: str = "qwen2.5:3b"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2048
    ollama_base_url: str = "http://ollama:11434"
    embedding_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 768

    # Optional cloud provider keys (LiteLLM router)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    deepseek_api_key: str | None = None
    openrouter_api_key: str | None = None

    # ── OAuth ─────────────────────────────────────────────────
    google_client_id: str | None = None
    google_client_secret: str | None = None
    github_client_id: str | None = None
    github_client_secret: str | None = None
    microsoft_client_id: str | None = None
    microsoft_client_secret: str | None = None
    oauth_redirect_uri: str = "http://localhost:3000/auth/callback"

    # ── Email / Billing / Obs ─────────────────────────────────
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    emails_from: str = "no-reply@cortexflow.io"
    stripe_api_key: str | None = None
    stripe_webhook_secret: str | None = None
    sentry_dsn: str | None = None
    otel_exporter_otlp_endpoint: str | None = None
    log_level: str = "INFO"

    # ── Storage limits ────────────────────────────────────────
    max_upload_mb: int = 100
    chunk_size: int = 1000
    chunk_overlap: int = 150
    retrieval_top_k: int = 8
    rerank_top_k: int = 5

    @computed_field  # type: ignore[misc]
    @property
    def is_prod(self) -> bool:
        return self.env == "prod"

    @property
    def cors_origins_list(self) -> list[str]:
        if isinstance(self.cors_origins, str):
            return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return [str(o) for o in self.cors_origins]


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()  # type: ignore[call-arg]


# Default instance imported across the codebase
settings = get_settings()
