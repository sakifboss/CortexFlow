"""
Chat router.

Two surfaces:
  POST /chat/{conversation_id}        — non-streaming, returns grounded answer
  POST /chat/{conversation_id}/stream — Server-Sent Events stream of deltas + citations

Both persist the user + assistant messages, attach citation refs, and record
token usage for billing/analytics.
"""
from __future__ import annotations

import json
import time
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.contexts.document.models import Document
from app.contexts.notebook.models import Conversation, Message, MessageRole
from app.contexts.notebook.schemas import ChatRequestIn, MessageOut
from app.core.deps import DbDep, WorkspaceDep
from app.core.exceptions import NotFoundError
from app.services.audit import audit
from app.services.rag import rag

router = APIRouter(
    prefix="/workspaces/{workspace_id}/notebooks/{notebook_id}/conversations",
    tags=["chat"],
)


async def _load_conversation(db, conversation_id: uuid.UUID, workspace_id: uuid.UUID) -> Conversation:  # type: ignore[no-untyped-def]
    conv = (
        await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.workspace_id == workspace_id,
            )
        )
    ).scalar_one_or_none()
    if not conv:
        raise NotFoundError("Conversation not found")
    return conv


async def _notebook_docs(db, notebook_id: uuid.UUID) -> list[uuid.UUID]:  # type: ignore[no-untyped-def]
    res = await db.execute(select(Document.id).where(Document.notebook_id == notebook_id))
    return [r[0] for r in res.all()]


@router.post("/{conversation_id}", response_model=MessageOut)
async def chat(
    conversation_id: uuid.UUID,
    payload: ChatRequestIn,
    ws: WorkspaceDep,
    db: DbDep,
):
    conv = await _load_conversation(db, conversation_id, ws.workspace_id)
    doc_ids = await _notebook_docs(db, conv.notebook_id)

    # Persist the user turn
    user_msg = Message(
        workspace_id=ws.workspace_id,
        conversation_id=conv.id,
        role=MessageRole.USER,
        content=payload.message,
    )
    db.add(user_msg)

    result = await rag.answer(
        db,
        question=payload.message,
        workspace_id=ws.workspace_id,
        notebook_id=conv.notebook_id,
        document_ids=doc_ids or None,
        top_k=payload.retrieve_k or 8,
    )

    assistant = Message(
        workspace_id=ws.workspace_id,
        conversation_id=conv.id,
        role=MessageRole.ASSISTANT,
        content=result.answer.text,
        citations=[c.model_dump() for c in result.answer.citations],
        model=rag_model(),
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        latency_ms=result.took_ms,
    )
    db.add(assistant)
    await audit(
        db,
        action="chat.message",
        target_type="conversation",
        target_id=str(conv.id),
        payload={"tokens": result.prompt_tokens + result.completion_tokens},
    )
    return MessageOut.model_validate(assistant)


@router.post("/{conversation_id}/stream")
async def chat_stream(
    conversation_id: uuid.UUID,
    payload: ChatRequestIn,
    ws: WorkspaceDep,
    db: DbDep,
):
    conv = await _load_conversation(db, conversation_id, ws.workspace_id)
    doc_ids = await _notebook_docs(db, conv.notebook_id)

    user_msg = Message(
        workspace_id=ws.workspace_id,
        conversation_id=conv.id,
        role=MessageRole.USER,
        content=payload.message,
    )
    db.add(user_msg)
    await db.commit()

    notebook_id = conv.notebook_id
    workspace_id = ws.workspace_id

    async def event_gen():  # type: ignore[no-untyped-def]
        full_parts: list[str] = []
        citations: list[dict] = []
        took = 0
        async for ev in rag.stream_answer(
            db,
            question=payload.message,
            workspace_id=workspace_id,
            notebook_id=notebook_id,
            document_ids=doc_ids or None,
            top_k=payload.retrieve_k or 8,
        ):
            if ev["event"] == "delta":
                full_parts.append(ev["data"])
            elif ev["event"] == "done":
                citations = ev["data"].get("citations", [])
                took = ev["data"].get("took_ms", 0)
            yield f"data: {json.dumps(ev)}\n\n"

        # Persist the completed assistant message (own session to avoid conflicts)
        from app.core.db import db_session

        async with db_session() as s2:
            s2.add(
                Message(
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    role=MessageRole.ASSISTANT,
                    content="".join(full_parts),
                    citations=citations,
                    model=rag_model(),
                    latency_ms=took,
                )
            )
        yield f"data: {json.dumps({'event': 'close'})}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


def rag_model() -> str:
    from app.core.config import settings

    return settings.llm_model
