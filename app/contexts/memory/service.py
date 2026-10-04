"""
Memory service — the layered Agent Memory System.

Responsibilities
----------------
* write(...)        persist a memory, embed it, index it in the vector store
* recall(...)       blended retrieval: cosine similarity × effective importance
                    × recency; bumps access stats (reinforcement)
* consolidate(...)  cluster similar episodic memories, summarize each cluster,
                    and promote high-signal clusters into LONG_TERM memories
* forget(...)       prune memories whose *effective* importance has decayed
                    below a floor (Ebbinghaus-style exponential decay)

Effective importance
---------------------
    eff = base_importance * exp(-decay_rate * age_days) + access_bonus

where `access_bonus` rewards frequently-recalled memories (spaced-repetition
style reinforcement), capped so a memory can never exceed 1.0.

The service depends only on singletons already present in the codebase
(`embeddings`, `vector`, `llm`) so it drops in with zero new infra.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from datetime import datetime

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import embeddings
from app.ai.llm import llm
from app.contexts.memory.models import Memory, MemoryCluster, MemoryLayer
from app.contexts.memory.repository import memory_repository
from app.contexts.memory.schemas import (
    ConsolidateIn,
    ConsolidateOut,
    ForgetIn,
    ForgetOut,
    MemoryHit,
    MemoryOut,
    MemoryRecallIn,
    MemoryWriteIn,
    RecallOut,
)

# Default per-layer decay rates (per day). Working memory evaporates fast;
# long-term barely decays. These are sane defaults, overridable per row.
_LAYER_DECAY: dict[MemoryLayer, float] = {
    MemoryLayer.WORKING: 0.60,
    MemoryLayer.EPISODIC: 0.05,
    MemoryLayer.SEMANTIC: 0.01,
    MemoryLayer.PROCEDURAL: 0.005,
    MemoryLayer.LONG_TERM: 0.002,
}

# Blend weights for recall scoring.
_W_SIM = 0.65
_W_IMP = 0.25
_W_RECENCY = 0.10

_ACCESS_BONUS_CAP = 0.25


@dataclass(slots=True)
class _Scored:
    memory: Memory
    similarity: float
    eff_importance: float
    recency: float
    score: float


class MemoryService:
    # ── Write ────────────────────────────────────────────────
    async def write(
        self,
        db: AsyncSession,
        *,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID | None,
        payload: MemoryWriteIn,
    ) -> MemoryOut:
        importance = (
            payload.importance
            if payload.importance is not None
            else self._auto_importance(payload.content, payload.layer)
        )
        decay = _LAYER_DECAY.get(payload.layer, 0.05)

        embedding = await embeddings.embed_one(payload.content)
        embedding_id = str(uuid.uuid4())

        mem = Memory(
            workspace_id=workspace_id,
            user_id=user_id,
            notebook_id=payload.notebook_id,
            conversation_id=payload.conversation_id,
            layer=payload.layer,
            content=payload.content,
            summary=payload.summary,
            importance=importance,
            access_count=0,
            last_accessed_at=None,
            embedding_id=embedding_id,
            embedding_model=embeddings.model,
            decay_rate=decay,
            properties=payload.properties,
        )
        mem = await memory_repository.create(db, mem)

        # Index in the vector store (best-effort; recall falls back to DB scan).
        await self._index(mem, embedding)
        logger.debug("memory.write id={} layer={} imp={:.2f}", mem.id, mem.layer, importance)
        return MemoryOut.model_validate(mem)

    # ── Recall ───────────────────────────────────────────────
    async def recall(
        self,
        db: AsyncSession,
        *,
        workspace_id: uuid.UUID,
        payload: MemoryRecallIn,
    ) -> RecallOut:
        query_vec = await embeddings.embed_one(payload.query)

        # Candidate set: pull the pool for the requested scope from Postgres,
        # then score in-process. This keeps recall correct even when Qdrant is
        # unavailable, and lets us apply the importance/recency blend that a
        # pure vector search can't express.
        candidates = await memory_repository.list(
            db,
            workspace_id=workspace_id,
            layers=payload.layers,
            notebook_id=payload.notebook_id,
            conversation_id=payload.conversation_id,
            limit=1_000,
        )
        if not candidates:
            return RecallOut(query=payload.query, hits=[])

        now = datetime.utcnow()
        scored: list[_Scored] = []
        for mem in candidates:
            eff = self._effective_importance(mem, now)
            if eff < payload.min_importance:
                continue
            sim = await self._similarity(query_vec, mem)
            recency = self._recency_score(mem, now)
            blended = _W_SIM * sim + _W_IMP * eff + _W_RECENCY * recency
            scored.append(_Scored(mem, sim, eff, recency, blended))

        scored.sort(key=lambda s: s.score, reverse=True)
        top = scored[: payload.limit]

        # Reinforcement: recalling a memory strengthens it.
        stamp = now.isoformat(timespec="seconds")
        await memory_repository.bump_access(db, [s.memory.id for s in top], stamp)

        hits = [
            MemoryHit(
                memory=MemoryOut.model_validate(s.memory),
                similarity=round(s.similarity, 4),
                effective_importance=round(s.eff_importance, 4),
                score=round(s.score, 4),
            )
            for s in top
        ]
        return RecallOut(query=payload.query, hits=hits)

    # ── Consolidate ──────────────────────────────────────────
    async def consolidate(
        self,
        db: AsyncSession,
        *,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID | None,
        payload: ConsolidateIn,
    ) -> ConsolidateOut:
        """
        Greedy single-linkage clustering over episodic memories by cosine
        distance. Each cluster is summarized by the LLM and, if its aggregate
        signal clears `promote_threshold`, promoted into a LONG_TERM memory.
        """
        pool = await memory_repository.list(
            db,
            workspace_id=workspace_id,
            layers=[payload.layer],
            notebook_id=payload.notebook_id,
            limit=1_000,
        )
        if len(pool) < 2:
            return ConsolidateOut(
                clusters_created=0,
                memories_promoted=0,
                memories_scanned=len(pool),
                cluster_ids=[],
            )

        vectors = await self._vectors_for(pool)
        clusters = self._greedy_cluster(vectors, payload.max_cluster_distance)

        cluster_ids: list[uuid.UUID] = []
        promoted = 0
        now = datetime.utcnow()

        for group in clusters:
            if len(group) < 2:
                continue
            members = [pool[i] for i in group]
            centroid_idx = self._centroid_index([vectors[i] for i in group])
            centroid_mem = members[centroid_idx]

            cluster = MemoryCluster(
                workspace_id=workspace_id,
                centroid_memory_id=centroid_mem.id,
                member_ids=[str(m.id) for m in members],
                label=None,
            )
            summary = await self._summarize_cluster(members)
            cluster.label = summary[:200]
            cluster = await memory_repository.create_cluster(db, cluster)
            cluster_ids.append(cluster.id)

            agg = sum(self._effective_importance(m, now) for m in members) / len(members)
            if agg >= payload.promote_threshold:
                await self.write(
                    db,
                    workspace_id=workspace_id,
                    user_id=user_id,
                    payload=MemoryWriteIn(
                        content=summary,
                        layer=MemoryLayer.LONG_TERM,
                        summary=f"Consolidated from {len(members)} memories",
                        importance=min(1.0, agg + 0.1),
                        notebook_id=payload.notebook_id,
                        properties={"consolidated_from": [str(m.id) for m in members]},
                    ),
                )
                promoted += 1

        logger.info(
            "memory.consolidate ws={} clusters={} promoted={}",
            workspace_id, len(cluster_ids), promoted,
        )
        return ConsolidateOut(
            clusters_created=len(cluster_ids),
            memories_promoted=promoted,
            memories_scanned=len(pool),
            cluster_ids=cluster_ids,
        )

    # ── Forget ───────────────────────────────────────────────
    async def forget(
        self,
        db: AsyncSession,
        *,
        workspace_id: uuid.UUID,
        payload: ForgetIn,
    ) -> ForgetOut:
        pool = await memory_repository.list(
            db,
            workspace_id=workspace_id,
            layers=[payload.layer] if payload.layer else None,
            notebook_id=payload.notebook_id,
            limit=5_000,
        )
        now = datetime.utcnow()
        doomed = [
            m.id
            for m in pool
            # Never auto-forget consolidated long-term knowledge.
            if m.layer != MemoryLayer.LONG_TERM
            and self._effective_importance(m, now) < payload.importance_floor
        ]

        deleted = 0
        if not payload.dry_run and doomed:
            deleted = await memory_repository.delete_ids(db, doomed, workspace_id)
            await self._deindex(doomed)

        return ForgetOut(
            candidates=len(doomed),
            deleted=deleted,
            dry_run=payload.dry_run,
            freed_ids=doomed,
        )

    async def list_memories(
        self,
        db: AsyncSession,
        *,
        workspace_id: uuid.UUID,
        layer: MemoryLayer | None = None,
        notebook_id: uuid.UUID | None = None,
        limit: int = 100,
    ) -> list[MemoryOut]:
        rows = await memory_repository.list(
            db,
            workspace_id=workspace_id,
            layers=[layer] if layer else None,
            notebook_id=notebook_id,
            limit=limit,
        )
        return [MemoryOut.model_validate(r) for r in rows]

    async def delete(
        self, db: AsyncSession, *, workspace_id: uuid.UUID, memory_id: uuid.UUID
    ) -> bool:
        n = await memory_repository.delete_ids(db, [memory_id], workspace_id)
        if n:
            await self._deindex([memory_id])
        return bool(n)

    # ── Scoring internals ────────────────────────────────────
    def _effective_importance(self, mem: Memory, now: datetime) -> float:
        age_days = self._age_days(mem, now)
        decayed = mem.importance * math.exp(-mem.decay_rate * age_days)
        access_bonus = min(_ACCESS_BONUS_CAP, 0.03 * math.log1p(mem.access_count))
        return max(0.0, min(1.0, decayed + access_bonus))

    def _recency_score(self, mem: Memory, now: datetime) -> float:
        # Maps age → (0, 1]; ~half-life of 7 days.
        return math.exp(-self._age_days(mem, now) / 7.0)

    @staticmethod
    def _age_days(mem: Memory, now: datetime) -> float:
        created = mem.created_at
        if created.tzinfo is not None:
            created = created.replace(tzinfo=None)
        return max(0.0, (now - created).total_seconds() / 86_400.0)

    @staticmethod
    def _auto_importance(content: str, layer: MemoryLayer) -> float:
        """Heuristic seed importance when the caller doesn't supply one."""
        base = {
            MemoryLayer.WORKING: 0.3,
            MemoryLayer.EPISODIC: 0.5,
            MemoryLayer.SEMANTIC: 0.7,
            MemoryLayer.PROCEDURAL: 0.75,
            MemoryLayer.LONG_TERM: 0.85,
        }.get(layer, 0.5)
        # Longer, denser content tends to carry more signal — nudge slightly.
        length_bonus = min(0.15, len(content) / 8_000)
        return round(min(1.0, base + length_bonus), 3)

    # ── Vector helpers (best-effort; DB is source of truth) ──
    async def _index(self, mem: Memory, embedding: list[float]) -> None:
        try:
            from app.services.vector import vector

            await vector.upsert(
                chunk_id=mem.id,
                embedding=embedding,
                text=mem.content,
                workspace_id=mem.workspace_id,
                notebook_id=mem.notebook_id or mem.id,
                document_id=mem.id,
                page=None,
                section=f"memory:{mem.layer.value}",
            )
        except Exception as exc:  # pragma: no cover - infra optional in dev
            logger.debug("vector index skipped for memory {}: {}", mem.id, exc)

    async def _deindex(self, ids: list[uuid.UUID]) -> None:
        try:
            from app.services.vector import vector

            for mid in ids:
                await vector.delete_document(mid)
        except Exception as exc:  # pragma: no cover
            logger.debug("vector deindex skipped: {}", exc)

    async def _similarity(self, query_vec: list[float], mem: Memory) -> float:
        vec = await self._vector_for(mem)
        return _cosine(query_vec, vec)

    async def _vector_for(self, mem: Memory) -> list[float]:
        # Re-embed the memory content. Cheap for local models and keeps recall
        # correct without a round-trip to Qdrant. Cached per call via _vectors_for.
        return await embeddings.embed_one(mem.content)

    async def _vectors_for(self, mems: list[Memory]) -> list[list[float]]:
        texts = [m.content for m in mems]
        return await embeddings.embed(texts)

    # ── Clustering internals ─────────────────────────────────
    @staticmethod
    def _greedy_cluster(
        vectors: list[list[float]], max_distance: float
    ) -> list[list[int]]:
        """
        Greedy agglomerative clustering. O(n^2) — fine for the bounded pools
        we consolidate over (<= ~1k). Returns lists of indices into `vectors`.
        """
        n = len(vectors)
        assigned = [-1] * n
        clusters: list[list[int]] = []
        for i in range(n):
            if assigned[i] != -1:
                continue
            cid = len(clusters)
            clusters.append([i])
            assigned[i] = cid
            for j in range(i + 1, n):
                if assigned[j] != -1:
                    continue
                dist = 1.0 - _cosine(vectors[i], vectors[j])
                if dist <= max_distance:
                    clusters[cid].append(j)
                    assigned[j] = cid
        return clusters

    @staticmethod
    def _centroid_index(vectors: list[list[float]]) -> int:
        """Index of the vector closest to the group mean."""
        dim = len(vectors[0])
        mean = [sum(v[k] for v in vectors) / len(vectors) for k in range(dim)]
        best_i, best_sim = 0, -1.0
        for i, v in enumerate(vectors):
            s = _cosine(v, mean)
            if s > best_sim:
                best_i, best_sim = i, s
        return best_i

    async def _summarize_cluster(self, members: list[Memory]) -> str:
        joined = "\n".join(f"- {m.summary or m.content[:300]}" for m in members[:12])
        try:
            resp = await llm.chat(
                [
                    {
                        "role": "system",
                        "content": (
                            "You consolidate related memories into ONE concise, "
                            "factual statement capturing their shared knowledge. "
                            "Reply with a single sentence, no preamble."
                        ),
                    },
                    {"role": "user", "content": f"Memories:\n{joined}\n\nConsolidated fact:"},
                ],
                temperature=0.2,
                max_tokens=120,
            )
            text = resp.text.strip()
            if text:
                return text
        except Exception as exc:  # pragma: no cover - LLM optional in tests
            logger.debug("cluster summarize fell back to extractive: {}", exc)
        # Extractive fallback: the centroid's own content.
        return members[0].summary or members[0].content[:200]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / math.sqrt(na * nb)


memory_service = MemoryService()
