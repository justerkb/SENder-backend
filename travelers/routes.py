from typing import Annotated, Sequence, Optional

from fastapi import APIRouter, Depends, Query, Path, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from db import get_session
from models import Traveler
from travelers.schemas import TravelerCreate, TravelerUpdate, TravelerRead
from travelers import service as travelers_service
from auth.deps import get_current_user, require_role
from errors.exceptions import NotFoundException


router = APIRouter(prefix="/travelers", tags=["travelers"])


@router.get(
    "/me",
    response_model=TravelerRead,
    status_code=status.HTTP_200_OK,
    summary="Get my traveler profile (auth)",
)
async def get_my_traveler(
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> Traveler:
    user_id = int(current_user["sub"])
    result = await session.exec(select(Traveler).where(Traveler.user_id == user_id))
    traveler = result.first()
    if not traveler:
        raise NotFoundException("You don't have a traveler profile yet")
    return traveler


@router.get(
    "",
    response_model=list[TravelerRead],
    status_code=status.HTTP_200_OK,
    summary="Get all travelers (public)",
)
async def get_travelers(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    search: Annotated[str | None, Query(description="Search by name or bio")] = None,
    sort_by: Annotated[str, Query(description="Sort by field: name, id, created_at")] = "id",
    order: Annotated[str, Query(description="asc or desc")] = "desc",
    session: AsyncSession = Depends(get_session),
) -> Sequence[Traveler]:
    return await travelers_service.list_travelers(
        session=session, skip=skip, limit=limit, search=search,
        sort_by=sort_by, order=order,
    )


@router.get(
    "/{traveler_id}",
    response_model=TravelerRead,
    status_code=status.HTTP_200_OK,
    summary="Get traveler by ID (public)",
)
async def get_traveler(
    traveler_id: Annotated[int, Path(gt=0)],
    session: AsyncSession = Depends(get_session),
) -> Traveler:
    return await travelers_service.get_traveler(session, traveler_id)


@router.post(
    "",
    response_model=TravelerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register new traveler profile (auth)",
)
async def create_traveler(
    traveler: TravelerCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> Traveler:
    user_id = int(current_user["sub"])
    return await travelers_service.create_traveler(session, traveler, user_id=user_id)


@router.put(
    "/{traveler_id}",
    response_model=TravelerRead,
    status_code=status.HTTP_200_OK,
    summary="Full update traveler (auth, owner only)",
)
async def update_traveler(
    traveler_update: TravelerCreate,
    traveler_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> Traveler:
    user_id = int(current_user["sub"])
    return await travelers_service.update_traveler_full(
        session, traveler_id, traveler_update, current_user_id=user_id
    )


@router.patch(
    "/{traveler_id}",
    response_model=TravelerRead,
    status_code=status.HTTP_200_OK,
    summary="Partial update traveler (auth, owner only)",
)
async def partial_update_traveler(
    traveler_update: TravelerUpdate,
    traveler_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> Traveler:
    user_id = int(current_user["sub"])
    return await travelers_service.update_traveler_partial(
        session, traveler_id, traveler_update, current_user_id=user_id
    )


@router.delete(
    "/{traveler_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete traveler (auth, owner or admin)",
)
async def delete_traveler(
    traveler_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> None:
    user_id = int(current_user["sub"])
    is_admin = current_user.get("role") == "admin"
    await travelers_service.delete_traveler(
        session, traveler_id, current_user_id=user_id, is_admin=is_admin
    )
