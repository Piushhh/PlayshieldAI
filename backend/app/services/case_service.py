"""Case service — case lifecycle management (user-scoped)."""

import difflib
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import async_session_factory
from app.models import Case, CaseStatus, Detection, GeminiCall, TakedownDraft
from app.services.audit_service import log_action
from app.services.gemini_service import generate_case_content

settings = get_settings()


async def generate_case_gemini_content_background(
    case_id: uuid.UUID,
    actor_user_id: uuid.UUID | None = None,
) -> None:
    """Background-safe wrapper that creates its own DB session."""
    async with async_session_factory() as db:
        case = await get_case(db, case_id)
        if not case:
            return
        await generate_case_gemini_content(db, case, actor_user_id=actor_user_id, force=True)
        await db.commit()



async def get_case(db: AsyncSession, case_id: uuid.UUID) -> Case | None:
    result = await db.execute(
        select(Case).where(Case.id == case_id).options(
            selectinload(Case.detection).selectinload(Detection.discovery),
            selectinload(Case.detection).selectinload(Detection.asset),
            selectinload(Case.takedown_drafts),
            selectinload(Case.gemini_calls).selectinload(GeminiCall.actor),
        )
    )
    return result.scalar_one_or_none()


async def list_cases(
    db: AsyncSession,
    status: str | None = None,
    min_confidence: float | None = None,
    owner_id: uuid.UUID | None = None,
) -> list[Case]:
    """List cases, optionally scoped to the asset owner."""
    q = select(Case).options(
        selectinload(Case.detection).selectinload(Detection.discovery),
        selectinload(Case.detection).selectinload(Detection.asset),
        selectinload(Case.takedown_drafts),
        selectinload(Case.gemini_calls).selectinload(GeminiCall.actor),
    ).order_by(Case.created_at.desc())
    if status:
        q = q.where(Case.status == CaseStatus(status))
    if owner_id:
        q = q.where(Case.owner_id == owner_id)
    result = await db.execute(q)
    cases = list(result.scalars().all())
    if min_confidence is not None:
        cases = [c for c in cases if c.detection and c.detection.confidence >= min_confidence]
    return cases


async def update_case_status(
    db: AsyncSession, case_id: uuid.UUID, new_status: str
) -> Case | None:
    case = await get_case(db, case_id)
    if not case:
        return None
    case.status = CaseStatus(new_status)
    await db.flush()
    return case


async def create_case_from_detection(
    db: AsyncSession,
    detection_id: uuid.UUID,
    owner_id: uuid.UUID | None = None,
    priority: str = "medium",
    assigned_to: uuid.UUID | None = None,
) -> Case:
    case = Case(
        detection_id=detection_id,
        owner_id=owner_id,
        status=CaseStatus.NEW,
        priority=priority,
        assigned_to=assigned_to,
    )
    db.add(case)
    await db.flush()
    return case


async def save_draft(
    db: AsyncSession, case_id: uuid.UUID, draft_text: str, model: str = "deterministic"
) -> TakedownDraft:
    draft = TakedownDraft(case_id=case_id, draft_text=draft_text, model=model, draft_kind="legacy")
    db.add(draft)
    await db.flush()
    return draft


def build_case_context(case: Case) -> dict[str, Any]:
    detection = case.detection
    asset = detection.asset if detection else None
    discovery = detection.discovery if detection else None

    return {
        "case": {
            "id": str(case.id),
            "status": case.status.value if case.status else "new",
            "priority": case.priority.value if case.priority else "medium",
            "created_at": case.created_at.isoformat() if case.created_at else None,
            "previous_rationale": case.gemini_rationale,
        },
        "current_draft": {
            "id": str(case.current_draft.id) if case.current_draft else None,
            "text": case.current_draft.draft_text if case.current_draft else None,
            "kind": case.current_draft.draft_kind if case.current_draft else None,
        },
        "detection": {
            "confidence": detection.confidence if detection else 0,
            "hash_score": detection.hash_score if detection else 0,
            "embed_score": detection.embed_score if detection else 0,
            "risk_score": detection.risk_score if detection else 0,
        },
        "asset": {
            "id": str(asset.id) if asset else None,
            "title": asset.title if asset else "Unknown",
            "license_type": asset.license_type if asset else "Unknown",
            "allowed_use_notes": asset.allowed_use_notes if asset else None,
            "allowed_sources_json": asset.allowed_sources_json if asset else [],
        },
        "discovery": {
            "id": str(discovery.id) if discovery else None,
            "source_url": discovery.source_url if discovery else "Unknown",
            "media_url": discovery.media_url if discovery else None,
            "platform": discovery.platform if discovery else "Unknown",
            "captured_at": discovery.captured_at.isoformat() if discovery and discovery.captured_at else None,
            "meta_json": discovery.meta_json if discovery else {},
        },
        "evidence": detection.evidence_json if detection and detection.evidence_json else {},
    }



def serialize_gemini_summary(case: Case) -> dict[str, Any]:
    draft_history = sorted(
        case.takedown_drafts,
        key=lambda draft: draft.created_at.timestamp() if draft.created_at else 0,
        reverse=True,
    )
    recent_calls = sorted(
        case.gemini_calls,
        key=lambda call: call.created_at.timestamp() if call.created_at else 0,
        reverse=True,
    )[:5]
    return {
        "case_id": case.id,
        "status": case.gemini_status,
        "rationale": case.gemini_rationale,
        "model": case.gemini_model,
        "provider": case.gemini_provider,
        "error_message": case.gemini_error,
        "incomplete_reason": case.gemini_incomplete_reason,
        "is_incomplete": case.gemini_is_incomplete,
        "is_fallback": case.gemini_is_fallback,
        "generated_at": case.gemini_generated_at,
        "last_attempted_at": case.gemini_last_attempted_at,
        "current_draft": draft_history[0] if draft_history else None,
        "draft_history": draft_history,
        "recent_calls": recent_calls,
    }


async def save_draft_revision(
    db: AsyncSession,
    case_id: uuid.UUID,
    draft_text: str,
    model: str,
    draft_kind: str,
    actor_user_id: uuid.UUID | None = None,
    parent_draft_id: uuid.UUID | None = None,
) -> TakedownDraft:
    draft = TakedownDraft(
        case_id=case_id,
        draft_text=draft_text,
        model=model,
        draft_kind=draft_kind,
        parent_draft_id=parent_draft_id,
        edited_by_user_id=actor_user_id if draft_kind == "user_edit" else None,
    )
    db.add(draft)
    await db.flush()
    return draft


def _build_delta(before_text: str, after_text: str) -> str:
    diff = difflib.unified_diff(
        before_text.splitlines(),
        after_text.splitlines(),
        fromfile="previous",
        tofile="updated",
        lineterm="",
    )
    return "\n".join(list(diff)[:40])


async def generate_case_gemini_content(
    db: AsyncSession,
    case: Case,
    actor_user_id: uuid.UUID | None = None,
    force: bool = False,
) -> Case:
    if not force and case.gemini_generated_at and case.current_draft:
        return case

    prior_draft = case.current_draft
    before_summary = {
        "status": case.gemini_status,
        "draft_id": str(prior_draft.id) if prior_draft else None,
        "is_fallback": case.gemini_is_fallback,
    }
    request_json = build_case_context(case)

    case.gemini_status = "pending"
    case.gemini_error = None
    case.gemini_incomplete_reason = "Generation in progress."
    case.gemini_is_incomplete = True
    case.gemini_last_attempted_at = datetime.now(timezone.utc)

    call = GeminiCall(
        case_id=case.id,
        actor_user_id=actor_user_id,
        operation="generate_case_content",
        provider="vertex_ai",
        model=settings.GEMINI_MODEL,
        status="pending",
        is_incomplete=True,
        request_json=request_json,
    )
    db.add(call)
    await db.flush()

    result = await generate_case_content(request_json)
    generated_at = datetime.now(timezone.utc)

    case.gemini_status = result.status
    case.gemini_rationale = result.rationale
    case.gemini_model = result.model
    case.gemini_provider = result.provider
    case.gemini_error = result.error_message
    case.gemini_incomplete_reason = result.incomplete_reason
    case.gemini_is_incomplete = result.is_incomplete
    case.gemini_is_fallback = result.is_fallback
    case.gemini_generated_at = generated_at

    # Auto-escalation logic: Update case priority based on Gemini risk level
    if result.risk_level.lower() == "critical":
        case.priority = "critical"
    elif result.risk_level.lower() == "high":
        case.priority = "high"

    new_draft = await save_draft_revision(
        db,
        case_id=case.id,
        draft_text=result.draft_text,
        model=result.model,
        draft_kind="fallback" if result.is_fallback else "gemini",
        actor_user_id=actor_user_id,
        parent_draft_id=prior_draft.id if prior_draft else None,
    )
    if all(existing.id != new_draft.id for existing in case.takedown_drafts):
        case.takedown_drafts.append(new_draft)

    call.status = result.status
    call.model = result.model
    call.provider = result.provider
    call.is_incomplete = result.is_incomplete
    call.error_message = result.error_message
    call.response_json = {
        "rationale": result.rationale,
        "draft_id": str(new_draft.id),
        "draft_kind": new_draft.draft_kind,
        "raw_response": result.raw_response,
    }
    call.completed_at = generated_at
    await db.flush()

    await log_action(
        db,
        actor_user_id,
        "case",
        case.id,
        "gemini_generated",
        before_json=before_summary,
        after_json={
            "status": result.status,
            "model": result.model,
            "draft_id": str(new_draft.id),
            "draft_kind": new_draft.draft_kind,
            "is_incomplete": result.is_incomplete,
            "is_fallback": result.is_fallback,
        },
    )
    return case


async def edit_case_draft(
    db: AsyncSession,
    case: Case,
    draft_id: uuid.UUID,
    draft_text: str,
    actor_user_id: uuid.UUID,
) -> TakedownDraft | None:
    source_draft = next((draft for draft in case.takedown_drafts if draft.id == draft_id), None)
    if not source_draft:
        return None

    edited_draft = await save_draft_revision(
        db,
        case_id=case.id,
        draft_text=draft_text,
        model=source_draft.model,
        draft_kind="user_edit",
        actor_user_id=actor_user_id,
        parent_draft_id=source_draft.id,
    )
    if all(existing.id != edited_draft.id for existing in case.takedown_drafts):
        case.takedown_drafts.append(edited_draft)
    await log_action(
        db,
        actor_user_id,
        "case",
        case.id,
        "draft_edited",
        before_json={
            "draft_id": str(source_draft.id),
            "draft_kind": source_draft.draft_kind,
            "text_preview": source_draft.draft_text[:280],
        },
        after_json={
            "draft_id": str(edited_draft.id),
            "parent_draft_id": str(source_draft.id),
            "draft_kind": edited_draft.draft_kind,
            "text_preview": edited_draft.draft_text[:280],
            "delta": _build_delta(source_draft.draft_text, draft_text),
        },
    )
    return edited_draft


async def mark_case_draft_reviewed(
    db: AsyncSession,
    case: Case,
    draft_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> TakedownDraft | None:
    draft = next((item for item in case.takedown_drafts if item.id == draft_id), None)
    if not draft:
        return None

    draft.is_reviewed = True
    draft.reviewed_at = datetime.now(timezone.utc)
    draft.reviewed_by_user_id = actor_user_id
    if case.status == CaseStatus.NEW:
        case.status = CaseStatus.REVIEW
    await db.flush()

    await log_action(
        db,
        actor_user_id,
        "case",
        case.id,
        "draft_reviewed",
        after_json={
            "draft_id": str(draft.id),
            "reviewed_at": draft.reviewed_at.isoformat() if draft.reviewed_at else None,
        },
    )
    return draft


async def count_open_cases(db: AsyncSession, owner_id: uuid.UUID | None = None) -> int:
    q = select(func.count(Case.id)).where(
        Case.status.in_([CaseStatus.NEW, CaseStatus.REVIEW])
    )
    if owner_id:
        q = q.where(Case.owner_id == owner_id)
    r = await db.execute(q)
    return r.scalar() or 0


async def seed_mock_case(db: AsyncSession, owner_id: uuid.UUID) -> Case:
    """Forcefully generate a high-detail Critical Risk mock case for UI testing."""
    # Find or create a dummy asset
    from app.services.asset_service import list_assets, create_asset
    assets = await list_assets(db, owner_id=owner_id)
    if assets:
        asset = assets[0]
    else:
        # Create a mock file
        from fastapi import UploadFile
        import io
        mock_file = UploadFile(filename="mock_asset.png", file=io.BytesIO(b"mock"))
        asset = await create_asset(db, owner_id, "Enterprise Media Asset X-1", "all_rights_reserved", "Private internal distribution only.", [], "image", mock_file)

    # Create a discovery
    from app.models import Discovery, Detection
    discovery = Discovery(
        source_url="https://leaked-content-hub.io/premium/asset-x1",
        platform="Unauthorized Torrent Hub",
        meta_json={"ip": "192.168.1.1", "uploader": "pirate_master_99"}
    )
    db.add(discovery)
    await db.flush()

    # Create a detection
    detection = Detection(
        discovery_id=discovery.id,
        asset_id=asset.id,
        hash_score=0.98,
        embed_score=0.95,
        risk_score=1.0,
        confidence=0.97,
        evidence_json={
            "hash_match": "exact",
            "metadata_overlap": ["title", "dimensions"],
            "risk_factors": ["high_traffic_domain", "no_license_detected"]
        }
    )
    db.add(detection)
    await db.flush()

    # Create the case
    case = Case(
        detection_id=detection.id,
        owner_id=owner_id,
        status="new",
        priority="critical",
        gemini_status="ready",
        gemini_rationale="🚨 CRITICAL RISK DETECTED: This asset ('Enterprise Media Asset X-1') has been found on a high-traffic piracy domain with 98% hash similarity. The uploader identity 'pirate_master_99' is a known repeat infringer.\n\n- Exact perceptual hash match found (0.98).\n- Semantic similarity confirms unauthorized use of core brand identifiers.\n- Source domain is on the global watchlist for IP theft.",
        gemini_model=settings.GEMINI_MODEL,
        gemini_generated_at=datetime.now(timezone.utc)
    )
    db.add(case)
    await db.flush()

    # Add a draft
    draft_text = f"TAKEDOWN NOTICE — CASE {case.id}\n\nWe have identified a critical violation of our protected asset 'Enterprise Media Asset X-1' at https://leaked-content-hub.io/premium/asset-x1. Your domain is hosting unauthorized copies of proprietary media. Immediate removal is required."
    draft = TakedownDraft(
        case_id=case.id,
        draft_text=draft_text,
        model=settings.GEMINI_MODEL,
        draft_kind="gemini"
    )
    db.add(draft)
    await db.flush()
    await db.commit()
    
    return case
