"""Notification service layer."""

from typing import Sequence

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Notification, User
from notifications.schemas import NotificationCreate
from errors.exceptions import NotFoundException, ForbiddenException


async def list_notifications_for_user(
    session: AsyncSession,
    user_id: int,
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 20,
) -> Sequence[Notification]:
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read == False)  # noqa: E712
    stmt = stmt.offset(skip).limit(limit).order_by(Notification.id.desc())
    result = await session.exec(stmt)
    return result.all()


async def get_notification(
    session: AsyncSession, notification_id: int
) -> Notification:
    notif = await session.get(Notification, notification_id)
    if not notif:
        raise NotFoundException(detail=f"Notification with id {notification_id} not found")
    return notif


async def create_notification(
    session: AsyncSession, payload: NotificationCreate
) -> Notification:
    # Validate user exists
    user = await session.get(User, payload.user_id)
    if not user:
        raise NotFoundException(detail=f"User with id {payload.user_id} not found")

    notif = Notification(**payload.model_dump())
    session.add(notif)
    await session.commit()
    await session.refresh(notif)
    return notif


async def mark_as_read(
    session: AsyncSession, notification_id: int, current_user_id: int
) -> Notification:
    notif = await get_notification(session, notification_id)
    if notif.user_id != current_user_id:
        raise ForbiddenException(detail="You can only modify your own notifications")
    notif.is_read = True
    await session.commit()
    await session.refresh(notif)
    return notif


async def mark_all_read(session: AsyncSession, user_id: int) -> int:
    stmt = select(Notification).where(
        Notification.user_id == user_id, Notification.is_read == False  # noqa: E712
    )
    result = await session.exec(stmt)
    notifications = result.all()
    count = 0
    for notif in notifications:
        notif.is_read = True
        count += 1
    if count:
        await session.commit()
    return count


async def delete_notification(
    session: AsyncSession, notification_id: int, current_user_id: int
) -> None:
    notif = await get_notification(session, notification_id)
    if notif.user_id != current_user_id:
        raise ForbiddenException(detail="You can only delete your own notifications")
    await session.delete(notif)
    await session.commit()
