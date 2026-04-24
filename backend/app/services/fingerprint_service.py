"""Fingerprint service — perceptual hashing and CLIP embedding extraction."""

import io
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional

import imagehash
import numpy as np
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Asset, Fingerprint, FingerprintKind, MediaType

settings = get_settings()


def compute_phash(img: Image.Image) -> str:
    """Compute perceptual hash of an image."""
    return str(imagehash.phash(img, hash_size=16))


def compute_ahash(img: Image.Image) -> str:
    """Compute average hash of an image."""
    return str(imagehash.average_hash(img, hash_size=16))


def compute_dhash(img: Image.Image) -> str:
    """Compute difference hash of an image."""
    return str(imagehash.dhash(img, hash_size=16))


def hash_similarity(hash1: str, hash2: str) -> float:
    """Calculate similarity between two hex hash strings (0 to 1)."""
    h1 = imagehash.hex_to_hash(hash1)
    h2 = imagehash.hex_to_hash(hash2)
    max_bits = len(h1.hash.flatten())
    distance = h1 - h2
    return 1.0 - (distance / max_bits)


def compute_clip_embedding(img: Image.Image) -> np.ndarray:
    """Compute CLIP embedding for an image.
    
    Uses a lightweight approach: resize image to 224x224 and create
    a normalized feature vector from pixel values as a stand-in 
    for actual CLIP when the model isn't available.
    """
    try:
        # Try using actual CLIP via sentence-transformers
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("clip-ViT-B-32")
        embedding = model.encode(img)
        return embedding / np.linalg.norm(embedding)
    except ImportError:
        # Fallback: create a deterministic 512-dim feature vector from image content
        img_resized = img.resize((224, 224)).convert("RGB")
        arr = np.array(img_resized, dtype=np.float32).flatten()
        # Subsample to 512 dimensions
        indices = np.linspace(0, len(arr) - 1, 512, dtype=int)
        features = arr[indices]
        # Normalize
        norm = np.linalg.norm(features)
        if norm > 0:
            features = features / norm
        return features.astype(np.float32)


def extract_keyframes(video_path: str, max_frames: int = 10) -> list[tuple[float, Image.Image]]:
    """Extract keyframes from a video using FFmpeg."""
    frames = []
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vf", f"select=eq(pict_type\\,I),scale=448:448",
            "-vsync", "vfr",
            "-frames:v", str(max_frames),
            "-f", "image2",
            os.path.join(tmpdir, "frame_%04d.png"),
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=60, check=True)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            # Fallback: extract at regular intervals
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vf", f"fps=1/{max(1, 10)},scale=448:448",
                "-frames:v", str(max_frames),
                "-f", "image2",
                os.path.join(tmpdir, "frame_%04d.png"),
            ]
            subprocess.run(cmd, capture_output=True, timeout=60)

        for i, fpath in enumerate(sorted(Path(tmpdir).glob("frame_*.png"))):
            img = Image.open(fpath).convert("RGB")
            timestamp = float(i)  # Approximate timestamp
            frames.append((timestamp, img))

    return frames


async def fingerprint_asset(db: AsyncSession, asset: Asset) -> list[Fingerprint]:
    """Generate all fingerprints for an asset."""
    fingerprints = []
    media_path = asset.media_local_path

    if not media_path or not os.path.exists(media_path):
        return fingerprints

    if asset.media_type == MediaType.IMAGE:
        img = Image.open(media_path).convert("RGB")
        fingerprints.extend(await _fingerprint_image(db, asset.id, img))

    elif asset.media_type == MediaType.VIDEO:
        frames = extract_keyframes(media_path)
        for ts, frame_img in frames:
            fingerprints.extend(await _fingerprint_image(db, asset.id, frame_img, frame_ts=ts))

    return fingerprints


async def _fingerprint_image(
    db: AsyncSession,
    asset_id: uuid.UUID,
    img: Image.Image,
    frame_ts: float | None = None,
) -> list[Fingerprint]:
    """Create fingerprint records for a single image."""
    fps = []

    # Perceptual hashes
    for kind, func in [
        (FingerprintKind.PHASH, compute_phash),
        (FingerprintKind.AHASH, compute_ahash),
        (FingerprintKind.DHASH, compute_dhash),
    ]:
        hash_val = func(img)
        fp = Fingerprint(
            asset_id=asset_id,
            kind=kind,
            hash_value=hash_val,
            frame_ts=frame_ts,
        )
        db.add(fp)
        fps.append(fp)

    # CLIP embedding
    embedding = compute_clip_embedding(img)
    fp = Fingerprint(
        asset_id=asset_id,
        kind=FingerprintKind.CLIP_EMBEDDING,
        vector=embedding.tobytes(),
        frame_ts=frame_ts,
    )
    db.add(fp)
    fps.append(fp)

    await db.flush()
    return fps


async def get_asset_fingerprints(
    db: AsyncSession, asset_id: uuid.UUID
) -> list[Fingerprint]:
    """Get all fingerprints for an asset."""
    result = await db.execute(
        select(Fingerprint).where(Fingerprint.asset_id == asset_id)
    )
    return list(result.scalars().all())
