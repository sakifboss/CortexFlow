"""
Knowledge Graph context (Phase 2).

Entities and relationships are primarily stored in Neo4j (graph-native).
These Postgres models are an *index/cache* for fast listing, search, and
workspace-scoped queries; the source of truth for graph traversal is Neo4j.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.models import TenantMixin, TimestampMixin, UUIDPK


class EntityType(str, enum.Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    EVENT = "event"
    CONCEPT = "concept"
    DATE = "date"
    DOCUMENT = "document"
    OTHER = "other"


class Entity(Base, UUIDPK, TimestampMixin, TenantMixin):
    __tablename__ = "kg_entities"
    __table_args__ = (Index("ix_entity_ws_type", "workspace_id", "type"),)

    type: Mapped[EntityType] = mapped_column(Enum(EntityType, name="entity_type"))
    name: Mapped[str] = mapped_column(String(300), index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    aliases: Mapped[list | None] = mapped_column(JSONB, default=None)
    properties: Mapped[dict | None] = mapped_column(JSONB, default=None)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    embedding_id: Mapped[str | None] = mapped_column(String(64), default=None)


class Relation(Base, UUIDPK, TimestampMixin, TenantMixin):
    __tablename__ = "kg_relations"
    __table_args__ = (
        Index("ix_rel_src", "source_id"),
        Index("ix_rel_tgt", "target_id"),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("kg_entities.id", ondelete="CASCADE"))
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("kg_entities.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(120), index=True)  # e.g. WORKS_FOR, AUTHORED
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    properties: Mapped[dict | None] = mapped_column(JSONB, default=None)
    source_chunk_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
