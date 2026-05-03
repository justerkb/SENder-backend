"""Sender service with edge-case validation and custom exceptions."""

from datetime import datetime
from typing import Sequence, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Sender
from senders.schemas import SenderCreate, SenderUpdate
from errors.exceptions import (
    NotFoundException,
    BadRequestException,
    ConflictException,
    ForbiddenException,
)


async def list_senders(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 10,
    search: str | None = None,
    sort_by: str = "id",
    order: str = "desc",
) -> Sequence[Sender]:
    stmt = select(Sender)
    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(
            (Sender.name.ilike(like)) | (Sender.city.ilike(like))  # type: ignore[attr-defined]
        )

    sort_column = getattr(Sender, sort_by, Sender.id)
    if order == "asc":
        stmt = stmt.order_by(sort_column.asc())
    else:
        stmt = stmt.order_by(sort_column.desc())

    stmt = stmt.offset(skip).limit(limit)
    result = await session.exec(stmt)
    return result.all()


async def get_sender(session: AsyncSession, sender_id: int) -> Sender:
    sender = await session.get(Sender, sender_id)
    if not sender:
        raise NotFoundException(detail=f"Sender with id {sender_id} not found")
    return sender


async def get_sender_by_user_id(session: AsyncSession, user_id: int) -> Optional[Sender]:
    stmt = select(Sender).where(Sender.user_id == user_id)
    result = await session.exec(stmt)
    return result.first()


async def create_sender(
    session: AsyncSession, payload: SenderCreate, user_id: int | None = None
) -> Sender:
    # Edge case: duplicate email
    stmt = select(Sender).where(Sender.email == payload.email)
    result = await session.exec(stmt)
    if result.first():
        raise ConflictException(detail=f"Sender with email '{payload.email}' already exists")

    if user_id:
        existing = await get_sender_by_user_id(session, user_id)
        if existing:
            raise ConflictException(detail="You already have a sender profile")

    sender = Sender(**payload.model_dump(), user_id=user_id)
    session.add(sender)
    await session.commit()
    await session.refresh(sender)
    return sender


async def update_sender_full(
    session: AsyncSession, sender_id: int, payload: SenderCreate, current_user_id: int | None = None
) -> Sender:
    sender = await get_sender(session, sender_id)

    if current_user_id and sender.user_id and sender.user_id != current_user_id:
        raise ForbiddenException(detail="You can only update your own sender profile")

    if payload.email != sender.email:
        stmt = select(Sender).where(Sender.email == payload.email)
        result = await session.exec(stmt)
        if result.first():
            raise ConflictException(detail=f"Email '{payload.email}' is already used by another sender")

    for field, value in payload.model_dump().items():
        setattr(sender, field, value)
    sender.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(sender)
    return sender


async def update_sender_partial(
    session: AsyncSession, sender_id: int, payload: SenderUpdate, current_user_id: int | None = None
) -> Sender:
    sender = await get_sender(session, sender_id)

    if current_user_id and sender.user_id and sender.user_id != current_user_id:
        raise ForbiddenException(detail="You can only update your own sender profile")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise BadRequestException(detail="At least one field must be provided")

    if "email" in data and data["email"] != sender.email:
        stmt = select(Sender).where(Sender.email == data["email"])
        result = await session.exec(stmt)
        if result.first():
            raise ConflictException(detail=f"Email '{data['email']}' is already used by another sender")

    for field, value in data.items():
        setattr(sender, field, value)
    sender.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(sender)
    return sender


async def delete_sender(
    session: AsyncSession, sender_id: int, current_user_id: int | None = None, is_admin: bool = False
) -> None:
    sender = await get_sender(session, sender_id)

    if not is_admin and current_user_id and sender.user_id and sender.user_id != current_user_id:
        raise ForbiddenException(detail="You can only delete your own sender profile")

    # Edge case: cannot delete if sender has packages in_transit
    for pkg in sender.packages:
        if pkg.status in ("accepted", "in_transit"):
            raise BadRequestException(
                detail=f"Cannot delete sender: package #{pkg.id} is still active (status: {pkg.status})"
            )

    await session.delete(sender)
    await session.commit()
