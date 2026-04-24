"""Worker task implementations (async functions called by Celery tasks)."""

import uuid
from PIL import Image

from app.database import async_session_factory
from app.services import crawler_service, detection_service


async def run_crawl_and_scan(source_configs=None):
    """Crawl sources and scan all new discoveries."""
    async with async_session_factory() as db:
        discoveries = await crawler_service.crawl_sources(db, source_configs)
        await db.commit()

        results = []
        for disc in discoveries:
            media_path = await crawler_service.download_discovery_media(disc)
            if media_path:
                disc.local_media_path = media_path
                try:
                    img = Image.open(media_path).convert("RGB")
                    dets = await detection_service.scan_discovery(db, disc, img)
                    results.append({
                        "discovery_id": str(disc.id),
                        "detections": len(dets),
                    })
                except Exception:
                    pass
        await db.commit()
    return {"discoveries": len(discoveries), "scan_results": results}


async def run_scan_discoveries(discovery_ids=None):
    """Scan specific or all unscanned discoveries."""
    from sqlalchemy import select
    from app.models import Discovery

    async with async_session_factory() as db:
        if discovery_ids:
            q = select(Discovery).where(
                Discovery.id.in_([uuid.UUID(d) for d in discovery_ids])
            )
        else:
            q = select(Discovery)
        result = await db.execute(q)
        discoveries = result.scalars().all()

        scan_results = []
        for disc in discoveries:
            media_path = disc.local_media_path
            if not media_path:
                media_path = await crawler_service.download_discovery_media(disc)
            if media_path:
                try:
                    img = Image.open(media_path).convert("RGB")
                    dets = await detection_service.scan_discovery(db, disc, img)
                    scan_results.append({
                        "discovery_id": str(disc.id),
                        "detections": len(dets),
                    })
                except Exception:
                    pass
        await db.commit()
    return {"scanned": len(scan_results), "results": scan_results}


async def run_rebuild_index():
    """Rebuild FAISS index from DB."""
    async with async_session_factory() as db:
        await detection_service.rebuild_index_from_db(db)
    return {"status": "rebuilt"}
