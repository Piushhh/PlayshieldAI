"""Celery worker configuration and tasks."""

from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ipguardian",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_max_tasks_per_child=100,
)


@celery_app.task(name="crawl_and_scan")
def crawl_and_scan_task(source_configs: list[dict] | None = None):
    """Background task: crawl sources then scan discoveries."""
    import asyncio
    from app.worker_tasks import run_crawl_and_scan
    return asyncio.get_event_loop().run_until_complete(
        run_crawl_and_scan(source_configs)
    )


@celery_app.task(name="scan_discoveries")
def scan_discoveries_task(discovery_ids: list[str] | None = None):
    """Background task: scan specific discoveries."""
    import asyncio
    from app.worker_tasks import run_scan_discoveries
    return asyncio.get_event_loop().run_until_complete(
        run_scan_discoveries(discovery_ids)
    )


@celery_app.task(name="rebuild_index")
def rebuild_index_task():
    """Background task: rebuild FAISS index."""
    import asyncio
    from app.worker_tasks import run_rebuild_index
    return asyncio.get_event_loop().run_until_complete(run_rebuild_index())
