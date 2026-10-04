"""
Security primitives: password hashing (Argon2), JWT (access + refresh),
and TOTP MFA. All algorithms are configurable via Settings.
"""
from __future__ import annotations

import base64
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import otpauth

from app.core.config import settings

_ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MiB
    parallelism=2,
)

TokenType = Literal["access", "refresh", "verification"]


# ── Passwords ────────────────────────────────────────────────
def hash_password(raw: str) -> str:
    return _ph.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, raw)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def needs_rehash(hashed: str) -> bool:
    return _ph.check_needs_rehash(hashed)


# ── JWT ──────────────────────────────────────────────────────
def _ttl(token_type: TokenType) -> timedelta:
    return {
        "access": timedelta(minutes=settings.access_token_ttl_minutes),
        "refresh": timedelta(days=settings.refresh_token_ttl_days),
        "verification": timedelta(hours=settings.verification_token_ttl_hours),
    }[token_type]


def create_token(
    subject: str,
    token_type: TokenType = "access",
    *,
    extra: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + _ttl(token_type),
        "jti": secrets.token_urlsafe(16),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])


# ── MFA (TOTP, RFC 6238) ─────────────────────────────────────
def _totp(secret: str):
    return otpauth.TOTP.from_b32encode(secret)


def generate_mfa_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("utf-8").rstrip("=")


def mfa_provisioning_uri(email: str, secret: str) -> str:
    return _totp(secret).to_uri(email, settings.app_name)


def verify_mfa(secret: str, code: str) -> bool:
    try:
        return _totp(secret).verify(code=int(code))
    except Exception:
        return False


# ── Misc ─────────────────────────────────────────────────────
def generate_token(nbytes: int = 32) -> str:
    """Random URL-safe token (for password reset, email verify, invites)."""
    return secrets.token_urlsafe(nbytes)
