"""Scan & crawl router — trigger crawling and scanning operations."""

import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Asset, User, UserRole
from app.schemas import CrawlRequest, ScanRequest, DetectionOut
from app.services.auth_service import get_current_user, require_role
from app.services.detection_service import list_detections

router = APIRouter(tags=["scan"])


@router.post("/crawl/run")
async def run_crawl(
    req: CrawlRequest | None = None,
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Trigger a background crawl job (admin only)."""
    from app.worker import crawl_and_scan_task
    sources = None
    if req and req.sources:
        sources = [{"url": s, "name": s, "selector": "img[src]"} for s in req.sources]
    task = crawl_and_scan_task.delay(sources)
    return {"task_id": task.id, "status": "queued"}


@router.post("/scan/run")
async def run_scan(
    req: ScanRequest | None = None,
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Trigger a background scan job (admin only)."""
    from app.worker import scan_discoveries_task
    ids = [str(d) for d in req.discovery_ids] if req and req.discovery_ids else None
    task = scan_discoveries_task.delay(ids)
    return {"task_id": task.id, "status": "queued"}


@router.get("/detections", response_model=list[DetectionOut])
async def get_detections(
    min_confidence: float | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List detections scoped to current user's assets. Admins see all."""
    owner_id = None if user.role == UserRole.ADMIN else user.id
    return await list_detections(db, min_confidence=min_confidence, owner_id=owner_id)
