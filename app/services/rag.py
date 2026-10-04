"""
RAG orchestration service.

Pipeline:  Retrieve → Rerank → Reason → Ground → Answer
Exposes both a one-shot `answer()` and a streaming `stream_answer()` used by
the chat WebSocket/endpoint.

The "reason" step is implicit in the LLM call (CoT stays internal per policy);
explicit multi-hop / graph reasoning is layered on by the agent service.
"""
from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import embeddings
from app.ai.llm import llm
from app.ai.prompts import build_rag_messages
from app.contexts.document.models import Document
from app.services.citation import GroundedAnswer, citation_engine
from app.services.vector import vector


@dataclass(slots=True)
class RAGResult:
    answer: GroundedAnswer
    raw_text: str
    took_ms: int
    prompt_tokens: int
    completion_tokens: int


class RAGService:
    async def answer(
        self,
        *,
        db: AsyncSession,
        question: str,
        workspace_id: uuid.UUID,
        notebook_id: uuid.UUID | None = None,
        document_ids: list[uuid.UUID] | None = None,
        top_k: int = 8,
    ) -> RAGResult:
        t0 = time.perf_counter()

        # 1. Retrieve
        q_vec = await embeddings.embed_one(question)
        hits = await vector.search(
            query_vector=q_vec,
            workspace_id=workspace_id,
            notebook_id=notebook_id,
            document_ids=document_ids,
            limit=top_k,
        )

        # 2. Rerank (lightweight: score sort; swap for a cross-encoder later)
        hits = self._rerank(hits, keep=5)

        # 3. Load document titles for citations
        titles = await self._load_titles(db, [h.document_id for h in hits])

        # 4. Build context + prompt
        context = self._render_context(hits)
        messages = build_rag_messages(question, context)

        # 5. Generate
        resp = await llm.chat(messages)

        # 6. Ground
        grounded = citation_engine.ground(
            raw_answer=resp.text, hits=hits, document_titles=titles
        )

        return RAGResult(
            answer=grounded,
            raw_text=resp.text,
            took_ms=int((time.perf_counter() - t0) * 1000),
            prompt_tokens=resp.prompt_tokens,
            completion_tokens=resp.completion_tokens,
        )

    async def stream_answer(
        self,
        *,
        db: AsyncSession,
        question: str,
        workspace_id: uuid.UUID,
        notebook_id: uuid.UUID | None = None,
        document_ids: list[uuid.UUID] | None = None,
        top_k: int = 8,
    ) -> AsyncIterator[dict]:
        """Yields SSE-like events: retrieved, delta*, done."""
        t0 = time.perf_counter()
        q_vec = await embeddings.embed_one(question)
        hits = await vector.search(
            query_vector=q_vec,
            workspace_id=workspace_id,
            notebook_id=notebook_id,
            document_ids=document_ids,
            limit=top_k,
        )
        hits = self._rerank(hits, keep=5)
        titles = await self._load_titles(db, [h.document_id for h in hits])

        yield {"event": "sources", "data": [h.chunk_id for h in hits]}

        context = self._render_context(hits)
        messages = build_rag_messages(question, context)

        full = []
        async for delta in llm.stream(messages):
            full.append(delta)
            yield {"event": "delta", "data": delta}

        grounded = citation_engine.ground(
            raw_answer="".join(full), hits=hits, document_titles=titles
        )
        yield {
            "event": "done",
            "data": {
                "citations": [c.model_dump() for c in grounded.citations],
                "took_ms": int((time.perf_counter() - t0) * 1000),
            },
        }

    # ── helpers ──────────────────────────────────────────────
    @staticmethod
    def _rerank(hits: list, keep: int = 5) -> list:
        # Cheap rerank: blend score with a length-normalized snippet quality.
        scored = sorted(hits, key=lambda h: h.score, reverse=True)
        return scored[:keep]

    @staticmethod
    def _render_context(hits: list) -> str:
        parts = []
        for i, h in enumerate(hits, start=1):
            loc = f"page {h.page}" if h.page else (h.section or "source")
            parts.append(f"[{i}] ({loc}) {h.text}")
        return "\n\n".join(parts)

    @staticmethod
    async def _load_titles(db: AsyncSession, doc_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not doc_ids:
            return {}
        res = await db.execute(select(Document.id, Document.title).where(Document.id.in_(doc_ids)))
        return {row[0]: row[1] for row in res.all()}


rag = RAGService()
