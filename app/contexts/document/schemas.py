"""Document schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from app.contexts.document.models import DocumentSource, DocumentStatus
from app.schemas import IDModel, ORMModel, Timestamped


class DocumentOut(IDModel, Timestamped):
    workspace_id: uuid.UUID
    notebook_id: uuid.UUID
    uploaded_by: uuid.UUID
    title: str
    source: DocumentSource
    source_uri: str | None
    mime_type: str
    size_bytes: int
    status: DocumentStatus
    pages: int | None
    language: str | None
    error: str | None
    progress: float | None = None  # 0..1 of ingest pipeline


class DocumentUpdateIn(ORMModel):
    title: str | None = None


class ChunkOut(IDModel, Timestamped):
    document_id: uuid.UUID
    chunk_index: int
    text: str
    page: int | None
    section: str | None
    token_count: int | None


class DocumentListOut(ORMModel):
    documents: list[DocumentOut]
    total: int


class IngestURLOn(ORMModel):
    url: str
    title: str | None = None
