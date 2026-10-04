"""Document service — metadata CRUD; ingestion itself runs in Celery."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.document.models import Document, DocumentSource, DocumentStatus
from app.contexts.document.schemas import DocumentOut, DocumentUpdateIn
from app.core.exceptions import NotFoundError
from app.services.storage import storage


class DocumentService:
    async def create(
        self,
        db: AsyncSession,
        *,
        workspace_id: uuid.UUID,
        notebook_id: uuid.UUID,
        uploaded_by: uuid.UUID,
        title: str,
        object_key: str,
        mime_type: str,
        size_bytes: int,
        checksum: str | None,
        source: DocumentSource = DocumentSource.UPLOAD,
        source_uri: str | None = None,
    ) -> DocumentOut:
        doc = Document(
            workspace_id=workspace_id,
            notebook_id=notebook_id,
            uploaded_by=uploaded_by,
            title=title,
            source=source,
            source_uri=source_uri,
            object_key=object_key,
            mime_type=mime_type,
            size_bytes=size_bytes,
            checksum=checksum,
            status=DocumentStatus.UPLOADED,
        )
        db.add(doc)
        await db.flush()
        return DocumentOut.model_validate(doc)

    async def get(self, db: AsyncSession, doc_id: uuid.UUID) -> Document:
        doc = (
            await db.execute(select(Document).where(Document.id == doc_id))
        ).scalar_one_or_none()
        if not doc:
            raise NotFoundError("Document not found")
        return doc

    async def list(
        self,
        db: AsyncSession,
        *,
        notebook_id: uuid.UUID,
        statuses: list[DocumentStatus] | None = None,
    ) -> list[DocumentOut]:
        q = select(Document).where(Document.notebook_id == notebook_id)
        if statuses:
            q = q.where(Document.status.in_(statuses))
        q = q.order_by(Document.created_at.desc())
        return [DocumentOut.model_validate(d) for d in (await db.execute(q)).scalars()]

    async def update(
        self, db: AsyncSession, doc_id: uuid.UUID, payload: DocumentUpdateIn
    ) -> DocumentOut:
        doc = await self.get(db, doc_id)
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(doc, k, v)
        return DocumentOut.model_validate(doc)

    async def delete(self, db: AsyncSession, doc_id: uuid.UUID) -> None:
        doc = await self.get(db, doc_id)
        # Best-effort delete from object store + vector store
        try:
            storage.delete(doc.object_key)
        except Exception:
            pass
        await db.delete(doc)

    async def set_status(
        self,
        db: AsyncSession,
        doc_id: uuid.UUID,
        status: DocumentStatus,
        *,
        error: str | None = None,
        pages: int | None = None,
        language: str | None = None,
    ) -> None:
        doc = await self.get(db, doc_id)
        doc.status = status
        if error is not None:
            doc.error = error
        if pages is not None:
            doc.pages = pages
        if language is not None:
            doc.language = language


document_service = DocumentService()
