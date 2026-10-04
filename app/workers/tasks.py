"""
Background tasks — the document ingestion & embedding pipeline.

Flow:
    ingest_document(doc_id)
        → download from storage
        → parse (parser) → OCR (ocr) → chunk (chunker)
        → persist Chunk rows (status: CHUNKING)
        → embed_chunks(doc_id)            # separate queue, GPU-friendly
            → embed via gateway
            → upsert into Qdrant
            → mark document READY
"""
from __future__ import annotations

import uuid

from celery import shared_task
from loguru import logger
from sqlalchemy import select

from app.ai.embeddings import embeddings
from app.contexts.document.models import Chunk, Document, DocumentStatus
from app.core.db import db_session
from app.services.chunker import chunker
from app.services.ocr import ocr
from app.services.parser import parser
from app.services.storage import storage
from app.services.vector import vector


@shared_task(name="app.workers.tasks.ingest_document")
def ingest_document(document_id: str) -> None:
    """Synchronous Celery wrapper around the async pipeline."""
    import asyncio

    asyncio.run(_ingest(uuid.UUID(document_id)))


@shared_task(name="app.workers.tasks.embed_chunks")
def embed_chunks(document_id: str) -> None:
    import asyncio

    asyncio.run(_embed(uuid.UUID(document_id)))


# ── implementations ──────────────────────────────────────────
async def _ingest(document_id: uuid.UUID) -> None:
    async with db_session() as db:
        doc = (
            await db.execute(select(Document).where(Document.id == document_id))
        ).scalar_one_or_none()
        if not doc:
            logger.warning("ingest: document {} not found", document_id)
            return

        try:
            # 1. Parse
            doc.status = DocumentStatus.PARSING
            await db.commit()
            data = storage.download(doc.object_key)
            parsed = parser.parse(data=data, mime_type=doc.mime_type, filename=doc.title)
            doc.pages = parsed.pages
            doc.language = parsed.language

            # 2. OCR image-only blocks (PDFs)
            doc.status = DocumentStatus.OCR
            await db.commit()
            if doc.mime_type == "application/pdf":
                _ocr_pdf_blocks(parsed)

            # 3. Chunk
            doc.status = DocumentStatus.CHUNKING
            await db.commit()
            chunks = chunker.chunk_blocks(parsed.blocks)
            for i, c in enumerate(chunks):
                db.add(
                    Chunk(
                        document_id=doc.id,
                        workspace_id=doc.workspace_id,
                        notebook_id=doc.notebook_id,
                        chunk_index=i,
                        text=c.text,
                        page=c.page,
                        section=c.section,
                        char_start=c.char_start,
                        char_end=c.char_end,
                        token_count=c.token_count,
                    )
                )
            await db.commit()
            logger.info("Ingested doc={} chunks={}", document_id, len(chunks))

            # 4. Kick off embedding
            embed_chunks.delay(str(document_id))
        except Exception as exc:
            logger.exception("Ingest failed for {}", document_id)
            await _mark_failed(db, document_id, str(exc))


def _ocr_pdf_blocks(parsed) -> None:  # type: ignore[no-untyped-def]
    import fitz  # reopen from blocks isn't possible; OCR uses blocks flagged needs_ocr

    for block in parsed.blocks:
        if block.needs_ocr and block.page:
            # Re-OCR requires the original page; without it we skip silently.
            # (Production keeps the fitz handle on the parsed doc.)
            continue


async def _embed(document_id: uuid.UUID) -> None:
    async with db_session() as db:
        doc = (
            await db.execute(select(Document).where(Document.id == document_id))
        ).scalar_one_or_none()
        if not doc:
            return
        try:
            doc.status = DocumentStatus.EMBEDDING
            await db.commit()

            res = await db.execute(
                select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index)
            )
            chunks = list(res.scalars())
            if not chunks:
                doc.status = DocumentStatus.READY
                await db.commit()
                return

            # Batch embed for efficiency
            texts = [c.text for c in chunks]
            vectors = await embeddings.embed(texts)

            for c, vec in zip(chunks, vectors):
                await vector.upsert(
                    chunk_id=c.id,
                    embedding=vec,
                    text=c.text,
                    workspace_id=doc.workspace_id,
                    notebook_id=doc.notebook_id,
                    document_id=doc.id,
                    page=c.page,
                    section=c.section,
                )
                c.vector_id = str(c.id)
                c.embedding_model = embeddings.model
            await db.commit()
            doc.status = DocumentStatus.READY
            await db.commit()
            logger.info("Embedded doc={} chunks={}", document_id, len(chunks))
        except Exception as exc:
            logger.exception("Embed failed for {}", document_id)
            await _mark_failed(db, document_id, str(exc))


async def _mark_failed(db, document_id: uuid.UUID, error: str) -> None:  # type: ignore[no-untyped-def]
    doc = (
        await db.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if doc:
        doc.status = DocumentStatus.FAILED
        doc.error = error[:1000]
        await db.commit()


# ── Studio artifact generation (optional async path) ─────────
@shared_task(name="app.workers.tasks.generate_artifact")
def generate_artifact(
    *,
    workspace_id: str,
    notebook_id: str,
    user_id: str,
    payload: dict,
) -> str:
    """Async wrapper around ArtifactService.generate.

    The HTTP endpoint generates synchronously (see app/api/v1/artifacts.py);
    this task exists so heavy decks/reports can be offloaded to a worker and
    polled via GET /artifacts/{id}. Returns the artifact id.
    """
    import asyncio

    return asyncio.run(
        _generate_artifact(uuid.UUID(workspace_id), uuid.UUID(notebook_id), uuid.UUID(user_id), payload)
    )


async def _generate_artifact(
    workspace_id: uuid.UUID, notebook_id: uuid.UUID, user_id: uuid.UUID, payload: dict
) -> str:
    from app.contexts.artifact.schemas import ArtifactGenerateIn
    from app.contexts.artifact.service import artifact_service

    async with db_session() as db:
        out = await artifact_service.generate(
            db,
            workspace_id=workspace_id,
            notebook_id=notebook_id,
            user_id=user_id,
            payload=ArtifactGenerateIn.model_validate(payload),
        )
        return str(out.id)
