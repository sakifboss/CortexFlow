"""
Tests for the Agent Memory System's core logic.

These exercise the pure, deterministic parts of the service — decay math,
blended recall scoring, clustering, and consolidation — with the embedding
backend stubbed so no Ollama/Qdrant/Postgres is required. Run with:

    pytest tests/test_memory_service.py -v
"""
from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta

import enum

import pytest


# Local mirror of app.contexts.memory.models.MemoryLayer. Defined here so test
# *collection* doesn't import the ORM model module (which configures a mapper
# eagerly). Values are asserted against the real enum in
# test_layer_enum_matches_model below.
class MemoryLayer(str, enum.Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    LONG_TERM = "long_term"


from app.contexts.memory.schemas import (  # noqa: E402
    ConsolidateIn,
    ForgetIn,
    MemoryRecallIn,
    MemoryWriteIn,
)
from app.contexts.memory.service import MemoryService, _cosine  # noqa: E402


class MemoryStub:
    """
    Attribute-compatible stand-in for the ORM Memory model.

    The service only ever *reads* attributes off Memory objects and persists
    them through the repository, so a plain object with the same fields lets us
    unit-test the logic without constructing the SQLAlchemy dataclass (whose
    mixin ordering requires a live mapper configuration).
    """

    __slots__ = (
        "id", "workspace_id", "user_id", "notebook_id", "conversation_id",
        "layer", "content", "summary", "importance", "access_count",
        "last_accessed_at", "embedding_id", "embedding_model", "decay_rate",
        "properties", "created_at", "updated_at",
    )

    def __init__(self, **kw):
        for slot in self.__slots__:
            setattr(self, slot, kw.get(slot))
        if self.access_count is None:
            self.access_count = 0


class ClusterStub:
    __slots__ = ("id", "workspace_id", "centroid_memory_id", "member_ids",
                 "label", "created_at", "updated_at")

    def __init__(self, **kw):
        for slot in self.__slots__:
            setattr(self, slot, kw.get(slot))


# Patch the service module's ORM symbols so it builds infra-free stubs.
@pytest.fixture(autouse=True)
def _patch_memory_model(monkeypatch):
    from app.contexts.memory import service as service_mod

    monkeypatch.setattr(service_mod, "Memory", MemoryStub)
    monkeypatch.setattr(service_mod, "MemoryCluster", ClusterStub)


# ─────────────────────────────────────────────────────────────
# Fakes: an in-memory repository + deterministic embeddings so the
# service can be tested without any external infrastructure.
# ─────────────────────────────────────────────────────────────
def _fake_embed(text: str) -> list[float]:
    """Deterministic 8-dim bag-of-chars embedding — similar text → similar vec."""
    vec = [0.0] * 8
    for ch in text.lower():
        vec[ord(ch) % 8] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class FakeRepo:
    def __init__(self) -> None:
        self.rows: dict = {}
        self.clusters: list = []

    async def create(self, db, memory) -> "MemoryStub":
        if getattr(memory, "id", None) is None:
            memory.id = uuid.uuid4()
        if getattr(memory, "created_at", None) is None:
            memory.created_at = datetime.utcnow()
        memory.updated_at = datetime.utcnow()
        self.rows[memory.id] = memory
        return memory

    async def list(self, db, *, workspace_id, layers=None, notebook_id=None,
                   conversation_id=None, limit=500):
        out = [
            m for m in self.rows.values()
            if m.workspace_id == workspace_id
            and (layers is None or m.layer in layers)
            and (notebook_id is None or m.notebook_id == notebook_id)
            and (conversation_id is None or m.conversation_id == conversation_id)
        ]
        out.sort(key=lambda m: m.created_at, reverse=True)
        return out[:limit]

    async def fetch_by_ids(self, db, ids, workspace_id):
        return [self.rows[i] for i in ids if i in self.rows]

    async def bump_access(self, db, ids, when):
        for i in ids:
            if i in self.rows:
                self.rows[i].access_count += 1
                self.rows[i].last_accessed_at = when

    async def delete_ids(self, db, ids, workspace_id):
        n = 0
        for i in list(ids):
            if i in self.rows:
                del self.rows[i]
                n += 1
        return n

    async def create_cluster(self, db, cluster):
        if getattr(cluster, "id", None) is None:
            cluster.id = uuid.uuid4()
        cluster.created_at = datetime.utcnow()
        cluster.updated_at = datetime.utcnow()
        self.clusters.append(cluster)
        return cluster


class FakeEmbeddings:
    model = "fake-embed"

    async def embed_one(self, text: str) -> list[float]:
        return _fake_embed(text)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [_fake_embed(t) for t in texts]


@pytest.fixture
def svc(monkeypatch):
    """A MemoryService wired to fakes: no DB, no network, no LLM."""
    from app.contexts.memory import service as service_mod

    repo = FakeRepo()
    fake_emb = FakeEmbeddings()
    monkeypatch.setattr(service_mod, "memory_repository", repo)
    monkeypatch.setattr(service_mod, "embeddings", fake_emb)

    s = MemoryService()
    # Vector indexing + LLM summarize are best-effort; stub them to no-ops.

    async def _noop_index(mem, embedding):
        return None

    async def _noop_deindex(ids):
        return None

    async def _extractive_summary(members):
        return (members[0].summary or members[0].content)[:200]

    monkeypatch.setattr(s, "_index", _noop_index)
    monkeypatch.setattr(s, "_deindex", _noop_deindex)
    monkeypatch.setattr(s, "_summarize_cluster", _extractive_summary)
    s._repo = repo  # expose for assertions
    return s


WS = uuid.uuid4()


def _mem(content, layer=MemoryLayer.EPISODIC, importance=0.5, age_days=0.0,
         access=0, decay=None) -> MemoryStub:
    from app.contexts.memory.service import _LAYER_DECAY

    created = datetime.utcnow() - timedelta(days=age_days)
    return MemoryStub(
        id=uuid.uuid4(),
        workspace_id=WS,
        user_id=None,
        notebook_id=None,
        conversation_id=None,
        layer=layer,
        content=content,
        summary=None,
        importance=importance,
        access_count=access,
        last_accessed_at=None,
        embedding_id=None,
        embedding_model=None,
        decay_rate=decay if decay is not None else _LAYER_DECAY[layer],
        properties=None,
        created_at=created,
        updated_at=created,
    )


# ── Guard: local enum mirror stays in sync with the ORM model ─
def test_layer_enum_matches_model():
    from app.contexts.memory.models import MemoryLayer as RealLayer

    assert {m.name: m.value for m in MemoryLayer} == {
        m.name: m.value for m in RealLayer
    }


# ── Pure math ────────────────────────────────────────────────
def test_cosine_identity_and_orthogonal():
    assert _cosine([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)
    assert _cosine([1, 0], [0, 1]) == pytest.approx(0.0)
    assert _cosine([], [1]) == 0.0  # guard against empty


def test_effective_importance_decays_with_age():
    s = MemoryService()
    now = datetime.utcnow()
    fresh = _mem("x", importance=0.8, age_days=0)
    old = _mem("x", importance=0.8, age_days=30, decay=0.05)
    assert s._effective_importance(fresh, now) > s._effective_importance(old, now)
    # exp(-0.05*30) ≈ 0.223 → 0.8 * 0.223 ≈ 0.178
    assert s._effective_importance(old, now) == pytest.approx(0.8 * math.exp(-1.5), abs=0.02)


def test_access_reinforces_importance():
    s = MemoryService()
    now = datetime.utcnow()
    cold = _mem("x", importance=0.5, age_days=10, access=0, decay=0.05)
    hot = _mem("x", importance=0.5, age_days=10, access=50, decay=0.05)
    assert s._effective_importance(hot, now) > s._effective_importance(cold, now)


def test_effective_importance_clamped_0_1():
    s = MemoryService()
    now = datetime.utcnow()
    m = _mem("x", importance=1.0, age_days=0, access=10_000)
    assert 0.0 <= s._effective_importance(m, now) <= 1.0


def test_auto_importance_orders_by_layer():
    s = MemoryService()
    working = s._auto_importance("hi", MemoryLayer.WORKING)
    longterm = s._auto_importance("hi", MemoryLayer.LONG_TERM)
    assert longterm > working


def test_greedy_cluster_groups_near_and_splits_far():
    s = MemoryService()
    a = _fake_embed("cats are wonderful pets")
    a2 = _fake_embed("cats are wonderful pets!")   # near-duplicate → same cluster
    b = _fake_embed("quantum chromodynamics lagrangian")  # far → own cluster
    clusters = s._greedy_cluster([a, a2, b], max_distance=0.15)
    sizes = sorted(len(c) for c in clusters)
    assert sizes == [1, 2]


def test_centroid_index_picks_representative():
    s = MemoryService()
    vecs = [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]]
    idx = s._centroid_index(vecs)
    assert idx in (0, 1)  # the two clustered vectors, not the outlier


# ── Async service behaviour ──────────────────────────────────
@pytest.mark.asyncio
async def test_write_persists_and_seeds_importance(svc):
    out = await svc.write(
        None, workspace_id=WS, user_id=None,
        payload=MemoryWriteIn(content="user prefers dark mode", layer=MemoryLayer.SEMANTIC),
    )
    assert out.layer == MemoryLayer.SEMANTIC
    assert 0.0 < out.importance <= 1.0
    assert len(svc._repo.rows) == 1
    # embedding_model is an internal field (not surfaced in MemoryOut); verify
    # it was recorded on the persisted row.
    persisted = svc._repo.rows[out.id]
    assert persisted.embedding_model == "fake-embed"
    assert persisted.embedding_id is not None


@pytest.mark.asyncio
async def test_recall_ranks_relevant_memory_first(svc):
    await svc.write(None, workspace_id=WS, user_id=None,
                    payload=MemoryWriteIn(content="the deployment runs on Render"))
    await svc.write(None, workspace_id=WS, user_id=None,
                    payload=MemoryWriteIn(content="my favorite fruit is mango"))
    out = await svc.recall(
        None, workspace_id=WS,
        payload=MemoryRecallIn(query="where is the deployment hosted", limit=2),
    )
    assert out.hits, "expected at least one hit"
    assert "Render" in out.hits[0].memory.content
    # scores are sorted descending
    scores = [h.score for h in out.hits]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_recall_bumps_access_count(svc):
    await svc.write(None, workspace_id=WS, user_id=None,
                    payload=MemoryWriteIn(content="remember the API key rotation policy"))
    out = await svc.recall(None, workspace_id=WS,
                           payload=MemoryRecallIn(query="API key rotation", limit=1))
    mid = out.hits[0].memory.id
    assert svc._repo.rows[mid].access_count == 1


@pytest.mark.asyncio
async def test_recall_respects_min_importance(svc):
    m = _mem("low signal note", importance=0.05, age_days=40, decay=0.1)
    svc._repo.rows[m.id] = m
    out = await svc.recall(None, workspace_id=WS,
                           payload=MemoryRecallIn(query="low signal note",
                                                  min_importance=0.5, limit=5))
    assert all(h.effective_importance >= 0.5 for h in out.hits)


@pytest.mark.asyncio
async def test_forget_dry_run_deletes_nothing(svc):
    m = _mem("stale", importance=0.05, age_days=100, decay=0.2)
    svc._repo.rows[m.id] = m
    out = await svc.forget(None, workspace_id=WS,
                           payload=ForgetIn(importance_floor=0.15, dry_run=True))
    assert out.candidates >= 1
    assert out.deleted == 0
    assert m.id in svc._repo.rows  # still there


@pytest.mark.asyncio
async def test_forget_deletes_decayed_but_spares_long_term(svc):
    stale = _mem("stale episodic", importance=0.05, age_days=100, decay=0.2)
    lt = _mem("core fact", layer=MemoryLayer.LONG_TERM, importance=0.05,
              age_days=100, decay=0.2)
    svc._repo.rows[stale.id] = stale
    svc._repo.rows[lt.id] = lt
    out = await svc.forget(None, workspace_id=WS,
                           payload=ForgetIn(importance_floor=0.15, dry_run=False))
    assert stale.id not in svc._repo.rows       # decayed episodic pruned
    assert lt.id in svc._repo.rows              # long-term spared
    assert out.deleted >= 1


@pytest.mark.asyncio
async def test_consolidate_clusters_and_promotes(svc):
    # Three near-duplicate high-importance memories → one cluster, promoted.
    for i in range(3):
        m = _mem("release notes for version two point one", importance=0.9, age_days=1)
        svc._repo.rows[m.id] = m
    # An unrelated one that should not join the cluster.
    other = _mem("completely different topic about gardening", importance=0.9)
    svc._repo.rows[other.id] = other

    out = await svc.consolidate(
        None, workspace_id=WS, user_id=None,
        payload=ConsolidateIn(max_cluster_distance=0.15, promote_threshold=0.7),
    )
    assert out.clusters_created >= 1
    assert out.memories_promoted >= 1
    # A LONG_TERM memory now exists.
    lt = [m for m in svc._repo.rows.values() if m.layer == MemoryLayer.LONG_TERM]
    assert lt, "expected a promoted long-term memory"


@pytest.mark.asyncio
async def test_consolidate_noop_on_tiny_pool(svc):
    m = _mem("lonely memory")
    svc._repo.rows[m.id] = m
    out = await svc.consolidate(None, workspace_id=WS, user_id=None,
                                payload=ConsolidateIn())
    assert out.clusters_created == 0
    assert out.memories_promoted == 0
