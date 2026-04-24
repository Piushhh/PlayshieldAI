"""Audit logging service — immutable action logs."""

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import AuditLog


async def log_action(
    db: AsyncSession,
    actor_user_id: uuid.UUID | None,
    entity_type: str,
    entity_id: uuid.UUID,
    action: str,
    before_json: dict | None = None,
    after_json: dict | None = None,
):
    entry = AuditLog(
        actor_user_id=actor_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        before_json=before_json,
        after_json=after_json,
    )
    db.add(entry)
    await db.flush()
    return entry


async def get_audit_logs(
    db: AsyncSession,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None = None,
    limit: int = 100,
) -> list[AuditLog]:
    q = (
        select(AuditLog)
        .options(selectinload(AuditLog.actor))
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.where(AuditLog.entity_id == entity_id)
    if actor_id:
        q = q.where(AuditLog.actor_user_id == actor_id)
    return list((await db.execute(q)).scalars().all())
