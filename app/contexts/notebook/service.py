"""Notebook service — CRUD, conversations, messages."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.document.models import Document
from app.contexts.notebook.models import Conversation, Message, Notebook
from app.contexts.notebook.schemas import (
    ConversationCreateIn,
    ConversationOut,
    NotebookCreateIn,
    NotebookOut,
    NotebookUpdateIn,
)
from app.core.exceptions import NotFoundError


class NotebookService:
    async def create(
        self,
        db: AsyncSession,
        *,
        workspace_id: uuid.UUID,
        owner_id: uuid.UUID,
        payload: NotebookCreateIn,
    ) -> NotebookOut:
        nb = Notebook(
            workspace_id=workspace_id,
            owner_id=owner_id,
            title=payload.title,
            description=payload.description,
            emoji=payload.emoji,
            color=payload.color,
            folder_id=payload.folder_id,
        )
        db.add(nb)
        await db.flush()
        return await self._to_out(db, nb)

    async def list(
        self, db: AsyncSession, *, workspace_id: uuid.UUID, include_archived: bool = False
    ) -> list[NotebookOut]:
        q = select(Notebook).where(Notebook.workspace_id == workspace_id)
        if not include_archived:
            q = q.where(Notebook.is_archived.is_(False))
        q = q.order_by(Notebook.updated_at.desc())
        out = []
        for nb in (await db.execute(q)).scalars():
            out.append(await self._to_out(db, nb))
        return out

    async def get(self, db: AsyncSession, notebook_id: uuid.UUID) -> Notebook:
        nb = (
            await db.execute(select(Notebook).where(Notebook.id == notebook_id))
        ).scalar_one_or_none()
        if not nb:
            raise NotFoundError("Notebook not found")
        return nb

    async def get_out(self, db: AsyncSession, notebook_id: uuid.UUID) -> NotebookOut:
        return await self._to_out(db, await self.get(db, notebook_id))

    async def update(
        self, db: AsyncSession, notebook_id: uuid.UUID, payload: NotebookUpdateIn
    ) -> NotebookOut:
        nb = await self.get(db, notebook_id)
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(nb, k, v)
        return await self._to_out(db, nb)

    async def delete(self, db: AsyncSession, notebook_id: uuid.UUID) -> None:
        nb = await self.get(db, notebook_id)
        await db.delete(nb)

    # ── Conversations ────────────────────────────────────────
    async def create_conversation(
        self,
        db: AsyncSession,
        *,
        workspace_id: uuid.UUID,
        notebook_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: ConversationCreateIn,
    ) -> ConversationOut:
        conv = Conversation(
            workspace_id=workspace_id,
            notebook_id=notebook_id,
            user_id=user_id,
            title=payload.title or "New conversation",
            agent=payload.agent,
        )
        db.add(conv)
        await db.flush()
        return ConversationOut(
            id=conv.id,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            workspace_id=conv.workspace_id,
            notebook_id=conv.notebook_id,
            user_id=conv.user_id,
            title=conv.title,
            agent=conv.agent,
            pinned=conv.pinned,
            message_count=0,
        )

    async def list_conversations(
        self, db: AsyncSession, *, notebook_id: uuid.UUID
    ) -> list[ConversationOut]:
        res = await db.execute(
            select(Conversation)
            .where(Conversation.notebook_id == notebook_id)
            .order_by(Conversation.updated_at.desc())
        )
        out = []
        for c in res.scalars():
            msg_count = (
                await db.execute(
                    select(func.count()).select_from(Message).where(Message.conversation_id == c.id)
                )
            ).scalar_one()
            out.append(
                ConversationOut(
                    id=c.id,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                    workspace_id=c.workspace_id,
                    notebook_id=c.notebook_id,
                    user_id=c.user_id,
                    title=c.title,
                    agent=c.agent,
                    pinned=c.pinned,
                    message_count=int(msg_count or 0),
                )
            )
        return out

    async def list_messages(
        self, db: AsyncSession, conversation_id: uuid.UUID
    ) -> list[Message]:
        res = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        return list(res.scalars())

    async def _to_out(self, db: AsyncSession, nb: Notebook) -> NotebookOut:
        doc_count = (
            await db.execute(
                select(func.count()).select_from(Document).where(Document.notebook_id == nb.id)
            )
        ).scalar_one()
        conv_count = (
            await db.execute(
                select(func.count()).select_from(Conversation).where(Conversation.notebook_id == nb.id)
            )
        ).scalar_one()
        return NotebookOut(
            id=nb.id,
            created_at=nb.created_at,
            updated_at=nb.updated_at,
            workspace_id=nb.workspace_id,
            title=nb.title,
            description=nb.description,
            emoji=nb.emoji,
            color=nb.color,
            owner_id=nb.owner_id,
            folder_id=nb.folder_id,
            is_archived=nb.is_archived,
            document_count=int(doc_count or 0),
            conversation_count=int(conv_count or 0),
        )


notebook_service = NotebookService()
