"""
Artifact service.

Orchestrates Studio generation end to end:

    resolve sources → retrieve grounded context (vector search, reused from RAG)
      → build kind-specific prompt (generators) → LLM call
      → extract + validate JSON against the content schema
      → attach citations → persist Artifact

The heavy retrieval/grounding stack (``embeddings``, ``vector``,
``citation_engine``) is shared with the chat RAG path, so Studio outputs are
grounded and cite the exact source spans — same guarantee as chat answers.

Generation is synchronous here (mirrors the existing ``/chat`` endpoint) but the
public :meth:`generate` is pure orchestration, so a Celery task can wrap it for
an async/polling path without changes (see ``app.workers.tasks``).
"""
from __future__ import annotations

import time
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import embeddings
from app.ai.llm import llm
from app.contexts.artifact.generators import build_messages, extract_json
from app.contexts.artifact.models import Artifact, ArtifactKind, ArtifactStatus
from app.contexts.artifact.schemas import (
    CONTENT_MODELS,
    ArtifactGenerateIn,
    ArtifactOut,
    ArtifactSummary,
    ArtifactUpdateIn,
)
from app.contexts.artifact.generators import REGISTRY
from app.contexts.citation.schemas import CitationRef
from app.contexts.document.models import Document
from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.services.citation import citation_engine
from app.services.vector import VectorHit, vector

log = get_logger(__name__)

# Kinds that expect inline [n] citations in their text — grounding is validated
# for these. Structured kinds (quiz, table, mind map) still get a citation
# table, but we don't strip their content.
_TEXTUAL_KINDS = {
    ArtifactKind.CUSTOM,
    ArtifactKind.REPORT,
    ArtifactKind.SLIDE_DECK,
    ArtifactKind.AUDIO_OVERVIEW,
}


class ArtifactService:
    # ── Generation ───────────────────────────────────────────
    async def generate(
        self,
        db: AsyncSession,
        *,
        workspace_id: uuid.UUID,
        notebook_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: ArtifactGenerateIn,
    ) -> ArtifactOut:
        t0 = time.perf_counter()

        art = Artifact(
            workspace_id=workspace_id,
            notebook_id=notebook_id,
            created_by=user_id,
            kind=payload.kind,
            status=ArtifactStatus.GENERATING,
            title=payload.title or REGISTRY[payload.kind].system[:40],
            prompt=payload.prompt,
            source_document_ids=[str(d) for d in (payload.document_ids or [])] or None,
        )
        db.add(art)
        await db.flush()

        try:
            hits, titles = await self._retrieve(
                db,
                workspace_id=workspace_id,
                notebook_id=notebook_id,
                query=self._retrieval_query(payload),
                document_ids=payload.document_ids,
                top_k=payload.retrieve_k,
            )
            context = self._render_context(hits)
            messages = build_messages(
                payload.kind, context=context, focus=payload.prompt or "", options=payload.options
            )

            resp = await llm.chat(messages, max_tokens=settings.llm_max_tokens)
            raw = extract_json(resp.text)
            if isinstance(raw, list):
                # Some models return a bare array; wrap into the primary field.
                raw = self._wrap_array(payload.kind, raw)

            content_model = CONTENT_MODELS[payload.kind]
            validated = content_model.model_validate(raw)
            content = validated.model_dump()

            citations = self._build_citations(hits, titles)
            if payload.kind in _TEXTUAL_KINDS:
                content = self._ground_textual(payload.kind, content, hits, titles)

            art.content = content
            art.citations = [c.model_dump(mode="json") for c in citations]
            art.title = payload.title or REGISTRY[payload.kind].title_of(content)
            art.model = resp.model
            art.tokens_used = (resp.prompt_tokens or 0) + (resp.completion_tokens or 0)
            art.took_ms = int((time.perf_counter() - t0) * 1000)
            art.status = ArtifactStatus.READY
            art.error = None
        except Exception as exc:  # noqa: BLE001
            log.exception("Artifact generation failed: {}", exc)
            art.status = ArtifactStatus.FAILED
            art.error = str(exc)[:1000]
            art.took_ms = int((time.perf_counter() - t0) * 1000)

        await db.flush()
        return self._to_out(art)

    async def regenerate(
        self, db: AsyncSession, *, artifact_id: uuid.UUID, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> ArtifactOut:
        art = await self._get(db, artifact_id, workspace_id)
        payload = ArtifactGenerateIn(
            kind=art.kind,
            prompt=art.prompt,
            title=None,  # let the fresh content re-derive the title
            document_ids=[uuid.UUID(d) for d in (art.source_document_ids or [])] or None,
        )
        # Regenerate in place by mutating the same row via a fresh generate that
        # reuses this row's identity is overkill; simplest is a new artifact.
        return await self.generate(
            db,
            workspace_id=workspace_id,
            notebook_id=art.notebook_id,
            user_id=user_id,
            payload=payload,
        )

    # ── CRUD ─────────────────────────────────────────────────
    async def list(
        self,
        db: AsyncSession,
        *,
        notebook_id: uuid.UUID,
        kind: ArtifactKind | None = None,
    ) -> list[ArtifactSummary]:
        q = select(Artifact).where(Artifact.notebook_id == notebook_id)
        if kind is not None:
            q = q.where(Artifact.kind == kind)
        q = q.order_by(Artifact.created_at.desc())
        return [self._to_summary(a) for a in (await db.execute(q)).scalars()]

    async def get(self, db: AsyncSession, *, artifact_id: uuid.UUID, workspace_id: uuid.UUID) -> ArtifactOut:
        return self._to_out(await self._get(db, artifact_id, workspace_id))

    async def update(
        self,
        db: AsyncSession,
        *,
        artifact_id: uuid.UUID,
        workspace_id: uuid.UUID,
        payload: ArtifactUpdateIn,
    ) -> ArtifactOut:
        art = await self._get(db, artifact_id, workspace_id)
        if payload.title is not None:
            art.title = payload.title
        if payload.content is not None:
            # Re-validate edited content against the schema.
            model = CONTENT_MODELS[art.kind]
            art.content = model.model_validate(payload.content).model_dump()
        await db.flush()
        return self._to_out(art)

    async def delete(self, db: AsyncSession, *, artifact_id: uuid.UUID, workspace_id: uuid.UUID) -> None:
        art = await self._get(db, artifact_id, workspace_id)
        await db.delete(art)

    # ── internals ────────────────────────────────────────────
    async def _get(self, db: AsyncSession, artifact_id: uuid.UUID, workspace_id: uuid.UUID) -> Artifact:
        art = (
            await db.execute(
                select(Artifact).where(
                    Artifact.id == artifact_id, Artifact.workspace_id == workspace_id
                )
            )
        ).scalar_one_or_none()
        if not art:
            raise NotFoundError("Artifact not found")
        return art

    @staticmethod
    def _retrieval_query(payload: ArtifactGenerateIn) -> str:
        base = {
            ArtifactKind.CUSTOM: "key ideas, arguments and evidence",
            ArtifactKind.AUDIO_OVERVIEW: "overview, main themes and takeaways",
            ArtifactKind.SLIDE_DECK: "structure, key points and conclusions",
            ArtifactKind.MIND_MAP: "concepts, topics and their relationships",
            ArtifactKind.REPORT: "findings, analysis, methodology and conclusions",
            ArtifactKind.FLASHCARDS: "definitions, key facts and terms",
            ArtifactKind.QUIZ: "testable facts, definitions and concepts",
            ArtifactKind.INFOGRAPHIC: "statistics, metrics, numbers and highlights",
            ArtifactKind.DATA_TABLE: "structured data, entities, attributes and values",
        }[payload.kind]
        return (payload.prompt.strip() + " " if payload.prompt else "") + base

    async def _retrieve(
        self,
        db: AsyncSession,
        *,
        workspace_id: uuid.UUID,
        notebook_id: uuid.UUID,
        query: str,
        document_ids: list[uuid.UUID] | None,
        top_k: int,
    ) -> tuple[list[VectorHit], dict[uuid.UUID, str]]:
        try:
            q_vec = await embeddings.embed_one(query)
            hits = await vector.search(
                query_vector=q_vec,
                workspace_id=workspace_id,
                notebook_id=notebook_id,
                document_ids=document_ids,
                limit=top_k,
            )
        except Exception as exc:  # noqa: BLE001 — Studio still works without a vector store
            log.warning("Artifact retrieval failed ({}); generating from prompt only.", exc)
            hits = []
        titles = await self._load_titles(db, [h.document_id for h in hits])
        return hits, titles

    @staticmethod
    def _render_context(hits: list[VectorHit]) -> str:
        if not hits:
            return "(No source excerpts were retrieved. Generate from the user's instruction.)"
        parts = []
        for i, h in enumerate(hits, start=1):
            loc = f"page {h.page}" if h.page else (h.section or "source")
            parts.append(f"[{i}] ({loc}) {h.text}")
        return "\n\n".join(parts)

    @staticmethod
    def _build_citations(hits: list[VectorHit], titles: dict[uuid.UUID, str]) -> list[CitationRef]:
        out: list[CitationRef] = []
        for i, h in enumerate(hits, start=1):
            out.append(
                CitationRef(
                    id=i,
                    document_id=h.document_id,
                    document_title=titles.get(h.document_id, "Source"),
                    chunk_id=h.chunk_id,
                    page=h.page,
                    section=h.section,
                    snippet=h.text[:400],
                    score=h.score,
                )
            )
        return out

    @staticmethod
    def _ground_textual(
        kind: ArtifactKind, content: dict, hits: list[VectorHit], titles: dict[uuid.UUID, str]
    ) -> dict:
        """Run textual fields through the citation engine to drop bogus [n]."""
        def clean(text: str) -> str:
            if not text:
                return text
            return citation_engine.ground(
                raw_answer=text, hits=hits, document_titles=titles
            ).text

        if kind == ArtifactKind.CUSTOM:
            content["body"] = clean(content.get("body", ""))
        elif kind == ArtifactKind.REPORT:
            content["abstract"] = clean(content.get("abstract", ""))
            content["conclusion"] = clean(content.get("conclusion", ""))
            for s in content.get("sections", []):
                s["content"] = clean(s.get("content", ""))
        elif kind == ArtifactKind.SLIDE_DECK:
            for s in content.get("slides", []):
                s["bullets"] = [clean(b) for b in s.get("bullets", [])]
        # Audio overview stays verbatim — spoken script shouldn't show [n] markers.
        return content

    @staticmethod
    def _wrap_array(kind: ArtifactKind, arr: list) -> dict:
        key = {
            ArtifactKind.SLIDE_DECK: "slides",
            ArtifactKind.FLASHCARDS: "cards",
            ArtifactKind.QUIZ: "questions",
            ArtifactKind.AUDIO_OVERVIEW: "turns",
            ArtifactKind.INFOGRAPHIC: "stats",
            ArtifactKind.DATA_TABLE: "rows",
        }.get(kind)
        return {key: arr} if key else {"body": str(arr)}

    @staticmethod
    async def _load_titles(db: AsyncSession, doc_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not doc_ids:
            return {}
        res = await db.execute(
            select(Document.id, Document.title).where(Document.id.in_(list(set(doc_ids))))
        )
        return {row[0]: row[1] for row in res.all()}

    # ── mapping ──────────────────────────────────────────────
    @staticmethod
    def _to_summary(a: Artifact) -> ArtifactSummary:
        return ArtifactSummary(
            id=a.id,
            created_at=a.created_at,
            updated_at=a.updated_at,
            notebook_id=a.notebook_id,
            kind=a.kind,
            status=a.status,
            title=a.title,
            prompt=a.prompt,
            model=a.model,
            error=a.error,
        )

    @staticmethod
    def _to_out(a: Artifact) -> ArtifactOut:
        return ArtifactOut(
            id=a.id,
            created_at=a.created_at,
            updated_at=a.updated_at,
            notebook_id=a.notebook_id,
            kind=a.kind,
            status=a.status,
            title=a.title,
            prompt=a.prompt,
            model=a.model,
            error=a.error,
            content=a.content,
            citations=[CitationRef.model_validate(c) for c in (a.citations or [])],
            source_document_ids=[uuid.UUID(d) for d in (a.source_document_ids or [])] or None,
            tokens_used=a.tokens_used,
            took_ms=a.took_ms,
        )


artifact_service = ArtifactService()
