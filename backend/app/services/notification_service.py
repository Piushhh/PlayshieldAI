"""Notification service — in-app notifications for users."""

import uuid
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification


async def create_notification(
    db: AsyncSession,
    user_id: uuid.UUID,
    title: str,
    message: str,
    case_id: uuid.UUID | None = None,
) -> Notification:
    """Create an in-app notification for a user."""
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        case_id=case_id,
    )
    db.add(notif)
    await db.flush()
    return notif


async def list_notifications(
    db: AsyncSession,
    user_id: uuid.UUID,
    unread_only: bool = False,
    limit: int = 50,
) -> list[Notification]:
    """List notifications for a user."""
    q = select(Notification).where(
        Notification.user_id == user_id
    ).order_by(Notification.created_at.desc()).limit(limit)
    if unread_only:
        q = q.where(Notification.is_read == False)
    result = await db.execute(q)
    return list(result.scalars().all())


async def mark_notification_read(
    db: AsyncSession,
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """Mark a single notification as read."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        return False
    notif.is_read = True
    await db.flush()
    return True


async def mark_all_read(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Mark all notifications as read for a user. Returns count updated."""
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read == False)
        .values(is_read=True)
    )
    await db.flush()
    return result.rowcount


async def count_unread(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Count unread notifications for a user."""
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read == False,
        )
    )
    return result.scalar() or 0
