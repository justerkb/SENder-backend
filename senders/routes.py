from typing import Annotated, Sequence

from fastapi import APIRouter, Depends, Query, Path, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from db import get_session
from models import Sender
from senders.schemas import SenderCreate, SenderUpdate, SenderRead
from senders import service as senders_service
from auth.deps import get_current_user
from errors.exceptions import NotFoundException


router = APIRouter(prefix="/senders", tags=["senders"])


@router.get(
    "/me",
    response_model=SenderRead,
    status_code=status.HTTP_200_OK,
    summary="Get my sender profile (auth)",
)
async def get_my_sender(
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> Sender:
    user_id = int(current_user["sub"])
    result = await session.exec(select(Sender).where(Sender.user_id == user_id))
    sender = result.first()
    if not sender:
        raise NotFoundException("You don't have a sender profile yet")
    return sender


@router.get(
    "",
    response_model=list[SenderRead],
    status_code=status.HTTP_200_OK,
    summary="Get all senders (public)",
)
async def get_senders(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    search: Annotated[str | None, Query(description="Search by name or city")] = None,
    sort_by: Annotated[str, Query(description="Sort by field")] = "id",
    order: Annotated[str, Query(description="asc or desc")] = "desc",
    session: AsyncSession = Depends(get_session),
) -> Sequence[Sender]:
    return await senders_service.list_senders(
        session=session, skip=skip, limit=limit, search=search,
        sort_by=sort_by, order=order,
    )


@router.get(
    "/{sender_id}",
    response_model=SenderRead,
    status_code=status.HTTP_200_OK,
    summary="Get sender by ID (public)",
)
async def get_sender(
    sender_id: Annotated[int, Path(gt=0)],
    session: AsyncSession = Depends(get_session),
) -> Sender:
    return await senders_service.get_sender(session, sender_id)


@router.post(
    "",
    response_model=SenderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register new sender profile (auth)",
)
async def create_sender(
    sender: SenderCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> Sender:
    user_id = int(current_user["sub"])
    return await senders_service.create_sender(session, sender, user_id=user_id)


@router.put(
    "/{sender_id}",
    response_model=SenderRead,
    status_code=status.HTTP_200_OK,
    summary="Full update sender (auth, owner only)",
)
async def update_sender(
    sender_update: SenderCreate,
    sender_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> Sender:
    user_id = int(current_user["sub"])
    return await senders_service.update_sender_full(
        session, sender_id, sender_update, current_user_id=user_id
    )


@router.patch(
    "/{sender_id}",
    response_model=SenderRead,
    status_code=status.HTTP_200_OK,
    summary="Partial update sender (auth, owner only)",
)
async def partial_update_sender(
    sender_update: SenderUpdate,
    sender_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> Sender:
    user_id = int(current_user["sub"])
    return await senders_service.update_sender_partial(
        session, sender_id, sender_update, current_user_id=user_id
    )


@router.delete(
    "/{sender_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete sender (auth, owner or admin)",
)
async def delete_sender(
    sender_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
) -> None:
    user_id = int(current_user["sub"])
    is_admin = current_user.get("role") == "admin"
    await senders_service.delete_sender(
        session, sender_id, current_user_id=user_id, is_admin=is_admin
    )
