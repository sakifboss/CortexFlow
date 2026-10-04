"""Search schemas."""
from __future__ import annotations

import uuid
from enum import StrEnum

from pydantic import Field

from app.schemas import ORMModel


class SearchMode(StrEnum):
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    GRAPH = "graph"
    MEMORY = "memory"


class SearchIn(ORMModel):
    query: str = Field(min_length=1)
    notebook_id: uuid.UUID | None = None
    document_ids: list[uuid.UUID] | None = None
    mode: SearchMode = SearchMode.HYBRID
    limit: int = 10
    filters: dict | None = None


class SearchHit(ORMModel):
    document_id: uuid.UUID
    document_title: str
    chunk_id: uuid.UUID
    page: int | None = None
    section: str | None = None
    text: str
    score: float


class SearchOut(ORMModel):
    query: str
    mode: SearchMode
    hits: list[SearchHit]
    took_ms: int
