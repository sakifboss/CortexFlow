# CortexFlow — Agent Memory System (Priority 1) — Changelog

This changeset turns the Memory context from a models-only stub into a fully
working, tested vertical slice: backend logic, API routes, and a frontend
console. It also fixes a latent, codebase-wide ORM mapping bug found along the
way.

## What this is (and isn't)

Your uploaded feature list spans ~150 features across 10 priority tiers — that's
a multi-team, multi-quarter roadmap, not a single deliverable. Rather than ship
thousands of untested stub files, this implements **one** module properly, end
to end, the way your README says the codebase is meant to grow: one bounded
context at a time, behind the existing interfaces.

Chosen module: **Agent Memory System** (Priority 1, and the "WOW" differentiator
you flagged). It also gives the other three candidates (Reasoning, Knowledge
Graph, Multi-Agent) a foundation, since they all read/write memory.

## Files added

Backend
- `app/contexts/memory/schemas.py` — Pydantic v2 request/response models
  (write, recall, consolidate, forget) matching the codebase's `ORMModel` base.
- `app/contexts/memory/repository.py` — async SQLAlchemy data access,
  tenant-scoped, no business logic.
- `app/contexts/memory/service.py` — the core memory engine:
  - **write**: seed importance (per-layer heuristic), embed, index in Qdrant.
  - **recall**: blended ranking = `0.65·cosine + 0.25·effective_importance +
    0.10·recency`; reinforces recalled memories (access bump).
  - **consolidate**: greedy cosine clustering of episodic memories → LLM
    summary per cluster → promote high-signal clusters to `long_term`.
  - **forget**: Ebbinghaus-style exponential decay
    (`importance·exp(-decay_rate·age_days) + access_bonus`); prunes below a
    floor but never touches `long_term`.
- `app/api/v1/memory.py` — REST router:
  `GET/POST /workspaces/{ws}/memory`, `POST …/recall`, `POST …/consolidate`,
  `POST …/forget`, `DELETE …/{id}`. RBAC via `WorkspaceDep`, audit-logged.

Frontend
- `frontend/services/memory.ts` — typed API client for the memory routes.
- `frontend/hooks/use-memory.ts` — React Query hooks (list/write/recall/
  consolidate/forget/delete) scoped to the active workspace.
- `frontend/app/(app)/memory/page.tsx` — interactive console: store memories by
  layer, recall with visible scores, browse by layer with counts, one-click
  consolidate / forget. Replaces the previous ComingSoon placeholder.

Tests
- `tests/test_memory_service.py` — 16 tests, **all passing**, covering the pure
  math (cosine, decay, reinforcement, clustering, centroid) and async behaviour
  (write, recall ranking, access bump, min-importance filter, forget dry-run vs
  real, long-term sparing, consolidation + promotion). Runs with **no external
  infra** — embeddings/LLM/vector store are stubbed.
- `conftest.py`, `pytest.ini`, `tests/__init__.py` — test bootstrap.

## Files changed

- `app/main.py` — import and register the memory router.
- `app/core/db.py` — **bug fix (codebase-wide):** `Base` now uses
  `kw_only=True`. Tenant-scoped models compose plain mixins where
  `TenantMixin.workspace_id` (no default) follows defaulted columns from other
  mixins; on SQLAlchemy 2.0.51 this raised *"non-default argument follows
  default argument"* and **prevented `agent`, `document`, `knowledge_graph`,
  `memory`, and `notebook` models from mapping at all**. `kw_only=True` makes
  mapped columns keyword-only and removes the ordering constraint. Model
  construction is now explicit (`Memory(workspace_id=…, …)`), which the codebase
  already did everywhere.
- `requirements-dev.txt` — added `pytest`, `pytest-asyncio`.

## Known pre-existing issue (NOT introduced here, NOT fixed here)

With the `kw_only` fix in place, `document` and `notebook` models surface a
separate, older problem: a `Mapped[dict]` column named `settings` (and
`MetadataMixin.meta`) has no resolvable Core type on newer SQLAlchemy
(`MappedAnnotationError`). This predates this changeset and is out of scope. The
fix is to type those columns explicitly, e.g.
`Mapped[dict] = mapped_column(JSONB, …)` or
`Mapped[dict[str, Any]] = mapped_column(MutableDict.as_mutable(JSONB))`.

## Running the tests

```bash
cd CortexFlow
pip install -r requirements-dev.txt
pytest tests/test_memory_service.py -v
```

## Try the API (once infra is up via docker-compose)

```bash
# store
curl -X POST localhost:8000/api/v1/workspaces/$WS/memory \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"content":"User deploys on Render with FastAPI","layer":"semantic"}'

# recall
curl -X POST localhost:8000/api/v1/workspaces/$WS/memory/recall \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"query":"where does the user deploy","limit":5}'

# consolidate / forget
curl -X POST localhost:8000/api/v1/workspaces/$WS/memory/consolidate -H "Authorization: Bearer $TOKEN" -d '{}'
curl -X POST localhost:8000/api/v1/workspaces/$WS/memory/forget -H "Authorization: Bearer $TOKEN" -d '{"dry_run":true}'
```
