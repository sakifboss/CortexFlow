"""Auth context — users, organizations, OAuth identities, MFA, sessions."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.models import TimestampMixin, UUIDPK


class AuthProvider(str, enum.Enum):
    EMAIL = "email"
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"


class Organization(Base, UUIDPK, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    members: Mapped[list["User"]] = relationship(back_populates="org")


class User(Base, UUIDPK, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(120), default=None)
    hashed_password: Mapped[str | None] = mapped_column(String(255), default=None)
    provider: Mapped[AuthProvider] = mapped_column(
        Enum(AuthProvider, name="auth_provider"), default=AuthProvider.EMAIL
    )
    provider_subject: Mapped[str | None] = mapped_column(String(255), default=None, index=True)

    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), default=None
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    # MFA
    mfa_secret: Mapped[str | None] = mapped_column(String(64), default=None)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    avatar_url: Mapped[str | None] = mapped_column(String(512), default=None)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    org: Mapped[Organization | None] = relationship(back_populates="members")


class OAuthAccount(Base, UUIDPK, TimestampMixin):
    """Linked third-party identities for a user (multi-link)."""

    __tablename__ = "oauth_accounts"
    __table_args__ = (UniqueConstraint("provider", "provider_subject", name="uq_provider_subject"),)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    provider: Mapped[AuthProvider] = mapped_column(Enum(AuthProvider, name="auth_provider"))
    provider_subject: Mapped[str] = mapped_column(String(255))
    refresh_token: Mapped[str | None] = mapped_column(String(1024), default=None)
    scopes: Mapped[str | None] = mapped_column(String(512), default=None)


class RefreshToken(Base, UUIDPK, TimestampMixin):
    """Persisted refresh tokens for revocation & rotation."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    user_agent: Mapped[str | None] = mapped_column(String(255), default=None)
    ip: Mapped[str | None] = mapped_column(String(64), default=None)


class PasswordResetToken(Base, UUIDPK, TimestampMixin):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (Index("ix_prt_user_active", "user_id", "expires_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)
