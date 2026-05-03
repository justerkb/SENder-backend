from typing import Annotated, Sequence, Optional

from fastapi import APIRouter, Depends, Query, Path, status
from sqlmodel.ext.asyncio.session import AsyncSession

from db import get_session
from models import Trip
from trips.schemas import TripCreate, TripUpdate, TripRead
from trips import service as trips_service
from auth.deps import get_current_user


router = APIRouter(prefix="/trips", tags=["trips"])


@router.get(
    "",
    response_model=list[TripRead],
    status_code=status.HTTP_200_OK,
    summary="Get all trips (public, with filters)",
)
async def get_trips(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    from_city: Annotated[Optional[str], Query(description="Filter by departure city")] = None,
    to_city: Annotated[Optional[str], Query(description="Filter by destination city")] = None,
    status_filter: Annotated[Optional[str], Query(alias="status")] = None,
    traveler_id: Annotated[Optional[int], Query(gt=0)] = None,
    min_weight: Annotated[Optional[float], Query(gt=0, description="Min available weight kg")] = None,
    sort_by: Annotated[str, Query()] = "id",
    order: Annotated[str, Query()] = "desc",
    session: AsyncSession = Depends(get_session),
) -> Sequence[Trip]:
    return await trips_service.list_trips(
        session=session,
        skip=skip,
        limit=limit,
        from_city=from_city,
        to_city=to_city,
        status_filter=status_filter,
        traveler_id=traveler_id,
        min_weight=min_weight,
        sort_by=sort_by,
        order=order,
    )


@router.get(
    "/{trip_id}",
    response_model=TripRead,
    status_code=status.HTTP_200_OK,
    summary="Get trip by ID (public)",
)
async def get_trip(
    trip_id: Annotated[int, Path(gt=0)],
    session: AsyncSession = Depends(get_session),
) -> Trip:
    return await trips_service.get_trip(session, trip_id)


@router.post(
    "",
    response_model=TripRead,
    status_code=status.HTTP_201_CREATED,
    summary="Post new trip route (auth, traveler only)",
)
async def create_trip(
    trip: TripCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> Trip:
    user_id = int(current_user["sub"])
    return await trips_service.create_trip(session, trip, current_user_id=user_id)


@router.put(
    "/{trip_id}",
    response_model=TripRead,
    status_code=status.HTTP_200_OK,
    summary="Full update trip (auth, owner only)",
)
async def update_trip(
    trip_update: TripCreate,
    trip_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> Trip:
    user_id = int(current_user["sub"])
    return await trips_service.update_trip_full(
        session, trip_id, trip_update, current_user_id=user_id
    )


@router.patch(
    "/{trip_id}",
    response_model=TripRead,
    status_code=status.HTTP_200_OK,
    summary="Partial update trip (auth, owner only)",
)
async def partial_update_trip(
    trip_update: TripUpdate,
    trip_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> Trip:
    user_id = int(current_user["sub"])
    return await trips_service.update_trip_partial(
        session, trip_id, trip_update, current_user_id=user_id
    )


@router.delete(
    "/{trip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete trip (auth, owner or admin)",
)
async def delete_trip(
    trip_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> None:
    user_id = int(current_user["sub"])
    is_admin = current_user.get("role") == "admin"
    await trips_service.delete_trip(
        session, trip_id, current_user_id=user_id, is_admin=is_admin
    )
