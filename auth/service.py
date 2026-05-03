"""Auth business logic – register, login, token refresh."""

from datetime import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import User
from auth.schemas import UserRegister, UserLogin
from auth.utils import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from auth.redis_blocklist import add_to_blocklist
from errors.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)


async def register_user(session: AsyncSession, payload: UserRegister) -> User:
    # Check username uniqueness
    stmt = select(User).where(User.username == payload.username)
    result = await session.exec(stmt)
    if result.first():
        raise ConflictException(detail=f"Username '{payload.username}' is already taken")

    # Check email uniqueness
    stmt = select(User).where(User.email == payload.email)
    result = await session.exec(stmt)
    if result.first():
        raise ConflictException(detail=f"Email '{payload.email}' is already registered")

    user = User(
        username=payload.username,
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def login_user(session: AsyncSession, payload: UserLogin) -> dict:
    stmt = select(User).where(User.username == payload.username)
    result = await session.exec(stmt)
    user = result.first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedException(detail="Invalid username or password")

    if not user.is_active:
        raise ForbiddenException(detail="Account is deactivated")

    access = create_access_token(user.id, user.username, user.role)
    refresh = create_refresh_token(user.id)
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


async def refresh_tokens(session: AsyncSession, refresh_token: str) -> dict:
    import jwt as pyjwt

    try:
        payload = decode_token(refresh_token)
    except pyjwt.ExpiredSignatureError:
        raise UnauthorizedException(detail="Refresh token expired")
    except pyjwt.InvalidTokenError:
        raise UnauthorizedException(detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedException(detail="Invalid token type")

    user_id = int(payload["sub"])
    user = await session.get(User, user_id)
    if not user:
        raise NotFoundException(detail="User not found")
    if not user.is_active:
        raise UnauthorizedException(detail="Account is deactivated")

    # Blocklist old refresh token
    jti = refresh_token[-16:]
    exp = payload.get("exp", 0)
    import time
    ttl = max(int(exp - time.time()), 1)
    await add_to_blocklist(jti, ttl)

    access = create_access_token(user.id, user.username, user.role)
    new_refresh = create_refresh_token(user.id)
    return {"access_token": access, "refresh_token": new_refresh, "token_type": "bearer"}


async def logout_user(access_token: str) -> None:
    """Add the access token to the blocklist so it can't be reused."""
    import jwt as pyjwt
    import time

    try:
        payload = decode_token(access_token)
    except pyjwt.InvalidTokenError:
        return  # already invalid, nothing to blocklist

    jti = access_token[-16:]
    exp = payload.get("exp", 0)
    ttl = max(int(exp - time.time()), 1)
    await add_to_blocklist(jti, ttl)


async def get_user_by_id(session: AsyncSession, user_id: int) -> User:
    user = await session.get(User, user_id)
    if not user:
        raise NotFoundException(detail=f"User with id {user_id} not found")
    return user
