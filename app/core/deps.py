"""
FastAPI dependencies: settings, DB session, JWT auth, OAuth scheme,
workspace resolution, RBAC guards, and rate-limiting primitives.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Callable
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.redis import get_redis
from app.core.security import decode_token
from app.core.tenant import CurrentUser, Role, set_current_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_settings_dep() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


# ── Auth ─────────────────────────────────────────────────────
async def get_current_user(
    db: DbDep,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    settings: SettingsDep,
) -> CurrentUser:
    """Validate JWT and load the request-scoped CurrentUser context."""
    from app.contexts.auth.models import User  # local import to avoid cycle

    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exc

    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise credentials_exc

    if payload.get("type") != "access":
        raise credentials_exc

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exc

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id), User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exc

    current = CurrentUser(
        user_id=user.id,
        email=user.email,
        org_id=user.org_id,
        workspace_id=None,  # resolved by WorkspaceDep
        role=Role.MEMBER,
        is_superuser=user.is_superuser,
        scopes=tuple(payload.get("scopes", [])),
    )
    set_current_user(current)
    return current


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


# ── Workspace resolution & RBAC ──────────────────────────────
async def resolve_workspace(
    workspace_id: Annotated[uuid.UUID, Query()],
    db: DbDep,
    user: CurrentUserDep,
) -> CurrentUser:
    """Verify the user is a member of the workspace; set role."""
    from app.contexts.workspace.models import WorkspaceMember

    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    updated = CurrentUser(
        user_id=user.user_id,
        email=user.email,
        org_id=user.org_id,
        workspace_id=workspace_id,
        role=Role(membership.role),
        is_superuser=user.is_superuser,
        scopes=user.scopes,
    )
    set_current_user(updated)
    return updated


WorkspaceDep = Annotated[CurrentUser, Depends(resolve_workspace)]


def require_roles(*roles: Role) -> Callable:
    """Dependency factory enforcing one of the given roles."""

    async def _guard(user: WorkspaceDep) -> CurrentUser:
        if user.is_superuser:
            return user
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return _guard


# ── Rate limiting (token bucket via Redis) ───────────────────
async def rate_limit(key: str, limit: int, window_s: int) -> bool:
    """Return True if request is allowed, False if rate-limited."""
    redis = get_redis()
    bucket = f"rl:{key}"
    count = await redis.incr(bucket)
    if count == 1:
        await redis.expire(bucket, window_s)
    return count <= limit
