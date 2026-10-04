"""
Embedding gateway.

Default backend: Ollama `nomic-embed-text` (or bge-m3). Falls back to a local
sentence-transformers model if Ollama is unavailable, so the platform always
boots. Vectors are L2-normalized for cosine search in Qdrant.
"""
from __future__ import annotations

import asyncio
from typing import Any

import numpy as np
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


class EmbeddingGateway:
    def __init__(self, *, provider: str | None = None, model: str | None = None) -> None:
        self.provider = provider or settings.embedding_provider
        self.model = model or settings.embedding_model
        self._dim = settings.embedding_dim
        self._st_model: Any = None

    @property
    def dim(self) -> int:
        return self._dim

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self.provider == "ollama":
            try:
                return await self._ollama_embed(texts)
            except Exception as exc:  # pragma: no cover - fallback path
                logger.warning("Ollama embedding failed ({}); using local fallback.", exc)
                return await self._local_embed(texts)
        return await self._local_embed(texts)

    async def embed_one(self, text: str) -> list[float]:
        out = await self.embed([text])
        return out[0]

    # ── backends ─────────────────────────────────────────────
    async def _ollama_embed(self, texts: list[str]) -> list[list[float]]:
        import ollama

        async with ollama.AsyncClient(host=settings.ollama_base_url) as client:
            # Ollama supports batch input
            resp = await client.embed(model=self.model, input=texts)
        vecs = resp["embeddings"] if isinstance(resp, dict) else resp.embeddings
        return [_normalize(v) for v in vecs]

    async def _local_embed(self, texts: list[str]) -> list[list[float]]:
        await self._ensure_local()
        loop = asyncio.get_running_loop()
        vecs = await loop.run_in_executor(None, self._st_model.encode, texts)
        return [_normalize(list(v)) for v in vecs]

    async def _ensure_local(self) -> None:
        if self._st_model is None:
            from sentence_transformers import SentenceTransformer

            self._st_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            self._dim = self._st_model.get_sentence_embedding_dimension()
            logger.info("Loaded local embedding model (dim={}).", self._dim)


def _normalize(vec: list[float]) -> list[float]:
    arr = np.asarray(vec, dtype=np.float32)
    norm = float(np.linalg.norm(arr))
    if norm > 0:
        arr = arr / norm
    return arr.tolist()


embeddings = EmbeddingGateway()
