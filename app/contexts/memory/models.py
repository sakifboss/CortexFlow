"""
Memory context (Phase 3).

Implements a layered memory system:
  - working:  current turn's scratchpad
  - episodic: past events/interactions (time-indexed)
  - semantic: distilled facts (concept-indexed)
  - procedural: skills/how-to patterns
  - long_term: consolidated high-importance memories

Each memory is embedded for similarity retrieval. Importance decays over time;
low-importance memories are forgotten on a consolidation schedule.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.models import TenantMixin, TimestampMixin, UUIDPK


class MemoryLayer(str, enum.Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    LONG_TERM = "long_term"


class Memory(Base, UUIDPK, TimestampMixin, TenantMixin):
    __tablename__ = "memories"
    __table_args__ = (Index("ix_mem_ws_layer", "workspace_id", "layer"),)

    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None, index=True)
    notebook_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None, index=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)

    layer: Mapped[MemoryLayer] = mapped_column(Enum(MemoryLayer, name="memory_layer"))
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text, default=None)
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed_at: Mapped[str | None] = mapped_column(String(40), default=None)
    embedding_id: Mapped[str | None] = mapped_column(String(64), default=None)
    embedding_model: Mapped[str | None] = mapped_column(String(120), default=None)
    decay_rate: Mapped[float] = mapped_column(Float, default=0.01)
    properties: Mapped[dict | None] = mapped_column(JSONB, default=None)


class MemoryCluster(Base, UUIDPK, TimestampMixin, TenantMixin):
    """Semantic cluster produced by consolidation (memories → clusters)."""

    __tablename__ = "memory_clusters"

    centroid_memory_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    member_ids: Mapped[list] = mapped_column(JSONB, default=list)
    label: Mapped[str | None] = mapped_column(String(200), default=None)
