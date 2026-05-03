from typing import Annotated, Sequence

from fastapi import APIRouter, Depends, Path, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from db import get_session
from models import Review
from reviews.schemas import ReviewCreate, ReviewUpdate, ReviewPartialUpdate, ReviewRead
from reviews import service as reviews_service
from auth.deps import get_current_user


router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get(
    "",
    response_model=list[ReviewRead],
    status_code=status.HTTP_200_OK,
    summary="List all reviews (public)",
)
async def list_reviews(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="id"),
    order: str = Query(default="desc"),
    session: AsyncSession = Depends(get_session),
) -> Sequence[Review]:
    return await reviews_service.list_reviews(
        session, skip=skip, limit=limit, sort_by=sort_by, order=order
    )


@router.get(
    "/traveler/{traveler_id}",
    response_model=list[ReviewRead],
    status_code=status.HTTP_200_OK,
    summary="List reviews for a traveler (public)",
)
async def list_reviews_for_traveler(
    traveler_id: Annotated[int, Path(gt=0)],
    session: AsyncSession = Depends(get_session),
) -> Sequence[Review]:
    return await reviews_service.list_reviews_for_traveler(session, traveler_id)


@router.get(
    "/{review_id}",
    response_model=ReviewRead,
    status_code=status.HTTP_200_OK,
    summary="Get review by ID (public)",
)
async def get_review(
    review_id: Annotated[int, Path(gt=0)],
    session: AsyncSession = Depends(get_session),
) -> Review:
    return await reviews_service.get_review(session, review_id)


@router.post(
    "",
    response_model=ReviewRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create review for traveler on a delivered package (auth, sender only)",
)
async def create_review(
    review: ReviewCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> Review:
    user_id = int(current_user["sub"])
    return await reviews_service.create_review(session, review, current_user_id=user_id)


@router.put(
    "/{review_id}",
    response_model=ReviewRead,
    status_code=status.HTTP_200_OK,
    summary="Update existing review (auth, owner only)",
)
async def update_review(
    review_id: Annotated[int, Path(gt=0)],
    review: ReviewUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> Review:
    user_id = int(current_user["sub"])
    return await reviews_service.update_review(session, review_id, review, current_user_id=user_id)


@router.patch(
    "/{review_id}",
    response_model=ReviewRead,
    status_code=status.HTTP_200_OK,
    summary="Partially update review (auth, owner only)",
)
async def update_review_partial(
    review_id: Annotated[int, Path(gt=0)],
    review: ReviewPartialUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> Review:
    user_id = int(current_user["sub"])
    return await reviews_service.update_review_partial(session, review_id, review, current_user_id=user_id)


@router.delete(
    "/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete review (auth, owner or admin)",
)
async def delete_review(
    review_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> None:
    user_id = int(current_user["sub"])
    is_admin = current_user.get("role") == "admin"
    await reviews_service.delete_review(session, review_id, current_user_id=user_id, is_admin=is_admin)
