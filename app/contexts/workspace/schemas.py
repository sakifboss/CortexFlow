"""Workspace schemas."""
from __future__ import annotations

import uuid

from pydantic import Field

from app.contexts.workspace.models import WorkspaceRole
from app.schemas import IDModel, ORMModel, Timestamped


class WorkspaceCreateIn(ORMModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=120)
    description: str | None = None


class WorkspaceUpdateIn(ORMModel):
    name: str | None = None
    description: str | None = None
    settings: dict | None = None


class WorkspaceOut(IDModel, Timestamped):
    name: str
    slug: str
    description: str | None
    owner_id: uuid.UUID
    plan: str
    settings: dict | None
    member_count: int | None = None


class MemberOut(IDModel, Timestamped):
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    role: WorkspaceRole
    email: str | None = None
    full_name: str | None = None


class MemberAddIn(ORMModel):
    email: str
    role: WorkspaceRole = WorkspaceRole.MEMBER


class MemberRoleIn(ORMModel):
    role: WorkspaceRole


class InviteCreateIn(ORMModel):
    email: str
    role: WorkspaceRole = WorkspaceRole.MEMBER
