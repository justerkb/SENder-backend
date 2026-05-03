"""Auth routes – register, login, logout, refresh, me, email confirm, password reset."""

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, status, Path
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from db import get_session
from auth.schemas import (
    UserRegister,
    UserLogin,
    TokenResponse,
    RefreshRequest,
    UserRead,
    UserUpdate,
    PasswordChange,
    ForgotPasswordRequest,
)
from auth import service as auth_service
from auth.deps import get_current_user
from auth.utils import verify_password, hash_password
from errors.exceptions import BadRequestException, NotFoundException
from models import User

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    payload: UserRegister,
    session: AsyncSession = Depends(get_session),
) -> dict:
    user = await auth_service.register_user(session, payload)

    # Trigger confirmation email via Celery background task
    try:
        from tasks.email_tasks import send_confirmation_email

        token = secrets.token_urlsafe(32)
        user.confirmation_token = token
        await session.commit()
        await session.refresh(user)

        send_confirmation_email.delay(
            user_email=user.email,
            username=user.username,
            token=token,
        )
    except Exception:
        pass  # Don't fail registration if Celery is down

    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login and receive JWT tokens",
)
async def login(
    payload: UserLogin,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await auth_service.login_user(session, payload)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token using refresh token",
)
async def refresh(
    payload: RefreshRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await auth_service.refresh_tokens(session, payload.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout and blocklist current token",
)
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> dict:
    await auth_service.logout_user(credentials.credentials)
    return {"detail": "Successfully logged out"}


@router.get(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
)
async def get_me(
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> dict:
    user_id = int(current_user["sub"])
    user = await auth_service.get_user_by_id(session, user_id)
    return user


@router.patch(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update current user profile",
)
async def update_me(
    payload: UserUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> dict:
    from datetime import datetime

    user_id = int(current_user["sub"])
    user = await auth_service.get_user_by_id(session, user_id)

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise BadRequestException(detail="At least one field must be provided")

    for field, value in data.items():
        setattr(user, field, value)
    user.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(user)
    return user


@router.post(
    "/me/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change current user password",
)
async def change_password(
    payload: PasswordChange,
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> dict:
    from datetime import datetime

    user_id = int(current_user["sub"])
    user = await auth_service.get_user_by_id(session, user_id)

    if not verify_password(payload.old_password, user.password_hash):
        raise BadRequestException(detail="Current password is incorrect")

    user.password_hash = hash_password(payload.new_password)
    user.updated_at = datetime.utcnow()
    await session.commit()
    return {"detail": "Password updated successfully"}


# ──────────────────────────────────────────────────────────
# Email Confirmation
# ──────────────────────────────────────────────────────────

@router.post(
    "/confirm-email/{token}",
    status_code=status.HTTP_200_OK,
    summary="Confirm email address using the token from the confirmation email",
)
async def confirm_email(
    token: Annotated[str, Path()],
    session: AsyncSession = Depends(get_session),
) -> dict:
    stmt = select(User).where(User.confirmation_token == token)
    result = await session.exec(stmt)
    user = result.first()

    if not user:
        raise NotFoundException(detail="Invalid or expired confirmation token")

    user.email_confirmed = True
    user.confirmation_token = None
    await session.commit()
    return {"detail": "Email confirmed successfully"}


# ──────────────────────────────────────────────────────────
# Forgot / Reset Password
# ──────────────────────────────────────────────────────────

@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    summary="Request a password reset email",
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    stmt = select(User).where(User.email == payload.email)
    result = await session.exec(stmt)
    user = result.first()

    # Always return success (don't reveal if email exists)
    if user:
        try:
            from tasks.email_tasks import send_password_reset_email

            token = secrets.token_urlsafe(32)
            user.confirmation_token = token
            await session.commit()

            send_password_reset_email.delay(
                user_email=user.email,
                username=user.username,
                token=token,
            )
        except Exception:
            pass

    return {"detail": "If the email is registered, a reset link has been sent"}
