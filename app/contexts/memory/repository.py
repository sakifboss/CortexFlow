"""
Memory repository — async SQLAlchemy data-access layer.

Pure persistence: no business logic, no embedding, no scoring. The service
composes these calls. All queries are tenant-scoped via workspace_id.
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.memory.models import Memory, MemoryCluster, MemoryLayer


class MemoryRepository:
    async def create(self, db: AsyncSession, memory: Memory) -> Memory:
        db.add(memory)
        await db.flush()
        await db.refresh(memory)
        return memory

    async def get(
        self, db: AsyncSession, memory_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> Memory | None:
        result = await db.execute(
            select(Memory).where(
                Memory.id == memory_id, Memory.workspace_id == workspace_id
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        db: AsyncSession,
        *,
        workspace_id: uuid.UUID,
        layers: Sequence[MemoryLayer] | None = None,
        notebook_id: uuid.UUID | None = None,
        conversation_id: uuid.UUID | None = None,
        limit: int = 500,
    ) -> list[Memory]:
        stmt = select(Memory).where(Memory.workspace_id == workspace_id)
        if layers:
            stmt = stmt.where(Memory.layer.in_(list(layers)))
        if notebook_id is not None:
            stmt = stmt.where(Memory.notebook_id == notebook_id)
        if conversation_id is not None:
            stmt = stmt.where(Memory.conversation_id == conversation_id)
        stmt = stmt.order_by(Memory.created_at.desc()).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def fetch_by_ids(
        self, db: AsyncSession, ids: Sequence[uuid.UUID], workspace_id: uuid.UUID
    ) -> list[Memory]:
        if not ids:
            return []
        result = await db.execute(
            select(Memory).where(
                Memory.id.in_(list(ids)), Memory.workspace_id == workspace_id
            )
        )
        return list(result.scalars().all())

    async def update_fields(
        self, db: AsyncSession, memory_id: uuid.UUID, **fields
    ) -> None:
        if not fields:
            return
        await db.execute(
            update(Memory).where(Memory.id == memory_id).values(**fields)
        )

    async def bump_access(
        self, db: AsyncSession, ids: Sequence[uuid.UUID], when: str
    ) -> None:
        """Increment access_count and set last_accessed_at for recalled memories."""
        if not ids:
            return
        await db.execute(
            update(Memory)
            .where(Memory.id.in_(list(ids)))
            .values(access_count=Memory.access_count + 1, last_accessed_at=when)
        )

    async def delete_ids(
        self, db: AsyncSession, ids: Sequence[uuid.UUID], workspace_id: uuid.UUID
    ) -> int:
        if not ids:
            return 0
        result = await db.execute(
            delete(Memory).where(
                Memory.id.in_(list(ids)), Memory.workspace_id == workspace_id
            )
        )
        return int(result.rowcount or 0)

    # ── Clusters ─────────────────────────────────────────────
    async def create_cluster(
        self, db: AsyncSession, cluster: MemoryCluster
    ) -> MemoryCluster:
        db.add(cluster)
        await db.flush()
        await db.refresh(cluster)
        return cluster


memory_repository = MemoryRepository()
