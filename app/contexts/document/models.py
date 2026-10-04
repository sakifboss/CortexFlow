"""Document context — uploaded sources, their chunks, and processing state."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.models import TenantMixin, TimestampMixin, UUIDPK
from app.contexts.notebook.models import Notebook


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    UPLOADED = "uploaded"
    PARSING = "parsing"
    OCR = "ocr"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    READY = "ready"
    FAILED = "failed"


class DocumentSource(str, enum.Enum):
    UPLOAD = "upload"
    URL = "url"
    GOOGLE_DRIVE = "google_drive"
    ONEDRIVE = "onedrive"
    DROPBOX = "dropbox"
    GITHUB = "github"
    YOUTUBE = "youtube"
    RSS = "rss"


class Document(Base, UUIDPK, TimestampMixin, TenantMixin):
    __tablename__ = "documents"
    __table_args__ = (Index("ix_doc_notebook_status", "notebook_id", "status"),)

    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="CASCADE"), index=True
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    title: Mapped[str] = mapped_column(String(400))
    source: Mapped[DocumentSource] = mapped_column(
        Enum(DocumentSource, name="document_source"), default=DocumentSource.UPLOAD
    )
    source_uri: Mapped[str | None] = mapped_column(String(1024), default=None)

    # Object storage
    object_key: Mapped[str] = mapped_column(String(512))  # MinIO/S3 key
    mime_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    checksum: Mapped[str | None] = mapped_column(String(128), default=None)

    # Parsing
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.PENDING
    )
    pages: Mapped[int | None] = mapped_column(Integer, default=None)
    language: Mapped[str | None] = mapped_column(String(20), default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)

    notebook: Mapped[Notebook] = relationship(back_populates="documents")
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="Chunk.chunk_index"
    )


class Chunk(Base, UUIDPK, TimestampMixin):
    """A semantic unit of a document, embedded into the vector store."""

    __tablename__ = "chunks"
    __table_args__ = (
        Index("ix_chunk_doc_idx", "document_id", "chunk_index"),
        Index("ix_chunk_workspace", "workspace_id"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    notebook_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)

    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    # Provenance for citations
    page: Mapped[int | None] = mapped_column(Integer, default=None)
    section: Mapped[str | None] = mapped_column(String(200), default=None)
    bbox: Mapped[list | None] = mapped_column(JSONB, default=None)  # [x0,y0,x1,y1]
    char_start: Mapped[int | None] = mapped_column(Integer, default=None)
    char_end: Mapped[int | None] = mapped_column(Integer, default=None)

    # Vector store reference (Qdrant point id mirrors this chunk's UUID)
    vector_id: Mapped[str | None] = mapped_column(String(64), default=None)
    embedding_model: Mapped[str | None] = mapped_column(String(120), default=None)
    token_count: Mapped[int | None] = mapped_column(Integer, default=None)
    meta: Mapped[dict | None] = mapped_column(JSONB, default=None)

    document: Mapped[Document] = relationship(back_populates="chunks")
