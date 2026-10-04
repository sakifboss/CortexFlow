# CortexFlow

> Production-grade, modular AI research platform — an extensible, enterprise-ready
> alternative to NotebookLM. Upload knowledge → organize → chat with citations →
> build knowledge graphs → run multi-agent research → quizzes & presentations.

CortexFlow is shipped as a **modular monolith** (one deployable, clean bounded
contexts) that is **microservice-extractable** by design. Every context has its
own `models / schemas / service / repository / router`, communicates via a typed
service interface, and is wired with **dependency injection** so it can be split
into a separate process later with zero refactor.

---

## ✨ What works out of the box

A full vertical slice, runnable on a laptop with one command:

```
Auth → Workspace → Notebook → Document upload
  → Parse (PyMuPDF / python-docx / markdown)
  → OCR (Tesseract, optional PaddleOCR)
  → Adaptive chunking
  → Embedding (Ollama bge / nomic / OpenAI-compatible)
  → Vector store (Qdrant, hybrid + metadata filters)
  → RAG with LangGraph agent (qwen2.5:3b via Ollama)
  → Strict citation engine (every claim grounded in a source span)
  → Streaming chat UI in Next.js with clickable citations
```

Other modules (Memory, Knowledge Graph, Billing, Admin, Analytics) ship as
**working but lighter** implementations behind the same interfaces so you can
extend them.

### 🎨 Studio — grounded artifact generation

The **Studio** tab on every notebook turns your sources into nine artifact
types, all grounded in your documents (same retrieval + citation engine as
chat):

| | Artifact | What you get |
|--|----------|--------------|
| 🧩 | **Create Artifact** | Free-form, prompt-driven markdown output |
| 🎙️ | **Audio Overview** | Two-host podcast script with in-browser playback (Web Speech API — no TTS backend) |
| 📑 | **Slide Deck** | Presentation slides with bullets + speaker notes |
| 🧠 | **Mind Map** | Interactive concept tree (React Flow) |
| 📄 | **Report** | Structured, cited long-form report |
| 🗂️ | **Flashcards** | Flip-card study deck with shuffle |
| ❓ | **Quiz** | Interactive multiple-choice with scoring + explanations |
| 📊 | **Infographic** | Headline stats + themed sections |
| 📋 | **Data Table** | Structured extraction with sort, filter, CSV export |

All nine live in **one** bounded context (`app/contexts/artifact/`): a single
`Artifact` model with a `kind` discriminator, one typed content schema per kind,
one generator registry, one service, and one router. Adding a tenth type is a
new enum member + content schema + generator entry — no new table or endpoint.

```
POST /workspaces/{ws}/notebooks/{nb}/artifacts   { "kind": "quiz", "options": {"count": 8} }
GET  /workspaces/{ws}/notebooks/{nb}/artifacts/kinds
GET  /workspaces/{ws}/notebooks/{nb}/artifacts/{id}
POST /workspaces/{ws}/notebooks/{nb}/artifacts/{id}/regenerate
```

Generation is synchronous by default; a Celery task
(`app.workers.tasks.generate_artifact`) wraps the same service for an
async/polling path.

---

## 🧱 Stack

| Layer | Tech |
|------|------|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind, shadcn/ui, TanStack Query, Zustand, Tiptap, React Flow |
| API | FastAPI, Pydantic v2, REST + WebSocket, OpenAPI |
| AI | Ollama (`qwen2.5:3b`), LangChain, LangGraph, LiteLLM router |
| Data | PostgreSQL, Redis, Qdrant, Neo4j, MinIO (S3), ElasticSearch |
| Jobs | Celery + RabbitMQ |
| Infra | Docker Compose, Kubernetes, NGINX, GitHub Actions |

---

## 🚀 Quickstart

```bash
cp .env.example .env          # edit secrets / Ollama host if needed
make pull-models              # ollama pull qwen2.5:3b  (and bge for embeddings)
make up                       # docker compose up -d --build
make migrate                  # apply DB migrations + create Qdrant collection
open http://localhost:3000
```

Default admin: `admin@cortexflow.io` / `changeme` (seeded on first migrate).

### Local dev (no Docker for app code)

```bash
make install-be && make install-fe
uvicorn app.main:app --reload --port 8000
cd frontend && pnpm dev
```

---

## 📁 Layout

```
cortexflow/
├── app/                          # FastAPI backend (modular monolith)
│   ├── main.py
│   ├── core/                     # config, security, db, redis, logging, DI
│   ├── contexts/                 # bounded contexts (DDD)
│   │   ├── auth/
│   │   ├── workspace/
│   │   ├── notebook/
│   │   ├── document/             # ingest + storage (MinIO)
│   │   ├── ingestion/            # parse / OCR / chunk pipeline
│   │   ├── embedding/
│   │   ├── vector/               # Qdrant hybrid search
│   │   ├── rag/                  # retrieval + grounding + answer
│   │   ├── agent/                # LangGraph multi-agent
│   │   ├── citation/
│   │   ├── memory/
│   │   ├── knowledge_graph/      # Neo4j
│   │   ├── search/
│   │   ├── quiz/
│   │   ├── presentation/
│   │   ├── billing/
│   │   ├── analytics/
│   │   └── admin/
│   ├── ai/                       # Ollama client, LiteLLM router, prompts
│   ├── workers/                  # Celery tasks
│   └── api/v1/                   # HTTP routers
├── alembic/
├── frontend/                     # Next.js 15 app
├── infra/                        # docker, k8s, nginx, terraform
├── docs/                         # architecture, ER, API, deployment
└── tests/
```

See **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**, **[docs/API.md](docs/API.md)**,
and **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for the deep dives.

---

## 🔐 Security

JWT (access + refresh), OAuth2 (Google/GitHub/Microsoft), MFA, RBAC with org/team/
workspace scopes, Argon2 password hashing, per-tenant row-level isolation,
rate limiting, audit logs, TLS termination at NGINX, encryption at rest in MinIO,
secret management via env / Vault. See [docs/SECURITY.md](docs/SECURITY.md).

---

## 🧠 AI philosophy

* **Grounded by default.** The RAG agent cannot emit an ungrounded sentence; the
  citation engine drops any claim lacking a retrieved source span.
* **Local-first.** Default model is `qwen2.5:3b` on Ollama. Swap providers
  (OpenAI/Anthropic/Gemini/DeepSeek/vLLM) via LiteLLM with one env var.
* **Multi-agent.** Specialized agents (Research, Writing, Citation, Memory, KG,
  Quiz, Presentation, Fact-Check, Debate) orchestrated by LangGraph.

---

## ⚖️ License

MIT. See [LICENSE](LICENSE).
