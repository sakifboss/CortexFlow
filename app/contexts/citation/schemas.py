"""Citation schemas — shared by RAG, chat, and agents."""
from __future__ import annotations

import uuid

from app.schemas import ORMModel


class CitationRef(ORMModel):
    """A clickable reference attached to a span of generated text.

    `id` is the citation index (1-based) as displayed to the user.
    `chunk_id` points to the source chunk; `document_id` + `page` allow the
    UI to deep-link into the source document viewer.
    """

    id: int
    document_id: uuid.UUID
    document_title: str
    chunk_id: uuid.UUID | None = None
    page: int | None = None
    section: str | None = None
    snippet: str  # the source span that grounds the claim
    score: float = 0.0


class GroundedSpan(ORMModel):
    """A piece of assistant output plus the citations that ground it."""

    text: str
    citations: list[int] = []  # references into CitationRef.id
