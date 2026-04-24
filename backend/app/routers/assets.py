"""Assets router — upload, list, delete protected assets (user-scoped)."""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import CaseStatus, User, UserRole
from app.schemas import AssetOut
from app.services.asset_service import create_asset, delete_asset, list_assets
from app.services.auth_service import get_current_user
from app.services.fingerprint_service import fingerprint_asset
from app.services.audit_service import log_action

router = APIRouter(prefix="/assets", tags=["assets"])


def _risk_label(confidence: float | None) -> str | None:
    if confidence is None:
        return None
    if confidence >= 0.85:
        return "High risk"
    if confidence >= 0.6:
        return "Watchlist"
    return "Low risk"


@router.post("", response_model=AssetOut)
async def upload_asset(
    title: str = Form(...),
    license_type: str = Form("all_rights_reserved"),
    allowed_use_notes: str = Form(None),
    media_type: str = Form("image"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    asset = await create_asset(
        db, user.id, title, license_type, allowed_use_notes, [], media_type, file
    )
    # Generate fingerprints
    await fingerprint_asset(db, asset)
    # Rebuild FAISS index
    from app.services.detection_service import rebuild_index_from_db
    await rebuild_index_from_db(db)
    # Audit log
    await log_action(db, user.id, "asset", asset.id, "created",
                     after_json={"title": asset.title, "media_type": media_type})
    return asset


@router.get("", response_model=list[AssetOut])
async def get_assets(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List assets scoped to the current user. Admins see all."""
    owner_id = None if user.role == UserRole.ADMIN else user.id
    assets = await list_assets(db, owner_id=owner_id)

    for asset in assets:
        case_pairs: list[tuple] = []
        for detection in asset.detections:
            for case in detection.cases:
                case_pairs.append((case, detection))

        case_pairs.sort(
            key=lambda pair: pair[0].created_at.timestamp() if pair[0].created_at else 0,
            reverse=True,
        )

        latest_case = case_pairs[0][0] if case_pairs else None
        latest_detection = case_pairs[0][1] if case_pairs else None
        open_case_count = sum(
            1
            for case, _ in case_pairs
            if case.status in {CaseStatus.NEW, CaseStatus.REVIEW}
        )

        asset.open_case_count = open_case_count
        asset.latest_case_id = latest_case.id if latest_case else None
        asset.latest_case_status = latest_case.status.value if latest_case else None
        asset.latest_confidence = latest_detection.confidence if latest_detection else None
        asset.gemini_status = asset.gemini_status or (latest_case.gemini_status if latest_case else None)
        asset.gemini_rationale = asset.gemini_rationale or (latest_case.gemini_rationale if latest_case else None)
        asset.highest_risk_label = _risk_label(asset.latest_confidence)

    return assets


@router.delete("/{asset_id}")
async def remove_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete an asset (only by owner)."""
    success = await delete_asset(db, uuid.UUID(asset_id), user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Asset not found or not owned by you")
    await log_action(db, user.id, "asset", uuid.UUID(asset_id), "deleted")
    return {"message": "Asset deleted"}


@router.post("/{asset_id}/analyze", response_model=AssetOut)
async def trigger_asset_analysis(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Trigger an AI risk scan for a specific asset."""
    from app.services.asset_service import get_asset, analyze_asset
    
    asset = await get_asset(db, uuid.UUID(asset_id))
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    if asset.owner_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await analyze_asset(db, asset)
    await db.commit()
    
    # Audit log
    await log_action(db, user.id, "asset", asset.id, "ai_scan_triggered")
    
    return asset
