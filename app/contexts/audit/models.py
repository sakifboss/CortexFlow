"""Audit log — append-only event stream for compliance & security reviews."""
from __future__ import annotations

import uuid

from sqlalchemy import Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.models import TimestampMixin, UUIDPK


class AuditEvent(Base, UUIDPK, TimestampMixin):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_ws_action", "workspace_id", "action"),)

    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None, index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None, index=True)
    actor_email: Mapped[str | None] = mapped_column(String(255), default=None)
    action: Mapped[str] = mapped_column(String(80))  # e.g. document.upload, user.login
    target_type: Mapped[str | None] = mapped_column(String(80), default=None)
    target_id: Mapped[str | None] = mapped_column(String(64), default=None)
    ip: Mapped[str | None] = mapped_column(String(64), default=None)
    user_agent: Mapped[str | None] = mapped_column(String(255), default=None)
    summary: Mapped[str | None] = mapped_column(Text, default=None)
    payload: Mapped[dict | None] = mapped_column(JSONB, default=None)
