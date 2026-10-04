"""
Agent context (Phase 4).

Persistence for LangGraph agent runs: each run is a stateful, resumable
multi-agent workflow. Steps record tool calls, intermediate reasoning, and
token usage. The runtime itself lives in app.ai.agents.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.models import TenantMixin, TimestampMixin, UUIDPK


class AgentKind(str, enum.Enum):
    RESEARCH = "research"
    WRITING = "writing"
    SUMMARY = "summary"
    TEACHING = "teaching"
    QUIZ = "quiz"
    PRESENTATION = "presentation"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    CITATION = "citation"
    MEMORY = "memory"
    PLANNING = "planning"
    DATA_ANALYSIS = "data_analysis"
    CODING = "coding"
    FACT_CHECK = "fact_check"
    DEBATE = "debate"


class AgentRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_HUMAN = "awaiting_human"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRun(Base, UUIDPK, TimestampMixin, TenantMixin):
    __tablename__ = "agent_runs"
    __table_args__ = (Index("ix_run_ws_status", "workspace_id", "status"),)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    notebook_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)

    kind: Mapped[AgentKind] = mapped_column(Enum(AgentKind, name="agent_kind"))
    status: Mapped[AgentRunStatus] = mapped_column(Enum(AgentRunStatus, name="agent_run_status"))
    goal: Mapped[str] = mapped_column(Text)
    plan: Mapped[list | None] = mapped_column(JSONB, default=None)
    result: Mapped[dict | None] = mapped_column(JSONB, default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float | None] = mapped_column(default=None)


class AgentStep(Base, UUIDPK, TimestampMixin, TenantMixin):
    __tablename__ = "agent_steps"
    __table_args__ = (Index("ix_step_run", "run_id", "created_at"),)

    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"))
    agent: Mapped[str] = mapped_column(String(60))
    step: Mapped[int] = mapped_column(Integer)
    thought: Mapped[str | None] = mapped_column(Text, default=None)
    action: Mapped[str | None] = mapped_column(String(200), default=None)
    action_input: Mapped[dict | None] = mapped_column(JSONB, default=None)
    observation: Mapped[dict | None] = mapped_column(JSONB, default=None)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
