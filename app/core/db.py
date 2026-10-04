"""
Async SQLAlchemy 2.x engine, session factory, and Base.

Sessions are request-scoped via `get_db` (FastAPI dependency). Every session
automatically sets the tenant context via `app.core.tenant.set_tenant_context`
when a current user is present, enforcing multi-tenant isolation at the ORM layer.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass

from app.core.config import settings


class Base(MappedAsDataclass, DeclarativeBase, kw_only=True):
    """
    Declarative base shared by all ORM models.

    ``kw_only=True`` makes every mapped column a keyword-only dataclass field.
    This is required because tenant-scoped models compose plain (non-dataclass)
    mixins — ``UUIDPK``/``TimestampMixin`` supply defaulted columns while
    ``TenantMixin.workspace_id`` has none. Without kw_only, SQLAlchemy's
    dataclass transform raises "non-default argument follows default argument"
    on newer 2.0.x releases. Keyword-only fields sidestep positional ordering
    entirely and keep model construction explicit (Memory(workspace_id=...)).
    """


engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    echo=settings.db_echo,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency — yields a scoped async session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def db_session() -> AsyncIterator[AsyncSession]:
    """Context manager variant for use outside FastAPI (workers, scripts)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
