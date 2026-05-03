"""Review service with edge-case validation and custom exceptions."""

from datetime import datetime
from typing import Optional, Sequence

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Review, Sender, Traveler, Package
from reviews.schemas import ReviewCreate, ReviewUpdate, ReviewPartialUpdate
from errors.exceptions import (
    NotFoundException,
    BadRequestException,
    ConflictException,
    ForbiddenException,
)


async def list_reviews(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    sort_by: str = "id",
    order: str = "desc",
) -> Sequence[Review]:
    stmt = select(Review)
    sort_column = getattr(Review, sort_by, Review.id)
    if order == "asc":
        stmt = stmt.order_by(sort_column.asc())
    else:
        stmt = stmt.order_by(sort_column.desc())
    stmt = stmt.offset(skip).limit(limit)
    result = await session.exec(stmt)
    return result.all()


async def list_reviews_for_traveler(
    session: AsyncSession, traveler_id: int
) -> Sequence[Review]:
    # Validate traveler exists
    traveler = await session.get(Traveler, traveler_id)
    if not traveler:
        raise NotFoundException(detail=f"Traveler with id {traveler_id} not found")

    stmt = select(Review).where(Review.traveler_id == traveler_id).order_by(Review.id.desc())
    result = await session.exec(stmt)
    return result.all()


async def get_review(session: AsyncSession, review_id: int) -> Review:
    review = await session.get(Review, review_id)
    if not review:
        raise NotFoundException(detail=f"Review with id {review_id} not found")
    return review


async def _validate_fk_ids(
    session: AsyncSession, sender_id: int, traveler_id: int, package_id: int
) -> Package:
    if not await session.get(Sender, sender_id):
        raise NotFoundException(detail=f"Sender with id {sender_id} not found")
    if not await session.get(Traveler, traveler_id):
        raise NotFoundException(detail=f"Traveler with id {traveler_id} not found")
    package = await session.get(Package, package_id)
    if not package:
        raise NotFoundException(detail=f"Package with id {package_id} not found")
    return package


async def create_review(
    session: AsyncSession, payload: ReviewCreate, current_user_id: int | None = None
) -> Review:
    package = await _validate_fk_ids(
        session,
        sender_id=payload.sender_id,
        traveler_id=payload.traveler_id,
        package_id=payload.package_id,
    )

    # Edge case: can only review delivered packages
    if package.status != "delivered":
        raise BadRequestException(
            detail=f"Cannot review a package with status '{package.status}'. Package must be 'delivered'."
        )

    # Edge case: sender must match the package sender
    if package.sender_id != payload.sender_id:
        raise BadRequestException(
            detail="Sender does not match the package's sender. You can only review packages you sent."
        )

    # Edge case: traveler must be the one who delivered
    if package.accepted_traveler_id != payload.traveler_id:
        raise BadRequestException(
            detail="Traveler does not match the package's delivering traveler."
        )

    # Edge case: one review per package per sender
    stmt = select(Review).where(
        Review.package_id == payload.package_id,
        Review.sender_id == payload.sender_id,
    )
    result = await session.exec(stmt)
    if result.first():
        raise ConflictException(detail="You have already reviewed this package delivery")

    # Ownership check: sender profile must belong to current user
    if current_user_id:
        sender = await session.get(Sender, payload.sender_id)
        if sender and sender.user_id and sender.user_id != current_user_id:
            raise ForbiddenException(detail="You can only create reviews with your own sender profile")

    review = Review(**payload.model_dump())
    session.add(review)
    await session.commit()
    await session.refresh(review)
    return review


async def update_review(
    session: AsyncSession, review_id: int, payload: ReviewUpdate, current_user_id: int | None = None
) -> Review:
    review = await get_review(session, review_id)

    # Ownership check
    if current_user_id:
        sender = await session.get(Sender, review.sender_id)
        if sender and sender.user_id and sender.user_id != current_user_id:
            raise ForbiddenException(detail="You can only update your own reviews")

    for field, value in payload.model_dump().items():
        setattr(review, field, value)
    review.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(review)
    return review


async def update_review_partial(
    session: AsyncSession, review_id: int, payload: ReviewPartialUpdate, current_user_id: int | None = None
) -> Review:
    review = await get_review(session, review_id)

    if current_user_id:
        sender = await session.get(Sender, review.sender_id)
        if sender and sender.user_id and sender.user_id != current_user_id:
            raise ForbiddenException(detail="You can only update your own reviews")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise BadRequestException(detail="At least one field must be provided")

    for field, value in data.items():
        setattr(review, field, value)
    review.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(review)
    return review


async def delete_review(
    session: AsyncSession, review_id: int, current_user_id: int | None = None, is_admin: bool = False
) -> None:
    review = await get_review(session, review_id)

    if not is_admin and current_user_id:
        sender = await session.get(Sender, review.sender_id)
        if sender and sender.user_id and sender.user_id != current_user_id:
            raise ForbiddenException(detail="You can only delete your own reviews")

    await session.delete(review)
    await session.commit()
