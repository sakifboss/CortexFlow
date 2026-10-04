"""
Documents router.

Uploads are streamed to MinIO via the storage service, a Document row is
created, and `ingest_document` Celery task is dispatched. A signed download
URL is provided for the source viewer.
"""
from __future__ import annotations

import mimetypes
import uuid

from fastapi import APIRouter, File, UploadFile, status
from sqlalchemy import select

from app.contexts.document.models import Document, DocumentSource, DocumentStatus
from app.contexts.document.schemas import DocumentOut, DocumentUpdateIn
from app.contexts.document.service import document_service
from app.core.config import settings
from app.core.deps import DbDep, WorkspaceDep
from app.core.exceptions import ValidationError
from app.services.audit import audit
from app.services.storage import storage
from app.workers.tasks import ingest_document

router = APIRouter(
    prefix="/workspaces/{workspace_id}/notebooks/{notebook_id}/documents", tags=["documents"]
)


@router.get("", response_model=list[DocumentOut])
async def list_documents(notebook_id: uuid.UUID, ws: WorkspaceDep, db: DbDep):
    return await document_service.list(db, notebook_id=notebook_id)


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    notebook_id: uuid.UUID,
    ws: WorkspaceDep,
    db: DbDep,
    file: UploadFile = File(...),
):
    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise ValidationError(f"File exceeds {settings.max_upload_mb}MB limit")

    checksum = storage.checksum(data)
    mime = file.content_type or mimetypes.guess_type(file.filename or "file")[0] or "application/octet-stream"
    key = storage.key_for(str(ws.workspace_id), file.filename or "upload", checksum)
    storage.upload_bytes(key, data, content_type=mime)

    doc = await document_service.create(
        db,
        workspace_id=ws.workspace_id,
        notebook_id=notebook_id,
        uploaded_by=ws.user_id,
        title=file.filename or "upload",
        object_key=key,
        mime_type=mime,
        size_bytes=len(data),
        checksum=checksum,
    )
    ingest_document.delay(str(doc.id))
    await audit(db, action="document.upload", target_type="document", target_id=str(doc.id))
    return doc


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(document_id: uuid.UUID, ws: WorkspaceDep, db: DbDep):
    return DocumentOut.model_validate(await document_service.get(db, document_id))


@router.patch("/{document_id}", response_model=DocumentOut)
async def update_document(
    document_id: uuid.UUID, payload: DocumentUpdateIn, ws: WorkspaceDep, db: DbDep
):
    return await document_service.update(db, document_id, payload)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: uuid.UUID, ws: WorkspaceDep, db: DbDep):
    await document_service.delete(db, document_id)
    await audit(db, action="document.delete", target_type="document", target_id=str(document_id))


@router.post("/{document_id}/reingest", response_model=DocumentOut)
async def reingest(document_id: uuid.UUID, ws: WorkspaceDep, db: DbDep):
    doc = await document_service.get(db, document_id)
    doc.status = DocumentStatus.PENDING
    doc.error = None
    ingest_document.delay(str(doc.id))
    return DocumentOut.model_validate(doc)


@router.get("/{document_id}/download-url")
async def download_url(document_id: uuid.UUID, ws: WorkspaceDep, db: DbDep):
    doc = await document_service.get(db, document_id)
    return {"url": storage.presigned_url(doc.object_key), "mime_type": doc.mime_type}
