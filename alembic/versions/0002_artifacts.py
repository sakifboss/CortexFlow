"""artifacts — Studio generated outputs

Revision ID: 0002_artifacts
Revises: 0001_initial
Create Date: 2026-07-05 10:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_artifacts"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ARTIFACT_KINDS = (
    "CUSTOM", "AUDIO_OVERVIEW", "SLIDE_DECK", "MIND_MAP", "REPORT",
    "FLASHCARDS", "QUIZ", "INFOGRAPHIC", "DATA_TABLE",
)
ARTIFACT_STATUSES = ("PENDING", "GENERATING", "READY", "FAILED")


def upgrade() -> None:
    op.create_table(
        "artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "notebook_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notebooks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.Enum(*ARTIFACT_KINDS, name="artifact_kind"), nullable=False),
        sa.Column(
            "status",
            sa.Enum(*ARTIFACT_STATUSES, name="artifact_status"),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("title", sa.String(300), server_default="Untitled artifact", nullable=False),
        sa.Column("prompt", sa.Text),
        sa.Column("content", postgresql.JSONB),
        sa.Column("citations", postgresql.JSONB),
        sa.Column("source_document_ids", postgresql.JSONB),
        sa.Column("model", sa.String(120)),
        sa.Column("tokens_used", sa.Integer, server_default="0", nullable=False),
        sa.Column("took_ms", sa.Integer, server_default="0", nullable=False),
        sa.Column("error", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_artifacts_notebook", "artifacts", ["notebook_id"])
    op.create_index("ix_artifacts_workspace", "artifacts", ["workspace_id"])
    op.create_index("ix_artifact_notebook_kind", "artifacts", ["notebook_id", "kind"])
    op.create_index("ix_artifact_notebook_created", "artifacts", ["notebook_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_artifact_notebook_created", table_name="artifacts")
    op.drop_index("ix_artifact_notebook_kind", table_name="artifacts")
    op.drop_index("ix_artifacts_workspace", table_name="artifacts")
    op.drop_index("ix_artifacts_notebook", table_name="artifacts")
    op.drop_table("artifacts")
    op.execute("DROP TYPE IF EXISTS artifact_kind")
    op.execute("DROP TYPE IF EXISTS artifact_status")
