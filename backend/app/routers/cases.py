"""Cases router — case management, decisions, draft generation (user-scoped)."""

import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, UserRole
from app.schemas import (
    CaseDecisionRequest,
    CaseFromDetectionRequest,
    CaseOut,
    DraftEditRequest,
    GeminiSummaryOut,
    TakedownDraftOut,
)
from app.services.auth_service import get_current_user
from app.services.case_service import (
    create_case_from_detection,
    edit_case_draft,
    generate_case_gemini_content,
    generate_case_gemini_content_background,
    get_case,
    list_cases,
    mark_case_draft_reviewed,
    serialize_gemini_summary,
    update_case_status,
)

from app.services.audit_service import log_action

router = APIRouter(prefix="/cases", tags=["cases"])


def _can_access_case(user: User, case) -> bool:
    """Check if user can access this case (owner or admin)."""
    if user.role == UserRole.ADMIN:
        return True
    return case.owner_id == user.id


@router.get("", response_model=list[CaseOut])
async def get_cases(
    status: str | None = None,
    min_confidence: float | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List cases scoped to current user. Admins see all."""
    owner_id = None if user.role == UserRole.ADMIN else user.id
    return await list_cases(db, status=status, min_confidence=min_confidence, owner_id=owner_id)


@router.get("/{case_id}", response_model=CaseOut)
async def get_case_detail(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    case = await get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not _can_access_case(user, case):
        raise HTTPException(status_code=403, detail="Access denied")
    return case


@router.post("/from-detection/{detection_id}", response_model=CaseOut)
async def create_case(
    detection_id: uuid.UUID,
    req: CaseFromDetectionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    case = await create_case_from_detection(
        db, detection_id, owner_id=user.id, priority=req.priority, assigned_to=req.assigned_to
    )
    await log_action(db, user.id, "case", case.id, "created",
                     after_json={"detection_id": str(detection_id), "priority": req.priority})
    
    # Non-blocking Gemini generation
    hydrated_case = await get_case(db, case.id)
    if hydrated_case:
        background_tasks.add_task(generate_case_gemini_content_background, case.id, actor_user_id=user.id)
    
    return hydrated_case



@router.post("/{case_id}/decision", response_model=CaseOut)
async def decide_case(
    case_id: uuid.UUID,
    req: CaseDecisionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    case = await get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not _can_access_case(user, case):
        raise HTTPException(status_code=403, detail="Access denied")
    old_status = case.status.value
    await update_case_status(db, case_id, req.status)
    await log_action(db, user.id, "case", case_id, "status_changed",
                     before_json={"status": old_status},
                     after_json={"status": req.status, "notes": req.notes})
    return await get_case(db, case_id)


@router.get("/{case_id}/gemini-summary", response_model=GeminiSummaryOut)
async def get_gemini_summary(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    case = await get_case(db, case_id)
    if not case or not case.detection:
        raise HTTPException(status_code=404, detail="Case not found")
    if not _can_access_case(user, case):
        raise HTTPException(status_code=403, detail="Access denied")
    return serialize_gemini_summary(case)


@router.post("/{case_id}/generate-gemini", response_model=GeminiSummaryOut)
async def generate_gemini(
    case_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    case = await get_case(db, case_id)
    if not case or not case.detection:
        raise HTTPException(status_code=404, detail="Case not found")
    if not _can_access_case(user, case):
        raise HTTPException(status_code=403, detail="Access denied")

    # Move to background-safe task
    background_tasks.add_task(generate_case_gemini_content_background, case.id, actor_user_id=user.id)
    
    # Return current state immediately
    return serialize_gemini_summary(case)


@router.post("/{case_id}/generate-draft", response_model=TakedownDraftOut)
async def generate_draft(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    case = await get_case(db, case_id)
    if not case or not case.detection:
        raise HTTPException(status_code=404, detail="Case not found")
    if not _can_access_case(user, case):
        raise HTTPException(status_code=403, detail="Access denied")

    await generate_case_gemini_content(db, case, actor_user_id=user.id, force=True)
    refreshed = await get_case(db, case_id)
    if not refreshed or not refreshed.current_draft:
        raise HTTPException(status_code=500, detail="Draft generation did not return a draft")
    return refreshed.current_draft


@router.patch("/{case_id}/drafts/{draft_id}", response_model=TakedownDraftOut)
async def edit_draft(
    case_id: uuid.UUID,
    draft_id: uuid.UUID,
    req: DraftEditRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    case = await get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not _can_access_case(user, case):
        raise HTTPException(status_code=403, detail="Access denied")

    draft = await edit_case_draft(db, case, draft_id, req.draft_text, user.id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.post("/{case_id}/drafts/{draft_id}/review", response_model=TakedownDraftOut)
async def review_draft(
    case_id: uuid.UUID,
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    case = await get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not _can_access_case(user, case):
        raise HTTPException(status_code=403, detail="Access denied")

    draft = await mark_case_draft_reviewed(db, case, draft_id, user.id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.get("/{case_id}/export-draft")
async def export_draft(
    case_id: uuid.UUID,
    format: str = Query("txt", pattern="^(txt|md)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    case = await get_case(db, case_id)
    if not case or not case.takedown_drafts:
        raise HTTPException(status_code=404, detail="No drafts found")
    if not _can_access_case(user, case):
        raise HTTPException(status_code=403, detail="Access denied")
    latest = case.current_draft
    if not latest:
        raise HTTPException(status_code=404, detail="No drafts found")
    await log_action(db, user.id, "case", case_id, "draft_exported",
                     after_json={"format": format, "draft_id": str(latest.id)})
    ct = "text/markdown" if format == "md" else "text/plain"
    return PlainTextResponse(content=latest.draft_text, media_type=ct, headers={
        "Content-Disposition": f"attachment; filename=takedown_draft_{case_id}.{format}"
    })


@router.post("/seed-mock", response_model=CaseOut)
async def create_mock_case(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Forcefully generate a high-detail Critical Risk mock case for UI testing."""
    from app.services.case_service import seed_mock_case
    case = await seed_mock_case(db, user.id)
    # Re-fetch to hydrate relationships
    return await get_case(db, case.id)
