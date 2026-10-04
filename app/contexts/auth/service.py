"""Auth context service — registration, login, MFA, token rotation."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.auth.models import (
    AuthProvider,
    Organization,
    PasswordResetToken,
    RefreshToken,
    User,
)
from app.contexts.auth.schemas import (
    LoginIn,
    RegisterIn,
    TokenOut,
    UserOut,
)
from app.core.config import settings
from app.core.exceptions import AuthError, ConflictError, NotFoundError
from app.core.security import (
    create_token,
    decode_token,
    generate_mfa_secret,
    generate_token,
    hash_password,
    mfa_provisioning_uri,
    verify_mfa,
    verify_password,
)
from app.core.tenant import set_current_user


def _hash_token(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


class AuthService:
    async def register(self, db: AsyncSession, payload: RegisterIn) -> TokenOut:
        existing = await db.execute(select(User).where(User.email == payload.email.lower()))
        if existing.scalar_one_or_none():
            raise ConflictError("Email already registered", details={"email": payload.email})

        user = User(
            email=payload.email.lower(),
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            provider=AuthProvider.EMAIL,
            is_active=True,
            is_verified=False,
        )
        db.add(user)
        await db.flush()

        # Provision a personal workspace lazily via workspace service on first login;
        # org is optional. Keep auth focused.
        return await self._issue_tokens(db, user)

    async def login(self, db: AsyncSession, payload: LoginIn, *, ip: str | None = None) -> TokenOut:
        res = await db.execute(select(User).where(User.email == payload.email.lower()))
        user = res.scalar_one_or_none()
        if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
            raise AuthError("Invalid email or password")
        if not user.is_active:
            raise AuthError("Account disabled")

        if user.mfa_enabled:
            if not payload.mfa_code or not user.mfa_secret or not verify_mfa(user.mfa_secret, payload.mfa_code):
                raise AuthError("MFA code required or invalid", details={"mfa_required": True})

        user.last_login_at = datetime.now(timezone.utc)
        set_current_user(_to_current(user))
        return await self._issue_tokens(db, user, ip=ip)

    async def refresh(self, db: AsyncSession, refresh_token: str) -> TokenOut:
        try:
            payload = decode_token(refresh_token)
        except Exception:
            raise AuthError("Invalid refresh token") from None
        if payload.get("type") != "refresh":
            raise AuthError("Wrong token type")

        user_id = uuid.UUID(payload["sub"])
        record = (
            await db.execute(
                select(RefreshToken).where(
                    RefreshToken.token_hash == _hash_token(refresh_token),
                    RefreshToken.revoked.is_(False),
                )
            )
        ).scalar_one_or_none()
        if not record:
            raise AuthError("Refresh token revoked")

        # Rotate: revoke the old, issue a new pair.
        record.revoked = True
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
        return await self._issue_tokens(db, user)

    async def logout(self, db: AsyncSession, refresh_token: str) -> None:
        record = (
            await db.execute(
                select(RefreshToken).where(RefreshToken.token_hash == _hash_token(refresh_token))
            )
        ).scalar_one_or_none()
        if record:
            record.revoked = True

    async def request_password_reset(self, db: AsyncSession, email: str) -> str:
        user = (
            await db.execute(select(User).where(User.email == email.lower()))
        ).scalar_one_or_none()
        if not user:  # do not leak existence
            return "ok"
        token = generate_token()
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=_hash_token(token),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        # In production: send email here. For dev we return/log the token.
        return token

    async def confirm_password_reset(self, db: AsyncSession, token: str, new_password: str) -> None:
        record = (
            await db.execute(
                select(PasswordResetToken).where(PasswordResetToken.token_hash == _hash_token(token))
            )
        ).scalar_one_or_none()
        if not record or record.used or record.expires_at < datetime.now(timezone.utc):
            raise AuthError("Invalid or expired token")
        user = (await db.execute(select(User).where(User.id == record.user_id))).scalar_one()
        user.hashed_password = hash_password(new_password)
        record.used = True

    # ── MFA ──────────────────────────────────────────────────
    async def setup_mfa(self, db: AsyncSession, user_id: uuid.UUID) -> tuple[str, str]:
        user = await self._get(db, user_id)
        secret = generate_mfa_secret()
        user.mfa_secret = secret  # not yet enabled until verified
        return secret, mfa_provisioning_uri(user.email, secret)

    async def enable_mfa(self, db: AsyncSession, user_id: uuid.UUID, code: str) -> None:
        user = await self._get(db, user_id)
        if not user.mfa_secret or not verify_mfa(user.mfa_secret, code):
            raise AuthError("Invalid MFA code")
        user.mfa_enabled = True

    async def disable_mfa(self, db: AsyncSession, user_id: uuid.UUID, code: str) -> None:
        user = await self._get(db, user_id)
        if not user.mfa_secret or not verify_mfa(user.mfa_secret, code):
            raise AuthError("Invalid MFA code")
        user.mfa_secret = None
        user.mfa_enabled = False

    async def get(self, db: AsyncSession, user_id: uuid.UUID) -> UserOut:
        return UserOut.model_validate(await self._get(db, user_id))

    async def _get(self, db: AsyncSession, user_id: uuid.UUID) -> User:
        user = (
            await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
        ).scalar_one_or_none()
        if not user:
            raise NotFoundError("User not found")
        return user

    # ── token issuance ───────────────────────────────────────
    async def _issue_tokens(
        self, db: AsyncSession, user: User, *, ip: str | None = None
    ) -> TokenOut:
        access = create_token(str(user.id), "access", extra={"email": user.email})
        refresh = create_token(str(user.id), "refresh")
        db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=_hash_token(refresh),
                expires_at=datetime.now(timezone.utc)
                + timedelta(days=settings.refresh_token_ttl_days),
                ip=ip,
            )
        )
        return TokenOut(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.access_token_ttl_minutes * 60,
            user=UserOut.model_validate(user),
        )


def _to_current(user: User):
    from app.core.tenant import CurrentUser

    return CurrentUser(user_id=user.id, email=user.email, org_id=user.org_id)


auth_service = AuthService()
