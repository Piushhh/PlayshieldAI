"""Dashboard router — user-scoped stats with real trend data."""

from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Asset, Case, CaseStatus, Detection, User, UserRole
from app.schemas import DashboardStats
from app.services.auth_service import get_current_user
from app.services.asset_service import count_assets
from app.services.detection_service import count_detections, count_detections_by_band
from app.services.case_service import count_open_cases

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


async def _get_trend_data(db: AsyncSession, owner_id=None, days: int = 7) -> list[dict]:
    """Generate real trend data from DB for the last N days."""
    trend = []
    for i in range(days - 1, -1, -1):
        day_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
        day_end = day_start + timedelta(days=1)

        det_q = select(func.count(Detection.id)).where(
            Detection.created_at >= day_start, Detection.created_at < day_end
        )
        case_q = select(func.count(Case.id)).where(
            Case.created_at >= day_start, Case.created_at < day_end
        )

        if owner_id:
            det_q = det_q.join(Asset, Detection.asset_id == Asset.id).where(Asset.owner_id == owner_id)
            case_q = case_q.where(Case.owner_id == owner_id)

        det_count = (await db.execute(det_q)).scalar() or 0
        case_count = (await db.execute(case_q)).scalar() or 0

        trend.append({
            "date": day_start.strftime("%b %d"),
            "detections": det_count,
            "cases": case_count,
        })
    return trend


async def _get_recent_cases(db: AsyncSession, owner_id=None, limit: int = 200) -> list[Case]:
    query = (
        select(Case)
        .options(selectinload(Case.detection).selectinload(Detection.discovery))
        .order_by(Case.created_at.desc())
        .limit(limit)
    )
    if owner_id:
        query = query.where(Case.owner_id == owner_id)
    return list((await db.execute(query)).scalars().all())


async def _get_recent_assets(db: AsyncSession, owner_id=None, limit: int = 200) -> list[Asset]:
    query = select(Asset).order_by(Asset.created_at.desc()).limit(limit)
    if owner_id:
        query = query.where(Asset.owner_id == owner_id)
    return list((await db.execute(query)).scalars().all())


def _domain_from_source(url: str | None) -> str:
    if not url:
        return "Unknown source"
    hostname = urlparse(url).hostname
    return hostname or url


def _top_flagged_sources(cases: list[Case]) -> list[dict]:
    buckets: dict[str, dict] = {}
    for case in cases:
        detection = case.detection
        discovery = detection.discovery if detection else None
        domain = _domain_from_source(discovery.source_url if discovery else None)
        bucket = buckets.setdefault(domain, {"count": 0, "max_confidence": 0.0})
        bucket["count"] += 1
        if detection:
            bucket["max_confidence"] = max(bucket["max_confidence"], detection.confidence)

    ranked = sorted(
        buckets.items(),
        key=lambda item: (item[1]["count"], item[1]["max_confidence"]),
        reverse=True,
    )[:4]

    insights = []
    for domain, stats in ranked:
        tone = "risk"
        if stats["max_confidence"] < 0.6:
            tone = "success"
        elif stats["max_confidence"] < 0.85:
            tone = "warning"
        insights.append(
            {
                "title": domain,
                "value": stats["count"],
                "trend": f"Peak confidence {stats['max_confidence']:.0%}",
                "tone": tone,
                "subtitle": "Top flagged source",
            }
        )
    return insights


def _gemini_overview(cases: list[Case], assets: list[Asset]) -> list[dict]:
    if cases:
        ready = sum(1 for case in cases if case.gemini_status == "ready")
        fallback = sum(1 for case in cases if case.gemini_status == "fallback")
        delayed = sum(1 for case in cases if case.gemini_status in {"pending", "error"})
        reviewed = sum(1 for case in cases if case.status == CaseStatus.REVIEW)
    else:
        ready = sum(1 for asset in assets if asset.gemini_status in {"ready", "completed"})
        fallback = sum(1 for asset in assets if asset.gemini_status == "fallback")
        delayed = sum(1 for asset in assets if asset.gemini_status in {"pending", "scanning", "failed"})
        reviewed = 0

    return [
        {
            "title": "Gemini ready",
            "value": ready,
            "trend": "Cases with rationale + draft ready",
            "tone": "success",
            "subtitle": "AI coverage",
        },
        {
            "title": "Fallback drafts",
            "value": fallback,
            "trend": "Classic template used when AI was unavailable",
            "tone": "warning",
            "subtitle": "Continuity",
        },
        {
            "title": "AI delayed",
            "value": delayed,
            "trend": "Soft-delay states that do not block actions",
            "tone": "info",
            "subtitle": "Non-blocking",
        },
        {
            "title": "Reviewed queue",
            "value": reviewed,
            "trend": "Cases already moved into reviewer flow",
            "tone": "neutral",
            "subtitle": "Analyst throughput",
        },
    ]


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get dashboard stats scoped to the current user. Admins see global stats."""
    owner_id = None if user.role == UserRole.ADMIN else user.id

    total_a = await count_assets(db, owner_id=owner_id)
    total_d = await count_detections(db, owner_id=owner_id)
    h, m, lo = await count_detections_by_band(db, owner_id=owner_id)
    open_c = await count_open_cases(db, owner_id=owner_id)
    trend = await _get_trend_data(db, owner_id=owner_id)
    recent_cases = await _get_recent_cases(db, owner_id=owner_id)
    recent_assets = await _get_recent_assets(db, owner_id=owner_id)

    return DashboardStats(
        total_assets=total_a,
        total_scans=total_d,
        open_cases=open_c,
        total_detections=total_d,
        high_confidence_count=h,
        medium_confidence_count=m,
        low_confidence_count=lo,
        trend_data=trend,
        top_flagged_sources=_top_flagged_sources(recent_cases),
        gemini_overview=_gemini_overview(recent_cases, recent_assets),
    )
