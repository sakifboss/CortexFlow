"""
Shared SQLAlchemy mixins: UUID primary key, timestamps, soft-delete, and
tenant scoping. All context models compose these.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class UUIDPK:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.utcnow()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.utcnow(),
        onupdate=func.now(),
    )


class TenantMixin:
    """Every tenant-scoped row carries a non-null workspace_id."""

    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )


class MetadataMixin:
    """Free-form JSON metadata column for extensibility."""

    meta: Mapped[dict | None] = mapped_column(default=None)
