"""
Artifact schemas.

Two families live here:

1. **Content schemas** — one Pydantic model per ``ArtifactKind`` describing the
   validated shape of ``Artifact.content``. Generators emit JSON; the service
   validates it against these before persisting, so the frontend can trust the
   structure. All fields are permissive (sensible defaults) so a slightly
   malformed LLM payload still yields a usable artifact rather than a 500.

2. **API schemas** — the request (``ArtifactGenerateIn``), response
   (``ArtifactOut``, ``ArtifactSummary``), and the static ``KIND_CATALOG`` the
   Studio UI renders as its "create" grid.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.contexts.artifact.models import ArtifactKind, ArtifactStatus
from app.contexts.citation.schemas import CitationRef
from app.schemas import IDModel, ORMModel, Timestamped


# ══════════════════════════════════════════════════════════════════════════
# Content schemas (one per kind) — the validated shape of Artifact.content
# ══════════════════════════════════════════════════════════════════════════
class CustomContent(BaseModel):
    """🧩 Free-form markdown artifact."""

    format: Literal["markdown"] = "markdown"
    body: str = ""


class DialogueTurn(BaseModel):
    speaker: str = "Host"
    text: str = ""


class AudioOverviewContent(BaseModel):
    """🎙️ Podcast-style two-host dialogue (rendered + TTS'd in the browser)."""

    title: str = "Audio Overview"
    description: str = ""
    host_a: str = "Alex"
    host_b: str = "Sam"
    est_seconds: int = 0
    turns: list[DialogueTurn] = Field(default_factory=list)


class Slide(BaseModel):
    title: str = ""
    bullets: list[str] = Field(default_factory=list)
    notes: str = ""


class SlideDeckContent(BaseModel):
    """📑 Slide deck."""

    title: str = "Slide Deck"
    subtitle: str = ""
    slides: list[Slide] = Field(default_factory=list)


class MindNode(BaseModel):
    """🧠 Recursive mind-map node."""

    label: str = ""
    children: list["MindNode"] = Field(default_factory=list)


class MindMapContent(BaseModel):
    title: str = "Mind Map"
    root: MindNode = Field(default_factory=MindNode)


class ReportSection(BaseModel):
    heading: str = ""
    content: str = ""  # markdown


class ReportContent(BaseModel):
    """📄 Long-form report."""

    title: str = "Report"
    abstract: str = ""
    sections: list[ReportSection] = Field(default_factory=list)
    conclusion: str = ""


class Flashcard(BaseModel):
    front: str = ""
    back: str = ""
    hint: str = ""


class FlashcardsContent(BaseModel):
    """🗂️ Flashcard deck."""

    title: str = "Flashcards"
    cards: list[Flashcard] = Field(default_factory=list)


class QuizQuestion(BaseModel):
    question: str = ""
    options: list[str] = Field(default_factory=list)
    answer_index: int = 0
    explanation: str = ""


class QuizContent(BaseModel):
    """❓ Multiple-choice quiz."""

    title: str = "Quiz"
    questions: list[QuizQuestion] = Field(default_factory=list)


class InfographicStat(BaseModel):
    label: str = ""
    value: str = ""
    unit: str = ""
    description: str = ""


class InfographicSection(BaseModel):
    heading: str = ""
    icon: str = ""       # emoji hint
    points: list[str] = Field(default_factory=list)


class InfographicContent(BaseModel):
    """📊 Infographic — headline stats + themed sections."""

    title: str = "Infographic"
    subtitle: str = ""
    stats: list[InfographicStat] = Field(default_factory=list)
    sections: list[InfographicSection] = Field(default_factory=list)
    takeaway: str = ""


class DataTableContent(BaseModel):
    """📋 Structured data table."""

    title: str = "Data Table"
    caption: str = ""
    columns: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)


# Registry: kind → content model. The service uses this to validate payloads.
CONTENT_MODELS: dict[ArtifactKind, type[BaseModel]] = {
    ArtifactKind.CUSTOM: CustomContent,
    ArtifactKind.AUDIO_OVERVIEW: AudioOverviewContent,
    ArtifactKind.SLIDE_DECK: SlideDeckContent,
    ArtifactKind.MIND_MAP: MindMapContent,
    ArtifactKind.REPORT: ReportContent,
    ArtifactKind.FLASHCARDS: FlashcardsContent,
    ArtifactKind.QUIZ: QuizContent,
    ArtifactKind.INFOGRAPHIC: InfographicContent,
    ArtifactKind.DATA_TABLE: DataTableContent,
}


# ══════════════════════════════════════════════════════════════════════════
# API schemas
# ══════════════════════════════════════════════════════════════════════════
class ArtifactGenerateIn(ORMModel):
    """Request to generate a Studio artifact from a notebook's sources."""

    kind: ArtifactKind
    # Optional focus/instruction, e.g. "focus on the methodology section".
    prompt: str | None = Field(default=None, max_length=4000)
    title: str | None = Field(default=None, max_length=300)
    # Restrict grounding to a subset of sources (default: whole notebook).
    document_ids: list[uuid.UUID] | None = None
    # Per-kind knobs (count of cards/questions/slides, tone, difficulty…).
    options: dict[str, Any] = Field(default_factory=dict)
    # Retrieval breadth used to build grounded context.
    retrieve_k: int = Field(default=12, ge=1, le=40)


class ArtifactUpdateIn(ORMModel):
    title: str | None = None
    content: dict | None = None


class ArtifactSummary(IDModel, Timestamped):
    """Lightweight list item (no heavy content payload)."""

    notebook_id: uuid.UUID
    kind: ArtifactKind
    status: ArtifactStatus
    title: str
    prompt: str | None = None
    model: str | None = None
    error: str | None = None


class ArtifactOut(ArtifactSummary):
    """Full artifact including validated content + grounding."""

    content: dict | None = None
    citations: list[CitationRef] | None = None
    source_document_ids: list[uuid.UUID] | None = None
    tokens_used: int = 0
    took_ms: int = 0


class KindInfo(BaseModel):
    """Static catalog entry powering the Studio 'create' grid."""

    kind: ArtifactKind
    label: str
    emoji: str
    description: str
    # UI hints the frontend can render as option controls.
    supports_count: bool = False
    default_count: int | None = None
    count_label: str | None = None


KIND_CATALOG: list[KindInfo] = [
    KindInfo(
        kind=ArtifactKind.CUSTOM, label="Create Artifact", emoji="🧩",
        description="Generate anything from your sources with a free-form prompt.",
    ),
    KindInfo(
        kind=ArtifactKind.AUDIO_OVERVIEW, label="Audio Overview", emoji="🎙️",
        description="A two-host, podcast-style deep dive you can play back.",
    ),
    KindInfo(
        kind=ArtifactKind.SLIDE_DECK, label="Slide Deck", emoji="📑",
        description="Presentation-ready slides with bullets and speaker notes.",
        supports_count=True, default_count=8, count_label="Slides",
    ),
    KindInfo(
        kind=ArtifactKind.MIND_MAP, label="Mind Map", emoji="🧠",
        description="An interactive concept tree of the key ideas.",
    ),
    KindInfo(
        kind=ArtifactKind.REPORT, label="Report", emoji="📄",
        description="A structured, cited long-form report.",
    ),
    KindInfo(
        kind=ArtifactKind.FLASHCARDS, label="Flashcards", emoji="🗂️",
        description="Front/back study cards for active recall.",
        supports_count=True, default_count=12, count_label="Cards",
    ),
    KindInfo(
        kind=ArtifactKind.QUIZ, label="Quiz", emoji="❓",
        description="Multiple-choice questions with answers and explanations.",
        supports_count=True, default_count=8, count_label="Questions",
    ),
    KindInfo(
        kind=ArtifactKind.INFOGRAPHIC, label="Infographic", emoji="📊",
        description="Headline stats and themed sections at a glance.",
    ),
    KindInfo(
        kind=ArtifactKind.DATA_TABLE, label="Data Table", emoji="📋",
        description="Extract structured, tabular data from your sources.",
        supports_count=True, default_count=10, count_label="Rows",
    ),
]
