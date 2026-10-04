"""Workspace service — CRUD, membership, roles, folders/tags."""
from __future__ import annotations

import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.auth.models import User
from app.contexts.workspace.models import (
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)
from app.contexts.workspace.schemas import (
    MemberAddIn,
    MemberOut,
    MemberRoleIn,
    WorkspaceCreateIn,
    WorkspaceOut,
    WorkspaceUpdateIn,
)
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "workspace"


class WorkspaceService:
    async def create_for_user(
        self, db: AsyncSession, user: User, payload: WorkspaceCreateIn
    ) -> WorkspaceOut:
        slug = payload.slug or _slugify(payload.name)
        if await self._exists_slug(db, slug):
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"
        ws = Workspace(
            name=payload.name,
            slug=slug,
            description=payload.description,
            owner_id=user.id,
            org_id=user.org_id,
            settings={},
        )
        db.add(ws)
        await db.flush()
        db.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=WorkspaceRole.OWNER))
        await db.flush()
        return await self._to_out(db, ws)

    async def list_for_user(self, db: AsyncSession, user_id: uuid.UUID) -> list[WorkspaceOut]:
        res = await db.execute(
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.created_at.desc())
        )
        out = []
        for ws in res.scalars():
            out.append(await self._to_out(db, ws))
        return out

    async def get(self, db: AsyncSession, workspace_id: uuid.UUID) -> WorkspaceOut:
        ws = await self._require(db, workspace_id)
        return await self._to_out(db, ws)

    async def update(
        self, db: AsyncSession, workspace_id: uuid.UUID, payload: WorkspaceUpdateIn
    ) -> WorkspaceOut:
        ws = await self._require(db, workspace_id)
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(ws, k, v)
        return await self._to_out(db, ws)

    async def delete(self, db: AsyncSession, workspace_id: uuid.UUID) -> None:
        ws = await self._require(db, workspace_id)
        await db.delete(ws)

    # ── Members ──────────────────────────────────────────────
    async def list_members(self, db: AsyncSession, workspace_id: uuid.UUID) -> list[MemberOut]:
        res = await db.execute(
            select(WorkspaceMember, User)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.created_at)
        )
        return [
            MemberOut(
                id=m.id,
                created_at=m.created_at,
                updated_at=m.updated_at,
                workspace_id=m.workspace_id,
                user_id=m.user_id,
                role=m.role,
                email=u.email,
                full_name=u.full_name,
            )
            for m, u in res.all()
        ]

    async def add_member(
        self, db: AsyncSession, workspace_id: uuid.UUID, payload: MemberAddIn
    ) -> MemberOut:
        user = (
            await db.execute(select(User).where(User.email == payload.email.lower()))
        ).scalar_one_or_none()
        if not user:
            raise NotFoundError("User not found by email")
        existing = (
            await db.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id == user.id,
                )
            )
        ).scalar_one_or_none()
        if existing:
            raise ConflictError("User already a member")
        m = WorkspaceMember(workspace_id=workspace_id, user_id=user.id, role=payload.role)
        db.add(m)
        await db.flush()
        return MemberOut(
            id=m.id,
            created_at=m.created_at,
            updated_at=m.updated_at,
            workspace_id=m.workspace_id,
            user_id=m.user_id,
            role=m.role,
            email=user.email,
            full_name=user.full_name,
        )

    async def set_role(
        self, db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID, payload: MemberRoleIn
    ) -> None:
        m = await self._require_member(db, workspace_id, user_id)
        if m.role == WorkspaceRole.OWNER:
            raise ForbiddenError("Cannot change owner role")
        m.role = payload.role

    async def remove_member(self, db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
        m = await self._require_member(db, workspace_id, user_id)
        if m.role == WorkspaceRole.OWNER:
            raise ForbiddenError("Cannot remove owner")
        await db.delete(m)

    # ── internals ────────────────────────────────────────────
    async def _to_out(self, db: AsyncSession, ws: Workspace) -> WorkspaceOut:
        count = (
            await db.execute(
                select(func.count())
                .select_from(WorkspaceMember)
                .where(WorkspaceMember.workspace_id == ws.id)
            )
        ).scalar_one()
        return WorkspaceOut(
            id=ws.id,
            created_at=ws.created_at,
            updated_at=ws.updated_at,
            name=ws.name,
            slug=ws.slug,
            description=ws.description,
            owner_id=ws.owner_id,
            plan=ws.plan,
            settings=ws.settings,
            member_count=int(count or 0),
        )

    async def _require(self, db: AsyncSession, workspace_id: uuid.UUID) -> Workspace:
        ws = (
            await db.execute(select(Workspace).where(Workspace.id == workspace_id))
        ).scalar_one_or_none()
        if not ws:
            raise NotFoundError("Workspace not found")
        return ws

    async def _require_member(
        self, db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkspaceMember:
        m = (
            await db.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if not m:
            raise NotFoundError("Member not found")
        return m

    async def _exists_slug(self, db: AsyncSession, slug: str) -> bool:
        return (
            await db.execute(select(Workspace).where(Workspace.slug == slug))
        ).scalar_one_or_none() is not None


workspace_service = WorkspaceService()
