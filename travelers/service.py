"""Traveler service with edge-case validation and custom exceptions."""

from datetime import datetime
from typing import Sequence, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Traveler
from travelers.schemas import TravelerCreate, TravelerUpdate
from errors.exceptions import (
    NotFoundException,
    BadRequestException,
    ConflictException,
    ForbiddenException,
)


async def list_travelers(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 10,
    search: str | None = None,
    sort_by: str = "id",
    order: str = "desc",
) -> Sequence[Traveler]:
    stmt = select(Traveler)
    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(
            (Traveler.name.ilike(like)) | (Traveler.bio.ilike(like))  # type: ignore[attr-defined]
        )

    # Dynamic sorting
    sort_column = getattr(Traveler, sort_by, Traveler.id)
    if order == "asc":
        stmt = stmt.order_by(sort_column.asc())
    else:
        stmt = stmt.order_by(sort_column.desc())

    stmt = stmt.offset(skip).limit(limit)
    result = await session.exec(stmt)
    return result.all()


async def get_traveler(session: AsyncSession, traveler_id: int) -> Traveler:
    traveler = await session.get(Traveler, traveler_id)
    if not traveler:
        raise NotFoundException(detail=f"Traveler with id {traveler_id} not found")
    return traveler


async def get_traveler_by_user_id(session: AsyncSession, user_id: int) -> Optional[Traveler]:
    stmt = select(Traveler).where(Traveler.user_id == user_id)
    result = await session.exec(stmt)
    return result.first()


async def create_traveler(
    session: AsyncSession, payload: TravelerCreate, user_id: int | None = None
) -> Traveler:
    # Edge case: duplicate email
    stmt = select(Traveler).where(Traveler.email == payload.email)
    result = await session.exec(stmt)
    if result.first():
        raise ConflictException(detail=f"Traveler with email '{payload.email}' already exists")

    # Edge case: user already has a traveler profile
    if user_id:
        existing = await get_traveler_by_user_id(session, user_id)
        if existing:
            raise ConflictException(detail="You already have a traveler profile")

    traveler = Traveler(**payload.model_dump(), user_id=user_id)
    session.add(traveler)
    await session.commit()
    await session.refresh(traveler)
    return traveler


async def update_traveler_full(
    session: AsyncSession, traveler_id: int, payload: TravelerCreate, current_user_id: int | None = None
) -> Traveler:
    traveler = await get_traveler(session, traveler_id)

    # Authorization: only owner can update
    if current_user_id and traveler.user_id and traveler.user_id != current_user_id:
        raise ForbiddenException(detail="You can only update your own traveler profile")

    # Edge case: email uniqueness on update
    if payload.email != traveler.email:
        stmt = select(Traveler).where(Traveler.email == payload.email)
        result = await session.exec(stmt)
        if result.first():
            raise ConflictException(detail=f"Email '{payload.email}' is already used by another traveler")

    for field, value in payload.model_dump().items():
        setattr(traveler, field, value)
    traveler.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(traveler)
    return traveler


async def update_traveler_partial(
    session: AsyncSession, traveler_id: int, payload: TravelerUpdate, current_user_id: int | None = None
) -> Traveler:
    traveler = await get_traveler(session, traveler_id)

    if current_user_id and traveler.user_id and traveler.user_id != current_user_id:
        raise ForbiddenException(detail="You can only update your own traveler profile")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise BadRequestException(detail="At least one field must be provided")

    # Edge case: email uniqueness
    if "email" in data and data["email"] != traveler.email:
        stmt = select(Traveler).where(Traveler.email == data["email"])
        result = await session.exec(stmt)
        if result.first():
            raise ConflictException(detail=f"Email '{data['email']}' is already used by another traveler")

    for field, value in data.items():
        setattr(traveler, field, value)
    traveler.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(traveler)
    return traveler


async def delete_traveler(
    session: AsyncSession, traveler_id: int, current_user_id: int | None = None, is_admin: bool = False
) -> None:
    traveler = await get_traveler(session, traveler_id)

    if not is_admin and current_user_id and traveler.user_id and traveler.user_id != current_user_id:
        raise ForbiddenException(detail="You can only delete your own traveler profile")

    # Edge case: cannot delete if traveler has active packages (in_transit)
    for pkg in traveler.accepted_packages:
        if pkg.status == "in_transit":
            raise BadRequestException(
                detail=f"Cannot delete traveler: package #{pkg.id} is still in transit"
            )

    await session.delete(traveler)
    await session.commit()
