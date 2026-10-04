"""
Memory router.

Exposes the Agent Memory System: write memories, recall them with blended
similarity/importance/recency scoring, run consolidation, and forget decayed
memories. All routes are workspace-scoped and RBAC-guarded via WorkspaceDep.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.contexts.memory.models import MemoryLayer
from app.contexts.memory.schemas import (
    ConsolidateIn,
    ConsolidateOut,
    ForgetIn,
    ForgetOut,
    MemoryOut,
    MemoryRecallIn,
    MemoryWriteIn,
    RecallOut,
)
from app.contexts.memory.service import memory_service
from app.core.deps import DbDep, WorkspaceDep
from app.core.exceptions import NotFoundError
from app.services.audit import audit

router = APIRouter(prefix="/workspaces/{workspace_id}/memory", tags=["memory"])


@router.get("", response_model=list[MemoryOut])
async def list_memories(
    ws: WorkspaceDep,
    db: DbDep,
    layer: MemoryLayer | None = Query(default=None),
    notebook_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    return await memory_service.list_memories(
        db,
        workspace_id=ws.workspace_id,
        layer=layer,
        notebook_id=notebook_id,
        limit=limit,
    )


@router.post("", response_model=MemoryOut, status_code=status.HTTP_201_CREATED)
async def write_memory(ws: WorkspaceDep, db: DbDep, payload: MemoryWriteIn):
    mem = await memory_service.write(
        db, workspace_id=ws.workspace_id, user_id=ws.user_id, payload=payload
    )
    await audit(db, action="memory.write", target_type="memory", target_id=str(mem.id))
    return mem


@router.post("/recall", response_model=RecallOut)
async def recall_memory(ws: WorkspaceDep, db: DbDep, payload: MemoryRecallIn):
    return await memory_service.recall(db, workspace_id=ws.workspace_id, payload=payload)


@router.post("/consolidate", response_model=ConsolidateOut)
async def consolidate_memory(ws: WorkspaceDep, db: DbDep, payload: ConsolidateIn):
    out = await memory_service.consolidate(
        db, workspace_id=ws.workspace_id, user_id=ws.user_id, payload=payload
    )
    await audit(
        db,
        action="memory.consolidate",
        target_type="workspace",
        target_id=str(ws.workspace_id),
    )
    return out


@router.post("/forget", response_model=ForgetOut)
async def forget_memory(ws: WorkspaceDep, db: DbDep, payload: ForgetIn):
    out = await memory_service.forget(db, workspace_id=ws.workspace_id, payload=payload)
    if not payload.dry_run:
        await audit(
            db,
            action="memory.forget",
            target_type="workspace",
            target_id=str(ws.workspace_id),
        )
    return out


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(memory_id: uuid.UUID, ws: WorkspaceDep, db: DbDep):
    ok = await memory_service.delete(
        db, workspace_id=ws.workspace_id, memory_id=memory_id
    )
    if not ok:
        raise NotFoundError("Memory not found")
    await audit(
        db, action="memory.delete", target_type="memory", target_id=str(memory_id)
    )
