"""Notebook schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.contexts.notebook.models import MessageRole
from app.schemas import IDModel, ORMModel, Timestamped


class NotebookCreateIn(ORMModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    emoji: str | None = None
    color: str | None = None
    folder_id: uuid.UUID | None = None


class NotebookUpdateIn(ORMModel):
    title: str | None = None
    description: str | None = None
    emoji: str | None = None
    color: str | None = None
    is_archived: bool | None = None


class NotebookOut(IDModel, Timestamped):
    workspace_id: uuid.UUID
    title: str
    description: str | None
    emoji: str | None
    color: str | None
    owner_id: uuid.UUID
    folder_id: uuid.UUID | None
    is_archived: bool
    document_count: int | None = None
    conversation_count: int | None = None


# ── Conversations / messages ─────────────────────────────────
class ConversationCreateIn(ORMModel):
    title: str | None = None
    agent: str = "research"


class ConversationOut(IDModel, Timestamped):
    workspace_id: uuid.UUID
    notebook_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    agent: str
    pinned: bool
    last_message_at: datetime | None = None
    message_count: int | None = None


class MessageOut(IDModel, Timestamped):
    conversation_id: uuid.UUID
    role: MessageRole
    content: str
    citations: list | None = None
    tool_calls: list | None = None
    model: str | None = None
    latency_ms: int | None = None


class ChatRequestIn(ORMModel):
    """Send a user turn to the RAG agent for a conversation."""

    message: str = Field(min_length=1)
    agent: str = "research"
    retrieve_k: int | None = None
    use_graph: bool = False
    use_memory: bool = True
    stream: bool = True
