"""Billing context (Phase 5) — plans, subscriptions, invoices, usage events."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.models import TimestampMixin, UUIDPK


class PlanTier(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    ENDED = "ended"


class Subscription(Base, UUIDPK, TimestampMixin):
    __tablename__ = "subscriptions"

    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    tier: Mapped[PlanTier] = mapped_column(Enum(PlanTier, name="plan_tier"))
    status: Mapped[SubscriptionStatus] = mapped_column(Enum(SubscriptionStatus, name="sub_status"))
    stripe_customer_id: Mapped[str | None] = mapped_column(String(120), default=None)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(120), default=None)
    seats: Mapped[int] = mapped_column(Integer, default=1)
    current_period_end: Mapped[str | None] = mapped_column(String(40), default=None)


class Invoice(Base, UUIDPK, TimestampMixin):
    __tablename__ = "invoices"

    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(8), default="usd")
    status: Mapped[str] = mapped_column(String(40), default="open")
    stripe_invoice_id: Mapped[str | None] = mapped_column(String(120), default=None)
    pdf_url: Mapped[str | None] = mapped_column(String(512), default=None)


class UsageEvent(Base, UUIDPK, TimestampMixin):
    """Append-only metering: tokens, storage, embeddings — feeds usage-based billing."""

    __tablename__ = "usage_events"

    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    metric: Mapped[str] = mapped_column(String(60))  # llm_tokens, storage_bytes, embed_calls
    units: Mapped[int] = mapped_column(Integer)
    unit_cost_cents: Mapped[float] = mapped_column(Numeric(10, 6), default=0)
    properties: Mapped[dict | None] = mapped_column(JSONB, default=None)
