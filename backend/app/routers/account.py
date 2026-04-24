"""Account router — user settings, preferences, and account deletion."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas import UserOut, UserSettingsUpdate
from app.services.auth_service import delete_user_account, get_current_user
from app.services.audit_service import log_action

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/settings", response_model=UserOut)
async def get_settings(user: User = Depends(get_current_user)):
    """Get current user settings."""
    return user


@router.patch("/settings", response_model=UserOut)
async def update_settings(
    req: UserSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update user preferences (e.g. email notification opt-in/out)."""
    if req.email_notifications is not None:
        user.email_notifications = req.email_notifications
    await db.flush()
    await log_action(db, user.id, "user", user.id, "settings_updated",
                     after_json={"email_notifications": user.email_notifications})
    return user


@router.delete("/delete")
async def delete_account(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """GDPR-style self-deletion: removes user and all associated data."""
    user_id = user.id
    await log_action(db, user_id, "user", user_id, "account_deleted")
    success = await delete_user_account(user_id, db)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete account")
    return {"message": "Account and all associated data deleted successfully."}
