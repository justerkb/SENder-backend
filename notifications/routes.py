"""Notification routes – all require authentication."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from db import get_session
from auth.deps import get_current_user, require_role
from notifications.schemas import NotificationRead, NotificationCreate
from notifications import service as notif_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get(
    "",
    response_model=list[NotificationRead],
    status_code=status.HTTP_200_OK,
    summary="List my notifications (auth)",
)
async def list_my_notifications(
    current_user: Annotated[dict, Depends(get_current_user)],
    unread_only: bool = False,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    user_id = int(current_user["sub"])
    return await notif_service.list_notifications_for_user(
        session, user_id, unread_only=unread_only, skip=skip, limit=limit
    )


@router.post(
    "",
    response_model=NotificationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a notification (admin only)",
)
async def create_notification(
    payload: NotificationCreate,
    current_user: Annotated[dict, Depends(require_role("admin"))],
    session: AsyncSession = Depends(get_session),
):
    return await notif_service.create_notification(session, payload)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationRead,
    status_code=status.HTTP_200_OK,
    summary="Mark notification as read (auth)",
)
async def mark_read(
    notification_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
):
    user_id = int(current_user["sub"])
    return await notif_service.mark_as_read(session, notification_id, user_id)


@router.post(
    "/read-all",
    status_code=status.HTTP_200_OK,
    summary="Mark all notifications as read (auth)",
)
async def mark_all_read(
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
):
    user_id = int(current_user["sub"])
    count = await notif_service.mark_all_read(session, user_id)
    return {"detail": f"Marked {count} notifications as read"}


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a notification (auth)",
)
async def delete_notification(
    notification_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[dict, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
):
    user_id = int(current_user["sub"])
    await notif_service.delete_notification(session, notification_id, user_id)
