"""
Artifacts (Studio) router.

    GET    /workspaces/{ws}/notebooks/{nb}/artifacts            list (summaries)
    POST   /workspaces/{ws}/notebooks/{nb}/artifacts            generate
    GET    /workspaces/{ws}/notebooks/{nb}/artifacts/kinds      static catalog
    GET    /workspaces/{ws}/notebooks/{nb}/artifacts/{id}       full artifact
    PATCH  /workspaces/{ws}/notebooks/{nb}/artifacts/{id}       edit title/content
    POST   /workspaces/{ws}/notebooks/{nb}/artifacts/{id}/regenerate
    DELETE /workspaces/{ws}/notebooks/{nb}/artifacts/{id}       remove

Generation is synchronous (like ``/chat``): the POST returns the finished
artifact with ``status`` ``ready`` or ``failed``.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.contexts.artifact.models import ArtifactKind
from app.contexts.artifact.schemas import (
    KIND_CATALOG,
    ArtifactGenerateIn,
    ArtifactOut,
    ArtifactSummary,
    ArtifactUpdateIn,
    KindInfo,
)
from app.contexts.artifact.service import artifact_service
from app.core.deps import DbDep, WorkspaceDep
from app.services.audit import audit

router = APIRouter(
    prefix="/workspaces/{workspace_id}/notebooks/{notebook_id}/artifacts",
    tags=["artifacts"],
)


@router.get("/kinds", response_model=list[KindInfo])
async def list_kinds(ws: WorkspaceDep):
    """Static catalog powering the Studio 'create' grid."""
    return KIND_CATALOG


@router.get("", response_model=list[ArtifactSummary])
async def list_artifacts(
    notebook_id: uuid.UUID,
    ws: WorkspaceDep,
    db: DbDep,
    kind: ArtifactKind | None = Query(default=None),
):
    return await artifact_service.list(db, notebook_id=notebook_id, kind=kind)


@router.post("", response_model=ArtifactOut, status_code=status.HTTP_201_CREATED)
async def generate_artifact(
    notebook_id: uuid.UUID,
    payload: ArtifactGenerateIn,
    ws: WorkspaceDep,
    db: DbDep,
):
    art = await artifact_service.generate(
        db,
        workspace_id=ws.workspace_id,
        notebook_id=notebook_id,
        user_id=ws.user_id,
        payload=payload,
    )
    await audit(
        db,
        action="artifact.generate",
        target_type="artifact",
        target_id=str(art.id),
        payload={"kind": art.kind.value, "status": art.status.value},
    )
    return art


@router.get("/{artifact_id}", response_model=ArtifactOut)
async def get_artifact(artifact_id: uuid.UUID, ws: WorkspaceDep, db: DbDep):
    return await artifact_service.get(db, artifact_id=artifact_id, workspace_id=ws.workspace_id)


@router.patch("/{artifact_id}", response_model=ArtifactOut)
async def update_artifact(
    artifact_id: uuid.UUID, payload: ArtifactUpdateIn, ws: WorkspaceDep, db: DbDep
):
    return await artifact_service.update(
        db, artifact_id=artifact_id, workspace_id=ws.workspace_id, payload=payload
    )


@router.post("/{artifact_id}/regenerate", response_model=ArtifactOut)
async def regenerate_artifact(artifact_id: uuid.UUID, ws: WorkspaceDep, db: DbDep):
    art = await artifact_service.regenerate(
        db, artifact_id=artifact_id, workspace_id=ws.workspace_id, user_id=ws.user_id
    )
    await audit(
        db, action="artifact.regenerate", target_type="artifact", target_id=str(art.id)
    )
    return art


@router.delete("/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact(artifact_id: uuid.UUID, ws: WorkspaceDep, db: DbDep):
    await artifact_service.delete(db, artifact_id=artifact_id, workspace_id=ws.workspace_id)
    await audit(
        db, action="artifact.delete", target_type="artifact", target_id=str(artifact_id)
    )
