"""Seed an admin user + a demo workspace + demo notebook (idempotent)."""
from __future__ import annotations

import asyncio
import os
import uuid

from sqlalchemy import select

from app.contexts.auth.models import AuthProvider, User
from app.contexts.auth.service import auth_service
from app.contexts.auth.schemas import RegisterIn
from app.contexts.notebook.service import notebook_service
from app.contexts.notebook.schemas import NotebookCreateIn
from app.contexts.workspace.service import workspace_service
from app.contexts.workspace.schemas import WorkspaceCreateIn
from app.core.db import db_session
from app.core.security import hash_password
from app.services.storage import storage


async def main() -> None:
    storage.ensure_bucket()
    admin_email = os.getenv("SEED_ADMIN_EMAIL", "admin@cortexflow.io")
    admin_password = os.getenv("SEED_ADMIN_PASSWORD", "changeme123")

    async with db_session() as db:
        existing = (
            await db.execute(select(User).where(User.email == admin_email))
        ).scalar_one_or_none()
        if existing:
            print(f"[skip] admin already exists: {admin_email}")
            return

        admin = User(
            email=admin_email,
            full_name="Admin",
            hashed_password=hash_password(admin_password),
            provider=AuthProvider.EMAIL,
            is_active=True,
            is_verified=True,
            is_superuser=True,
        )
        db.add(admin)
        await db.flush()

        ws = await workspace_service.create_for_user(
            db, admin, WorkspaceCreateIn(name="Demo Workspace", description="Seed workspace")
        )
        await notebook_service.create(
            db,
            workspace_id=ws.id,
            owner_id=admin.id,
            payload=NotebookCreateIn(title="Welcome to CortexFlow", emoji="🧠"),
        )
        print(f"[ok] seeded admin={admin_email} password={admin_password}")
        print(f"[ok] workspace={ws.slug} id={ws.id}")


if __name__ == "__main__":
    asyncio.run(main())
