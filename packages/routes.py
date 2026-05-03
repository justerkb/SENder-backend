from typing import Annotated, Sequence, Optional

from fastapi import APIRouter, Depends, Query, Path, status
from sqlmodel.ext.asyncio.session import AsyncSession

from db import get_session
from models import Package
from packages.schemas import PackageCreate, PackageUpdate, PackageRead, PackageStatusUpdate, PackageAccept
from packages import service as packages_service
from auth.deps import get_current_user


router = APIRouter(prefix="/packages", tags=["packages"])


@router.get(
    "",
    response_model=list[PackageRead],
    status_code=status.HTTP_200_OK,
    summary="Get all packages (public, with filters)",
)
async def get_packages(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    status_filter: Annotated[Optional[str], Query(alias="status")] = None,
    pickup_city: Annotated[Optional[str], Query()] = None,
    delivery_city: Annotated[Optional[str], Query()] = None,
    sender_id: Annotated[Optional[int], Query(gt=0)] = None,
    traveler_id: Annotated[Optional[int], Query(gt=0)] = None,
    max_weight: Annotated[Optional[float], Query(gt=0)] = None,
    sort_by: Annotated[str, Query()] = "id",
    order: Annotated[str, Query()] = "desc",
    session: AsyncSession = Depends(get_session),
) -> Sequence[Package]:
    return await packages_service.list_packages(
        session=session,
        skip=skip,
        limit=limit,
        status_filter=status_filter,
        pickup_city=pickup_city,
        delivery_city=delivery_city,
        sender_id=sender_id,
        traveler_id=traveler_id,
        max_weight=max_weight,
        sort_by=sort_by,
        order=order,
    )


@router.get(
    "/{package_id}",
    response_model=PackageRead,
    status_code=status.HTTP_200_OK,
    summary="Get package by ID (public)",
)
async def get_package(
    package_id: Annotated[int, Path(gt=0)],
    session: AsyncSession = Depends(get_session),
) -> Package:
    return await packages_service.get_package(session, package_id)


@router.post(
    "",
    response_model=PackageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Post new package for delivery (auth, sender only)",
)
async def create_package(
    package: PackageCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> Package:
    user_id = int(current_user["sub"])
    return await packages_service.create_package(session, package, current_user_id=user_id)


@router.post(
    "/{package_id}/accept",
    response_model=PackageRead,
    status_code=status.HTTP_200_OK,
    summary="Traveler accepts a package (auth, traveler only)",
)
async def accept_package(
    package_id: Annotated[int, Path(gt=0)],
    payload: PackageAccept,
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> Package:
    user_id = int(current_user["sub"])
    return await packages_service.accept_package(
        session, package_id, payload.traveler_id, current_user_id=user_id
    )


@router.patch(
    "/{package_id}/status",
    response_model=PackageRead,
    status_code=status.HTTP_200_OK,
    summary="Update package status (auth)",
)
async def update_status(
    package_id: Annotated[int, Path(gt=0)],
    payload: PackageStatusUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> Package:
    user_id = int(current_user["sub"])
    return await packages_service.update_package_status(
        session, package_id, payload.status, current_user_id=user_id
    )


@router.put(
    "/{package_id}",
    response_model=PackageRead,
    status_code=status.HTTP_200_OK,
    summary="Full update package (auth, sender owner only)",
)
async def update_package(
    package_update: PackageCreate,
    package_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> Package:
    user_id = int(current_user["sub"])
    return await packages_service.update_package_full(
        session, package_id, package_update, current_user_id=user_id
    )


@router.patch(
    "/{package_id}",
    response_model=PackageRead,
    status_code=status.HTTP_200_OK,
    summary="Partial update package (auth, sender owner only)",
)
async def partial_update_package(
    package_update: PackageUpdate,
    package_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> Package:
    user_id = int(current_user["sub"])
    return await packages_service.update_package_partial(
        session, package_id, package_update, current_user_id=user_id
    )


@router.delete(
    "/{package_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete package (auth, sender owner or admin)",
)
async def delete_package(
    package_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> None:
    user_id = int(current_user["sub"])
    is_admin = current_user.get("role") == "admin"
    await packages_service.delete_package(
        session, package_id, current_user_id=user_id, is_admin=is_admin
    )
