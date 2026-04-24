"""Crawler service — Playwright-based web crawler for media discovery."""

import asyncio
import os
import uuid
from pathlib import Path
from urllib.parse import urljoin, urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Discovery

settings = get_settings()

# Default crawl sources (configurable)
DEFAULT_SOURCES = [
    {"name": "Unsplash", "url": "https://unsplash.com/s/photos/sample", "selector": "img[src]"},
    {"name": "Pexels", "url": "https://www.pexels.com/search/nature/", "selector": "img[src]"},
    {"name": "Pixabay", "url": "https://pixabay.com/images/search/nature/", "selector": "img[src]"},
]


async def crawl_sources(db: AsyncSession, sources: list[dict] | None = None) -> list[Discovery]:
    """Crawl configured sources and save discovered media items."""
    targets = sources or DEFAULT_SOURCES
    discoveries = []

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return discoveries

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for source in targets:
            try:
                page = await browser.new_page()
                await page.goto(source["url"], timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(settings.CRAWLER_RATE_LIMIT_SECONDS)

                # Extract image URLs
                selector = source.get("selector", "img[src]")
                elements = await page.query_selector_all(selector)

                for elem in elements[:20]:  # Limit per source
                    src = await elem.get_attribute("src")
                    if not src or not src.startswith("http"):
                        src = urljoin(source["url"], src) if src else None
                    if not src:
                        continue

                    # Take screenshot
                    ss_dir = Path(settings.MEDIA_DIR) / "screenshots"
                    ss_dir.mkdir(parents=True, exist_ok=True)
                    ss_path = str(ss_dir / f"{uuid.uuid4()}.png")
                    try:
                        await page.screenshot(path=ss_path, full_page=False)
                    except Exception:
                        ss_path = None

                    disc = Discovery(
                        source_url=source["url"],
                        media_url=src,
                        platform=source.get("name", urlparse(source["url"]).netloc),
                        meta_json={"source_name": source.get("name"), "selector": selector},
                        screenshot_path=ss_path,
                    )
                    db.add(disc)
                    discoveries.append(disc)

                await page.close()
            except Exception:
                continue

        await browser.close()

    await db.flush()
    return discoveries


async def download_discovery_media(discovery: Discovery) -> str | None:
    """Download media from a discovery URL."""
    if not discovery.media_url:
        return None
    try:
        import httpx
        dl_dir = Path(settings.MEDIA_DIR) / "discoveries"
        dl_dir.mkdir(parents=True, exist_ok=True)
        ext = Path(urlparse(discovery.media_url).path).suffix or ".jpg"
        local_path = str(dl_dir / f"{discovery.id}{ext}")
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(discovery.media_url, timeout=30)
            if resp.status_code == 200:
                with open(local_path, "wb") as f:
                    f.write(resp.content)
                return local_path
    except Exception:
        pass
    return None
