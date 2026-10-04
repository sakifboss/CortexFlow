"""
Structured logging via loguru with a JSON sink for production.

Usage:
    from app.core.logging import get_logger
    log = get_logger(__name__)
    log.info("event", extra={"user_id": ..., "workspace_id": ...})
"""
from __future__ import annotations

import sys

from loguru import logger

from app.core.config import settings


def configure_logging() -> None:
    logger.remove()
    fmt_json = (
        '{{"ts":"{time:YYYY-MM-DDTHH:mm:ss.SSSZ}",'
        '"level":"{level}",'
        '"logger":"{name}",'
        '"message":"{message}"}}'
    )
    fmt_pretty = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    if settings.is_prod:
        logger.add(sys.stdout, level=settings.log_level, format=fmt_json, serialize=True)
    else:
        logger.add(sys.stdout, level=settings.log_level, colorize=True, format=fmt_pretty, backtrace=True, diagnose=True)

    if settings.sentry_dsn:
        try:
            import sentry_sdk
            sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.env, traces_sample_rate=0.1)
        except Exception:  # pragma: no cover - sentry optional
            pass


def get_logger(name: str | None = None):
    return logger.bind(name=name or "app")
