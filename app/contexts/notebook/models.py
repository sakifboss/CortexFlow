"""Notebook context — notebooks, conversations, messages, notes, highlights."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.models import TenantMixin, TimestampMixin, UUIDPK
from app.contexts.workspace.models import Workspace


class Notebook(Base, UUIDPK, TimestampMixin, TenantMixin):
    __tablename__ = "notebooks"

    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    emoji: Mapped[str | None] = mapped_column(String(16), default=None)
    color: Mapped[str | None] = mapped_column(String(16), default=None)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    folder_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    is_archived: Mapped[bool] = mapped_column(default=False)

    workspace: Mapped[Workspace] = relationship()
    documents: Mapped[list["Document"]] = relationship(  # noqa: F821
        back_populates="notebook", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="notebook", cascade="all, delete-orphan"
    )


class Conversation(Base, UUIDPK, TimestampMixin, TenantMixin):
    __tablename__ = "conversations"

    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="New conversation")
    agent: Mapped[str] = mapped_column(String(60), default="research")
    pinned: Mapped[bool] = mapped_column(default=False)

    notebook: Mapped[Notebook] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class MessageRole(str, enum.Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(Base, UUIDPK, TimestampMixin, TenantMixin):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_msg_conv_created", "conversation_id", "created_at"),)

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole, name="message_role"))
    content: Mapped[str] = mapped_column(Text)
    # Structured citations attached to assistant messages: list of CitationRef
    citations: Mapped[list | None] = mapped_column(JSONB, default=None)
    # Tool-call metadata (used by agents)
    tool_calls: Mapped[list | None] = mapped_column(JSONB, default=None)
    # Token accounting
    prompt_tokens: Mapped[int | None] = mapped_column(default=None)
    completion_tokens: Mapped[int | None] = mapped_column(default=None)
    model: Mapped[str | None] = mapped_column(String(80), default=None)
    # Latency in ms
    latency_ms: Mapped[int | None] = mapped_column(default=None)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Note(Base, UUIDPK, TimestampMixin, TenantMixin):
    __tablename__ = "notes"

    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200), default="Untitled")
    body: Mapped[str] = mapped_column(Text, default="")
    # Backlinks stored as note IDs for the bidirectional note graph
    backlinks: Mapped[list | None] = mapped_column(JSONB, default=None)
    tags: Mapped[list | None] = mapped_column(JSONB, default=None)


class Highlight(Base, UUIDPK, TimestampMixin, TenantMixin):
    """A user highlight on a specific document chunk/span."""

    __tablename__ = "highlights"

    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    color: Mapped[str] = mapped_column(String(16), default="yellow")
    note: Mapped[str | None] = mapped_column(Text, default=None)
