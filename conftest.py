"""Pytest bootstrap: set required env vars before any app import."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Minimal settings so app.core.config.Settings() validates during import.
# These point at nothing real — the memory tests never touch DB/Redis/Celery.
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-use-only")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/1")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
