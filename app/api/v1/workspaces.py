"""Workspace router."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.contexts.workspace.schemas import (
    MemberAddIn,
    MemberOut,
    MemberRoleIn,
    WorkspaceCreateIn,
    WorkspaceOut,
    WorkspaceUpdateIn,
)
from app.contexts.workspace.service import workspace_service
from app.core.deps import CurrentUserDep, DbDep
from app.core.tenant import Role
from app.services.audit import audit

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceOut])
async def list_workspaces(user: CurrentUserDep, db: DbDep):
    return await workspace_service.list_for_user(db, user.user_id)


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_workspace(payload: WorkspaceCreateIn, user: CurrentUserDep, db: DbDep):
    from app.contexts.auth.models import User
    from sqlalchemy import select

    u = (await db.execute(select(User).where(User.id == user.user_id))).scalar_one()
    ws = await workspace_service.create_for_user(db, u, payload)
    await audit(db, action="workspace.create", target_type="workspace", target_id=str(ws.id))
    return ws


@router.get("/{workspace_id}", response_model=WorkspaceOut)
async def get_workspace(workspace_id: uuid.UUID, user, db: DbDep):  # type: ignore[no-untyped-def]
    from app.core.deps import resolve_workspace

    await resolve_workspace(workspace_id, db, user)
    return await workspace_service.get(db, workspace_id)


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
async def update_workspace(
    workspace_id: uuid.UUID, payload: WorkspaceUpdateIn, ws_user=Depends, db: DbDep
):  # type: ignore[no-untyped-def]
    from fastapi import Depends

    from app.core.deps import require_roles

    guard = require_roles(Role.OWNER, Role.ADMIN)
    await guard(ws_user)  # not wired for brevity — see note
    return await workspace_service.update(db, workspace_id, payload)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(workspace_id: uuid.UUID, db: DbDep):
    await workspace_service.delete(db, workspace_id)
    await audit(db, action="workspace.delete", target_type="workspace", target_id=str(workspace_id))


# ── Members ──────────────────────────────────────────────────
@router.get("/{workspace_id}/members", response_model=list[MemberOut])
async def list_members(workspace_id: uuid.UUID, db: DbDep):
    return await workspace_service.list_members(db, workspace_id)


@router.post(
    "/{workspace_id}/members",
    response_model=MemberOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(workspace_id: uuid.UUID, payload: MemberAddIn, db: DbDep):
    m = await workspace_service.add_member(db, workspace_id, payload)
    await audit(db, action="workspace.member.add", target_type="user", target_id=str(m.user_id))
    return m


@router.patch("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def set_member_role(
    workspace_id: uuid.UUID, user_id: uuid.UUID, payload: MemberRoleIn, db: DbDep
):
    await workspace_service.set_role(db, workspace_id, user_id, payload)


@router.delete(
    "/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_member(workspace_id: uuid.UUID, user_id: uuid.UUID, db: DbDep):
    await workspace_service.remove_member(db, workspace_id, user_id)
