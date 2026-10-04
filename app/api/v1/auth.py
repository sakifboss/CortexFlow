"""Auth router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from app.contexts.auth.schemas import (
    LoginIn,
    MFASetupOut,
    MFAVerifyIn,
    PasswordResetConfirmIn,
    PasswordResetRequestIn,
    RefreshOut,
    RegisterIn,
    TokenOut,
    TokenRefreshIn,
    UserOut,
    UserUpdateIn,
)
from app.contexts.auth.service import auth_service
from app.core.deps import CurrentUserDep, DbDep
from app.services.audit import audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterIn, db: DbDep):
    return await auth_service.register(db, payload)


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, db: DbDep, request: Request):
    return await auth_service.login(db, payload, ip=request.client.host if request.client else None)


@router.post("/refresh", response_model=RefreshOut)
async def refresh(payload: TokenRefreshIn, db: DbDep):
    tokens = await auth_service.refresh(db, payload.refresh_token)
    return RefreshOut(access_token=tokens.access_token, expires_in=tokens.expires_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: TokenRefreshIn, db: DbDep):
    await auth_service.logout(db, payload.refresh_token)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUserDep, db: DbDep):
    return await auth_service.get(db, user.user_id)


@router.patch("/me", response_model=UserOut)
async def update_me(payload: UserUpdateIn, user: CurrentUserDep, db: DbDep):
    from sqlalchemy import select

    from app.contexts.auth.models import User

    u = (await db.execute(select(User).where(User.id == user.user_id))).scalar_one()
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(u, k, v)
    return await auth_service.get(db, user.user_id)


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
async def request_reset(payload: PasswordResetRequestIn, db: DbDep):
    token = await auth_service.request_password_reset(db, payload.email)
    # Dev-only: echo the token back. In prod this goes via email.
    return {"message": "If the email exists, a reset link was sent.", "dev_token": token}


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_reset(payload: PasswordResetConfirmIn, db: DbDep):
    await auth_service.confirm_password_reset(db, payload.token, payload.password)


@router.post("/mfa/setup", response_model=MFASetupOut)
async def setup_mfa(user: CurrentUserDep, db: DbDep):
    secret, uri = await auth_service.setup_mfa(db, user.user_id)
    return MFASetupOut(secret=secret, provisioning_uri=uri)


@router.post("/mfa/enable", status_code=status.HTTP_204_NO_CONTENT)
async def enable_mfa(payload: MFAVerifyIn, user: CurrentUserDep, db: DbDep):
    await auth_service.enable_mfa(db, user.user_id, payload.code)
    await audit(db, action="mfa.enable", target_type="user", target_id=str(user.user_id))


@router.post("/mfa/disable", status_code=status.HTTP_204_NO_CONTENT)
async def disable_mfa(payload: MFAVerifyIn, user: CurrentUserDep, db: DbDep):
    await auth_service.disable_mfa(db, user.user_id, payload.code)
    await audit(db, action="mfa.disable", target_type="user", target_id=str(user.user_id))
