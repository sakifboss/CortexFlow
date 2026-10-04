"""
Per-request tenant context.

Provides a contextvar-based container for the active user, workspace, and
role. Repositories and services read from it to enforce multi-tenant
isolation (e.g. every query is automatically scoped by workspace_id).
"""
from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"
    MEMBER = "member"


@dataclass(slots=True)
class CurrentUser:
    """Identity propagated through the request lifecycle."""

    user_id: uuid.UUID
    email: str
    org_id: uuid.UUID | None = None
    workspace_id: uuid.UUID | None = None
    role: Role = Role.MEMBER
    is_superuser: bool = False
    scopes: tuple[str, ...] = ()


_current: ContextVar[CurrentUser | None] = ContextVar("current_user", default=None)


def set_current_user(user: CurrentUser | None) -> None:
    _current.set(user)


def get_current_user() -> CurrentUser | None:
    return _current.get()


def require_current_user() -> CurrentUser:
    user = _current.get()
    if user is None:
        raise RuntimeError("No current user in context — auth dependency missing.")
    return user
