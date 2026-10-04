"""Notebooks router."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.contexts.notebook.schemas import (
    ConversationCreateIn,
    ConversationOut,
    MessageOut,
    NotebookCreateIn,
    NotebookOut,
    NotebookUpdateIn,
)
from app.contexts.notebook.service import notebook_service
from app.core.deps import DbDep, WorkspaceDep
from app.core.tenant import Role
from app.services.audit import audit

router = APIRouter(prefix="/workspaces/{workspace_id}/notebooks", tags=["notebooks"])


@router.get("", response_model=list[NotebookOut])
async def list_notebooks(ws: WorkspaceDep, db: DbDep):
    return await notebook_service.list(db, workspace_id=ws.workspace_id)


@router.post("", response_model=NotebookOut, status_code=status.HTTP_201_CREATED)
async def create_notebook(payload: NotebookCreateIn, ws: WorkspaceDep, db: DbDep):
    nb = await notebook_service.create(
        db, workspace_id=ws.workspace_id, owner_id=ws.user_id, payload=payload
    )
    await audit(db, action="notebook.create", target_type="notebook", target_id=str(nb.id))
    return nb


@router.get("/{notebook_id}", response_model=NotebookOut)
async def get_notebook(notebook_id: uuid.UUID, ws: WorkspaceDep, db: DbDep):
    return await notebook_service.get_out(db, notebook_id)


@router.patch("/{notebook_id}", response_model=NotebookOut)
async def update_notebook(
    notebook_id: uuid.UUID, payload: NotebookUpdateIn, ws: WorkspaceDep, db: DbDep
):
    return await notebook_service.update(db, notebook_id, payload)


@router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notebook(notebook_id: uuid.UUID, ws: WorkspaceDep, db: DbDep):
    await notebook_service.delete(db, notebook_id)
    await audit(db, action="notebook.delete", target_type="notebook", target_id=str(notebook_id))


# ── Conversations ────────────────────────────────────────────
@router.get("/{notebook_id}/conversations", response_model=list[ConversationOut])
async def list_conversations(notebook_id: uuid.UUID, ws: WorkspaceDep, db: DbDep):
    return await notebook_service.list_conversations(db, notebook_id=notebook_id)


@router.post(
    "/{notebook_id}/conversations",
    response_model=ConversationOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    notebook_id: uuid.UUID, payload: ConversationCreateIn, ws: WorkspaceDep, db: DbDep
):
    return await notebook_service.create_conversation(
        db,
        workspace_id=ws.workspace_id,
        notebook_id=notebook_id,
        user_id=ws.user_id,
        payload=payload,
    )


@router.get("/{notebook_id}/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(conversation_id: uuid.UUID, ws: WorkspaceDep, db: DbDep):
    msgs = await notebook_service.list_messages(db, conversation_id)
    return [MessageOut.model_validate(m) for m in msgs]
