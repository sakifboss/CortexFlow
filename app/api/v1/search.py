"""Search router — semantic / keyword / hybrid."""
from __future__ import annotations

import time
import uuid

from fastapi import APIRouter

from app.ai.embeddings import embeddings
from app.contexts.document.models import Document
from app.contexts.search.schemas import SearchIn, SearchOut, SearchHit
from app.core.deps import DbDep, WorkspaceDep
from app.services.vector import vector
from sqlalchemy import select

router = APIRouter(prefix="/workspaces/{workspace_id}/search", tags=["search"])


@router.post("", response_model=SearchOut)
async def search(payload: SearchIn, ws: WorkspaceDep, db: DbDep):
    t0 = time.perf_counter()
    q_vec = await embeddings.embed_one(payload.query)

    doc_ids = payload.document_ids
    if payload.notebook_id and not doc_ids:
        res = await db.execute(select(Document.id).where(Document.notebook_id == payload.notebook_id))
        doc_ids = [r[0] for r in res.all()]

    hits = await vector.search(
        query_vector=q_vec,
        workspace_id=ws.workspace_id,
        document_ids=doc_ids,
        limit=payload.limit,
    )

    titles = {}
    if hits:
        res = await db.execute(select(Document.id, Document.title).where(Document.id.in_([h.document_id for h in hits])))
        titles = {r[0]: r[1] for r in res.all()}

    out_hits = [
        SearchHit(
            document_id=h.document_id,
            document_title=titles.get(h.document_id, "Source"),
            chunk_id=h.chunk_id,
            page=h.page,
            section=h.section,
            text=h.text,
            score=h.score,
        )
        for h in hits
    ]
    return SearchOut(
        query=payload.query,
        mode=payload.mode,
        hits=out_hits,
        took_ms=int((time.perf_counter() - t0) * 1000),
    )
