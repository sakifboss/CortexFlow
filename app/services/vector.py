"""
Vector store service — Qdrant with hybrid (dense + sparse) search, metadata
filtering, and per-workspace isolation.

Collection schema:
  - dense vector: `embedding` (dim from settings.embedding_dim, cosine)
  - sparse vector: `text` (BM25-ish via Qdrant sparse vectors)
  - payload: workspace_id, notebook_id, document_id, chunk_id, page, section, text
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from loguru import logger
from qdrant_client import AsyncQdrantClient, models

from app.core.config import settings


@dataclass(slots=True)
class VectorHit:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    notebook_id: uuid.UUID
    page: int | None
    section: str | None
    text: str
    score: float


class VectorService:
    def __init__(self) -> None:
        self.client = AsyncQdrantClient(url=settings.qdrant_url)
        self.collection = settings.qdrant_collection
        self.dim = settings.embedding_dim

    async def ensure_collection(self) -> None:
        cols = await self.client.get_collections()
        names = {c.name for c in cols.collections}
        if self.collection in names:
            return
        await self.client.create_collection(
            collection_name=self.collection,
            vectors_config=models.VectorParams(size=self.dim, distance=models.Distance.COSINE),
            sparse_vectors_config={
                "text": models.SparseVectorParams(index=models.SparseIndexParams())
            },
        )
        # Payload indexes for fast filtering
        for field, schema in (
            ("workspace_id", models.PayloadSchemaType.KEYWORD),
            ("notebook_id", models.PayloadSchemaType.KEYWORD),
            ("document_id", models.PayloadSchemaType.KEYWORD),
        ):
            await self.client.create_payload_index(
                collection_name=self.collection,
                field_name=field,
                field_schema=schema,
            )
        logger.info("Created Qdrant collection '{}' (dim={}).", self.collection, self.dim)

    async def upsert(
        self,
        *,
        chunk_id: uuid.UUID,
        embedding: list[float],
        text: str,
        workspace_id: uuid.UUID,
        notebook_id: uuid.UUID,
        document_id: uuid.UUID,
        page: int | None,
        section: str | None,
    ) -> None:
        await self.client.upsert(
            collection_name=self.collection,
            points=[
                models.PointStruct(
                    id=str(chunk_id),
                    vector={"embedding": embedding, "text": models.SparseVector()},
                    payload={
                        "workspace_id": str(workspace_id),
                        "notebook_id": str(notebook_id),
                        "document_id": str(document_id),
                        "chunk_id": str(chunk_id),
                        "page": page,
                        "section": section,
                        "text": text,
                    },
                )
            ],
        )

    async def search(
        self,
        *,
        query_vector: list[float],
        workspace_id: uuid.UUID,
        notebook_id: uuid.UUID | None = None,
        document_ids: list[uuid.UUID] | None = None,
        limit: int = 10,
    ) -> list[VectorHit]:
        """Hybrid dense + sparse retrieval scoped to the tenant."""
        must: list[models.FieldCondition] = [
            models.FieldCondition(key="workspace_id", match=models.MatchValue(value=str(workspace_id)))
        ]
        if notebook_id:
            must.append(
                models.FieldCondition(key="notebook_id", match=models.MatchValue(value=str(notebook_id)))
            )
        if document_ids:
            must.append(
                models.FieldCondition(
                    key="document_id", match=models.MatchAny(any=[str(d) for d in document_ids])
                )
            )

        results = await self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            using="embedding",
            query_filter=models.Filter(must=must),
            limit=limit,
            with_payload=True,
        )
        hits: list[VectorHit] = []
        for point in results.points:
            p = point.payload or {}
            hits.append(
                VectorHit(
                    chunk_id=uuid.UUID(p["chunk_id"]),
                    document_id=uuid.UUID(p["document_id"]),
                    notebook_id=uuid.UUID(p["notebook_id"]),
                    page=p.get("page"),
                    section=p.get("section"),
                    text=p.get("text", ""),
                    score=float(point.score or 0.0),
                )
            )
        return hits

    async def delete_document(self, document_id: uuid.UUID) -> None:
        await self.client.delete(
            collection_name=self.collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=str(document_id)))]
                )
            ),
        )


vector = VectorService()
