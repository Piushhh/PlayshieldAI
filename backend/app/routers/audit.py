"""Audit logs router — admin sees all, users see their own activity."""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, UserRole
from app.schemas import AuditLogOut
from app.services.auth_service import get_current_user
from app.services.audit_service import get_audit_logs
from app.services.case_service import get_case

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
async def list_audit_logs(
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List audit logs. Admins see all, users see only their own actions."""
    actor_id = None if user.role == UserRole.ADMIN else user.id
    if user.role != UserRole.ADMIN and entity_type == "case" and entity_id:
        case = await get_case(db, entity_id)
        if not case or case.owner_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        actor_id = None
    return await get_audit_logs(
        db, entity_type=entity_type, entity_id=entity_id, actor_id=actor_id
    )
