"""Asset service — upload, manage, and retrieve protected assets (user-scoped)."""

import os
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models import Asset, Detection, MediaType

settings = get_settings()


async def create_asset(
    db: AsyncSession,
    owner_id: uuid.UUID,
    title: str,
    license_type: str,
    allowed_use_notes: str | None,
    allowed_sources: list[str],
    media_type: str,
    file: UploadFile,
) -> Asset:
    """Create a new protected asset and save the uploaded file."""
    asset_id = uuid.uuid4()
    ext = Path(file.filename).suffix if file.filename else ".bin"
    filename = f"{asset_id}{ext}"

    # Save locally
    media_dir = Path(settings.MEDIA_DIR) / "assets"
    media_dir.mkdir(parents=True, exist_ok=True)
    local_path = media_dir / filename

    content = await file.read()
    with open(local_path, "wb") as f:
        f.write(content)

    # Optionally upload to GCS (when configured)
    gcs_uri = None
    try:
        from app.services.storage_service import upload_to_gcs

        gcs_uri = await upload_to_gcs(content, f"assets/{filename}", file.content_type)
    except Exception:
        pass  # GCS optional in local dev

    asset = Asset(
        id=asset_id,
        owner_id=owner_id,
        title=title,
        license_type=license_type,
        allowed_use_notes=allowed_use_notes,
        allowed_sources_json=allowed_sources,
        media_type=MediaType(media_type),
        media_gcs_uri=gcs_uri,
        media_local_path=str(local_path),
    )
    db.add(asset)
    await db.flush()
    return asset


async def list_assets(db: AsyncSession, owner_id: uuid.UUID | None = None) -> list[Asset]:
    """List assets scoped to the owner. If owner_id is None, list all (admin)."""
    query = (
        select(Asset)
        .options(selectinload(Asset.detections).selectinload(Detection.cases))
        .order_by(Asset.created_at.desc())
    )
    if owner_id:
        query = query.where(Asset.owner_id == owner_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_asset(db: AsyncSession, asset_id: uuid.UUID) -> Asset | None:
    """Get a single asset by ID."""
    result = await db.execute(
        select(Asset).where(Asset.id == asset_id).options(selectinload(Asset.fingerprints))
    )
    return result.scalar_one_or_none()


async def count_assets(db: AsyncSession, owner_id: uuid.UUID | None = None) -> int:
    """Count total assets, optionally scoped to owner."""
    q = select(func.count(Asset.id))
    if owner_id:
        q = q.where(Asset.owner_id == owner_id)
    result = await db.execute(q)
    return result.scalar() or 0


async def delete_asset(db: AsyncSession, asset_id: uuid.UUID, owner_id: uuid.UUID) -> bool:
    """Delete an asset (only by owner)."""
    asset = await get_asset(db, asset_id)
    if not asset or asset.owner_id != owner_id:
        return False
    # Delete local file
    if asset.media_local_path and os.path.exists(asset.media_local_path):
        os.remove(asset.media_local_path)
    await db.delete(asset)
    await db.flush()
    return True


async def analyze_asset(db: AsyncSession, asset: Asset) -> Asset:
    """Analyze asset using Gemini and update its rationale/status."""
    from app.services.gemini_service import analyze_asset_risk
    
    asset_data = {
        "title": asset.title,
        "license_type": asset.license_type,
        "media_type": asset.media_type.value if asset.media_type else "image",
        "allowed_use_notes": asset.allowed_use_notes,
    }
    
    asset.gemini_status = "scanning"
    await db.flush()
    
    result = await analyze_asset_risk(asset_data)
    
    asset.gemini_status = result.status
    asset.gemini_rationale = result.rationale
    await db.flush()
    return asset
