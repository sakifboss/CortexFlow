"""
Artifact context — Studio-generated outputs.

A single ``Artifact`` model backs *every* Studio output type (audio overview,
slide deck, mind map, report, flashcards, quiz, infographic, data table, and
free-form "custom" artifacts). The ``kind`` discriminator selects the typed
content schema (see ``schemas.py``) and the generator (see ``generators.py``).

Keeping one table + one service (rather than nine near-identical contexts) is
the clean, extensible design: adding a new Studio type is a new enum member,
a content schema, and a generator entry — no new table, router, or migration.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.models import TenantMixin, TimestampMixin, UUIDPK
from app.contexts.notebook.models import Notebook


class ArtifactKind(str, enum.Enum):
    """The Studio output types. Value is the stable API/DB string."""

    CUSTOM = "custom"                 # 🧩 free-form, prompt-driven artifact
    AUDIO_OVERVIEW = "audio_overview" # 🎙️ two-host podcast-style dialogue
    SLIDE_DECK = "slide_deck"         # 📑 titled slides with bullets + notes
    MIND_MAP = "mind_map"             # 🧠 recursive concept tree
    REPORT = "report"                 # 📄 long-form grounded report
    FLASHCARDS = "flashcards"         # 🗂️ front/back study cards
    QUIZ = "quiz"                     # ❓ multiple-choice questions
    INFOGRAPHIC = "infographic"       # 📊 stat cards + visual sections
    DATA_TABLE = "data_table"         # 📋 structured extracted table


class ArtifactStatus(str, enum.Enum):
    PENDING = "pending"       # queued (async path)
    GENERATING = "generating" # LLM in flight
    READY = "ready"           # content validated + stored
    FAILED = "failed"         # generation/parse error (see `error`)


class Artifact(Base, UUIDPK, TimestampMixin, TenantMixin):
    __tablename__ = "artifacts"
    __table_args__ = (
        Index("ix_artifact_notebook_kind", "notebook_id", "kind"),
        Index("ix_artifact_notebook_created", "notebook_id", "created_at"),
    )

    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    kind: Mapped[ArtifactKind] = mapped_column(Enum(ArtifactKind, name="artifact_kind"))
    status: Mapped[ArtifactStatus] = mapped_column(
        Enum(ArtifactStatus, name="artifact_status"), default=ArtifactStatus.PENDING
    )

    title: Mapped[str] = mapped_column(String(300), default="Untitled artifact")
    # The user's focus / instruction that steered generation.
    prompt: Mapped[str | None] = mapped_column(Text, default=None)

    # Typed, kind-specific payload validated by the matching content schema.
    content: Mapped[dict | None] = mapped_column(JSONB, default=None)
    # Grounding: citation refs (same shape as chat citations) + source doc ids.
    citations: Mapped[list | None] = mapped_column(JSONB, default=None)
    source_document_ids: Mapped[list | None] = mapped_column(JSONB, default=None)

    # Bookkeeping
    model: Mapped[str | None] = mapped_column(String(120), default=None)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    took_ms: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, default=None)

    notebook: Mapped[Notebook] = relationship()
