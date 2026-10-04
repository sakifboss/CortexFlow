"""Audit helper — fire-and-forget audit event writes."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.audit.models import AuditEvent
from app.core.logging import get_logger
from app.core.tenant import get_current_user

log = get_logger(__name__)


async def audit(
    db: AsyncSession,
    *,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    summary: str | None = None,
    payload: dict[str, Any] | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    user = get_current_user()
    event = AuditEvent(
        workspace_id=user.workspace_id if user else None,
        actor_id=user.user_id if user else None,
        actor_email=user.email if user else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        summary=summary,
        payload=payload,
        ip=ip,
        user_agent=user_agent,
    )
    db.add(event)
    await db.flush()
