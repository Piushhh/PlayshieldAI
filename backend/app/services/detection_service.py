"""Detection service — FAISS index, similarity scanning, and owner notification."""

import os
import uuid
from pathlib import Path

import numpy as np
import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models import (
    Asset, Case, CasePriority, CaseStatus,
    Detection, Discovery, Fingerprint, FingerprintKind, User,
)
from app.services.fingerprint_service import (
    compute_clip_embedding, compute_phash, hash_similarity,
)

settings = get_settings()
logger = structlog.get_logger()
_faiss_index = None
_index_asset_ids: list[str] = []


def _get_faiss():
    try:
        import faiss
        return faiss
    except ImportError:
        return None


def build_faiss_index(embeddings: list[tuple[str, np.ndarray]]):
    global _faiss_index, _index_asset_ids
    faiss = _get_faiss()
    if faiss is None or not embeddings:
        return
    dim = embeddings[0][1].shape[0]
    index = faiss.IndexFlatIP(dim)
    vectors = np.array([e[1] for e in embeddings]).astype(np.float32)
    faiss.normalize_L2(vectors)
    index.add(vectors)
    _faiss_index = index
    _index_asset_ids = [e[0] for e in embeddings]
    idx_dir = Path(settings.FAISS_INDEX_DIR)
    idx_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(idx_dir / "ipguardian.faiss"))
    with open(idx_dir / "asset_ids.txt", "w") as f:
        f.write("\n".join(_index_asset_ids))


def load_faiss_index():
    global _faiss_index, _index_asset_ids
    faiss = _get_faiss()
    if faiss is None:
        return
    ip = Path(settings.FAISS_INDEX_DIR) / "ipguardian.faiss"
    ap = Path(settings.FAISS_INDEX_DIR) / "asset_ids.txt"
    if ip.exists() and ap.exists():
        _faiss_index = faiss.read_index(str(ip))
        with open(ap) as f:
            _index_asset_ids = f.read().strip().split("\n")


def search_faiss(query_embedding: np.ndarray, top_k: int = 5):
    faiss = _get_faiss()
    if faiss is None or _faiss_index is None or _faiss_index.ntotal == 0:
        return []
    q = query_embedding.reshape(1, -1).astype(np.float32)
    faiss.normalize_L2(q)
    dists, idxs = _faiss_index.search(q, min(top_k, _faiss_index.ntotal))
    return [
        (_index_asset_ids[i], float(d))
        for d, i in zip(dists[0], idxs[0])
        if 0 <= i < len(_index_asset_ids)
    ]


async def rebuild_index_from_db(db: AsyncSession):
    result = await db.execute(
        select(Fingerprint).where(Fingerprint.kind == FingerprintKind.CLIP_EMBEDDING)
    )
    embs = [
        (str(fp.asset_id), np.frombuffer(fp.vector, dtype=np.float32))
        for fp in result.scalars().all() if fp.vector
    ]
    if embs:
        build_faiss_index(embs)


def compute_confidence(h: float, e: float, r: float) -> float:
    return settings.WEIGHT_HASH * h + settings.WEIGHT_EMBED * e + settings.WEIGHT_RISK * r


def determine_priority(c: float) -> CasePriority:
    if c >= 0.95:
        return CasePriority.CRITICAL
    if c >= 0.85:
        return CasePriority.HIGH
    if c >= 0.75:
        return CasePriority.MEDIUM
    return CasePriority.LOW


async def _notify_asset_owner(db: AsyncSession, asset: Asset, case: Case, detection: Detection, discovery: Discovery):
    """Notify the asset owner about a new detection via in-app notification + email."""
    try:
        # Get the owner
        result = await db.execute(select(User).where(User.id == asset.owner_id))
        owner = result.scalar_one_or_none()
        if not owner:
            return

        # Create in-app notification
        from app.services.notification_service import create_notification
        await create_notification(
            db,
            user_id=owner.id,
            title=f"🚨 Potential violation of \"{asset.title}\"",
            message=f"A {detection.confidence:.0%} confidence match was found at {discovery.source_url}",
            case_id=case.id,
        )

        # Send email if user has notifications enabled
        if owner.email_notifications:
            from app.services.alert_service import send_detection_notification
            await send_detection_notification(
                user_email=owner.email,
                case_id=str(case.id),
                asset_title=asset.title,
                confidence=detection.confidence,
                source_url=discovery.source_url,
            )

        logger.info("Owner notified", user_id=str(owner.id), asset_id=str(asset.id), case_id=str(case.id))
    except Exception as e:
        logger.error("Failed to notify owner", error=str(e))


async def scan_discovery(db: AsyncSession, discovery: Discovery, query_img):
    detections = []
    query_phash = compute_phash(query_img)
    query_emb = compute_clip_embedding(query_img)
    nn = search_faiss(query_emb, top_k=10)
    pr = await db.execute(
        select(Fingerprint).where(Fingerprint.kind == FingerprintKind.PHASH)
    )
    ahm = {str(fp.asset_id): fp.hash_value for fp in pr.scalars().all() if fp.hash_value}
    cands, es = set(), {}
    for aid, sc in nn:
        cands.add(aid)
        es[aid] = max(0.0, sc)
    for aid, hv in ahm.items():
        if hash_similarity(query_phash, hv) >= 0.6:
            cands.add(aid)
    for aid in cands:
        hs = hash_similarity(query_phash, ahm[aid]) if aid in ahm else 0.0
        esc = es.get(aid, 0.0)
        ar = await db.execute(select(Asset).where(Asset.id == uuid.UUID(aid)))
        asset = ar.scalar_one_or_none()
        if not asset:
            continue
        rs = 1.0
        if asset.allowed_sources_json:
            for a in asset.allowed_sources_json:
                if a.lower() in discovery.source_url.lower():
                    rs = 0.0
                    break
        conf = compute_confidence(hs, esc, rs)
        det = Detection(
            discovery_id=discovery.id, asset_id=uuid.UUID(aid),
            hash_score=hs, embed_score=esc, risk_score=rs,
            confidence=conf, evidence_json={
                "hash_score": round(hs, 4), "embed_score": round(esc, 4),
                "risk_score": round(rs, 4), "source_url": discovery.source_url,
            },
        )
        db.add(det)
        await db.flush()
        detections.append(det)
        if conf >= settings.CONFIDENCE_THRESHOLD:
            case = Case(
                detection_id=det.id,
                owner_id=asset.owner_id,  # Link case to asset owner
                status=CaseStatus.NEW,
                priority=determine_priority(conf),
            )
            db.add(case)
            await db.flush()
            # Notify the asset owner
            await _notify_asset_owner(db, asset, case, det, discovery)
            try:
                from app.services.case_service import generate_case_gemini_content, get_case

                hydrated_case = await get_case(db, case.id)
                if hydrated_case:
                    await generate_case_gemini_content(
                        db,
                        hydrated_case,
                        actor_user_id=None,
                        force=True,
                    )
            except Exception as exc:
                logger.warning(
                    "Gemini generation failed during case creation",
                    case_id=str(case.id),
                    error=str(exc),
                )
    await db.flush()
    return detections


async def list_detections(
    db: AsyncSession,
    min_confidence: float | None = None,
    owner_id: uuid.UUID | None = None,
):
    """List detections, optionally scoped to assets owned by a user."""
    q = select(Detection).options(
        selectinload(Detection.discovery), selectinload(Detection.asset),
    ).order_by(Detection.confidence.desc())
    if min_confidence is not None:
        q = q.where(Detection.confidence >= min_confidence)
    if owner_id:
        q = q.join(Asset, Detection.asset_id == Asset.id).where(Asset.owner_id == owner_id)
    return list((await db.execute(q)).scalars().all())


async def count_detections(db: AsyncSession, owner_id: uuid.UUID | None = None) -> int:
    q = select(func.count(Detection.id))
    if owner_id:
        q = q.join(Asset, Detection.asset_id == Asset.id).where(Asset.owner_id == owner_id)
    return (await db.execute(q)).scalar() or 0


async def count_detections_by_band(db: AsyncSession, owner_id: uuid.UUID | None = None):
    def _q(condition):
        q = select(func.count(Detection.id)).where(condition)
        if owner_id:
            q = q.join(Asset, Detection.asset_id == Asset.id).where(Asset.owner_id == owner_id)
        return q

    h = (await db.execute(_q(Detection.confidence >= 0.85))).scalar() or 0
    m = (await db.execute(_q((Detection.confidence >= 0.6) & (Detection.confidence < 0.85)))).scalar() or 0
    lo = (await db.execute(_q(Detection.confidence < 0.6))).scalar() or 0
    return h, m, lo
