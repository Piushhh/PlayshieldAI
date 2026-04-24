"""Notifications router — list, read, mark-all-read."""

import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas import NotificationOut
from app.services.auth_service import get_current_user
from app.services.notification_service import (
    count_unread, list_notifications, mark_all_read, mark_notification_read,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
async def get_notifications(
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await list_notifications(db, user.id, unread_only=unread_only)


@router.get("/count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    count = await count_unread(db, user.id)
    return {"unread_count": count}


@router.post("/{notification_id}/read")
async def read_notification(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    success = await mark_notification_read(db, notification_id, user.id)
    if not success:
        return {"message": "Notification not found"}
    return {"message": "Marked as read"}


@router.post("/read-all")
async def read_all_notifications(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    count = await mark_all_read(db, user.id)
    return {"message": f"Marked {count} notifications as read"}
