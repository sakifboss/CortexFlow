"""Memory context schemas (Pydantic v2)."""
from __future__ import annotations

import uuid

from pydantic import Field

from app.contexts.memory.models import MemoryLayer
from app.schemas import IDModel, ORMModel, Timestamped


# ── Requests ─────────────────────────────────────────────────
class MemoryWriteIn(ORMModel):
    content: str = Field(min_length=1, max_length=20_000)
    layer: MemoryLayer = MemoryLayer.EPISODIC
    summary: str | None = Field(default=None, max_length=2_000)
    importance: float | None = Field(default=None, ge=0.0, le=1.0)
    notebook_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    properties: dict | None = None


class MemoryUpdateIn(ORMModel):
    content: str | None = Field(default=None, max_length=20_000)
    summary: str | None = Field(default=None, max_length=2_000)
    importance: float | None = Field(default=None, ge=0.0, le=1.0)
    layer: MemoryLayer | None = None
    properties: dict | None = None


class MemoryRecallIn(ORMModel):
    """Similarity + importance weighted recall query."""

    query: str = Field(min_length=1, max_length=4_000)
    layers: list[MemoryLayer] | None = None
    notebook_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    limit: int = Field(default=8, ge=1, le=50)
    min_importance: float = Field(default=0.0, ge=0.0, le=1.0)


class ConsolidateIn(ORMModel):
    """Trigger a consolidation pass over a scope."""

    notebook_id: uuid.UUID | None = None
    layer: MemoryLayer = MemoryLayer.EPISODIC
    max_cluster_distance: float = Field(default=0.35, ge=0.05, le=0.9)
    promote_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class ForgetIn(ORMModel):
    """Prune low-importance / decayed memories."""

    notebook_id: uuid.UUID | None = None
    layer: MemoryLayer | None = None
    importance_floor: float = Field(default=0.15, ge=0.0, le=1.0)
    dry_run: bool = True


# ── Responses ────────────────────────────────────────────────
class MemoryOut(IDModel, Timestamped):
    layer: MemoryLayer
    content: str
    summary: str | None
    importance: float
    access_count: int
    last_accessed_at: str | None
    decay_rate: float
    notebook_id: uuid.UUID | None
    conversation_id: uuid.UUID | None
    properties: dict | None


class MemoryHit(ORMModel):
    """A recalled memory with its blended relevance score."""

    memory: MemoryOut
    similarity: float
    effective_importance: float
    score: float


class RecallOut(ORMModel):
    query: str
    hits: list[MemoryHit]


class ConsolidateOut(ORMModel):
    clusters_created: int
    memories_promoted: int
    memories_scanned: int
    cluster_ids: list[uuid.UUID]


class ForgetOut(ORMModel):
    candidates: int
    deleted: int
    dry_run: bool
    freed_ids: list[uuid.UUID]
