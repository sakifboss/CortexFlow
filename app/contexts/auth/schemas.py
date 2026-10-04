"""Auth schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.schemas import IDModel, ORMModel, Timestamped


# ── Requests ─────────────────────────────────────────────────
class RegisterIn(ORMModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)

    @field_validator("password")
    @classmethod
    def _strong(cls, v: str) -> str:
        if not any(c.isupper() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("Password must contain an uppercase letter and a digit")
        return v


class LoginIn(ORMModel):
    email: EmailStr
    password: str
    mfa_code: str | None = None


class TokenRefreshIn(ORMModel):
    refresh_token: str


class PasswordResetRequestIn(ORMModel):
    email: EmailStr


class PasswordResetConfirmIn(ORMModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class MFASetupOut(ORMModel):
    secret: str
    provisioning_uri: str


class MFAVerifyIn(ORMModel):
    code: str = Field(min_length=6, max_length=8)


class UserUpdateIn(ORMModel):
    full_name: str | None = None
    avatar_url: str | None = None


# ── Responses ────────────────────────────────────────────────
class UserOut(IDModel, Timestamped):
    email: EmailStr
    full_name: str | None
    is_active: bool
    is_verified: bool
    is_superuser: bool
    mfa_enabled: bool
    avatar_url: str | None
    org_id: uuid.UUID | None


class TokenOut(ORMModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class RefreshOut(ORMModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
