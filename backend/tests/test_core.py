"""Unit tests for IP Guardian backend."""

import pytest
import numpy as np
from unittest.mock import AsyncMock, patch


class TestScoringLogic:
    """Test confidence scoring calculations."""

    def test_confidence_calculation(self):
        from app.services.detection_service import compute_confidence
        # Default weights: hash=0.4, embed=0.4, risk=0.2
        result = compute_confidence(1.0, 1.0, 1.0)
        assert abs(result - 1.0) < 0.001

    def test_confidence_zero(self):
        from app.services.detection_service import compute_confidence
        result = compute_confidence(0.0, 0.0, 0.0)
        assert result == 0.0

    def test_confidence_mixed(self):
        from app.services.detection_service import compute_confidence
        result = compute_confidence(0.8, 0.9, 0.5)
        expected = 0.4 * 0.8 + 0.4 * 0.9 + 0.2 * 0.5
        assert abs(result - expected) < 0.001

    def test_threshold_case_creation_high(self):
        from app.services.detection_service import determine_priority
        from app.models import CasePriority
        assert determine_priority(0.96) == CasePriority.CRITICAL
        assert determine_priority(0.90) == CasePriority.HIGH
        assert determine_priority(0.80) == CasePriority.MEDIUM
        assert determine_priority(0.50) == CasePriority.LOW


class TestHashSimilarity:
    """Test perceptual hash similarity."""

    def test_identical_hashes(self):
        from app.services.fingerprint_service import hash_similarity
        h = "a" * 64
        assert hash_similarity(h, h) == 1.0

    def test_hash_computation(self):
        from PIL import Image
        from app.services.fingerprint_service import compute_phash
        img = Image.new("RGB", (64, 64), color=(128, 128, 128))
        h = compute_phash(img)
        assert isinstance(h, str)
        assert len(h) > 0


class TestClipEmbedding:
    """Test CLIP embedding extraction."""

    def test_embedding_shape(self):
        from PIL import Image
        from app.services.fingerprint_service import compute_clip_embedding
        img = Image.new("RGB", (100, 100), color=(200, 100, 50))
        emb = compute_clip_embedding(img)
        assert emb.shape == (512,)
        assert abs(np.linalg.norm(emb) - 1.0) < 0.01  # Normalized

    def test_different_images_different_embeddings(self):
        from PIL import Image
        from app.services.fingerprint_service import compute_clip_embedding
        img1 = Image.new("RGB", (100, 100), color=(255, 0, 0))
        img2 = Image.new("RGB", (100, 100), color=(0, 0, 255))
        e1 = compute_clip_embedding(img1)
        e2 = compute_clip_embedding(img2)
        assert not np.allclose(e1, e2)


class TestGeminiFallback:
    """Test Gemini service with fallback."""

    @pytest.mark.asyncio
    async def test_deterministic_fallback(self):
        from app.services.gemini_service import generate_takedown_draft
        case_data = {
            "detection": {"confidence": 0.92, "hash_score": 0.88,
                         "embed_score": 0.95, "risk_score": 1.0},
            "asset": {"title": "Test Asset", "license_type": "all_rights_reserved"},
            "discovery": {"source_url": "https://example.com", "platform": "Test"},
        }
        # This will fall back to deterministic since Vertex AI isn't configured
        draft, model = await generate_takedown_draft(case_data)
        assert "TAKEDOWN NOTICE" in draft or "takedown" in draft.lower()
        assert "LEGAL DISCLAIMER" in draft
        assert model in ["deterministic", "gemini-2.0-flash"]

    def test_deterministic_template_contains_fields(self):
        from app.services.gemini_service import _deterministic_draft
        case_data = {
            "detection": {"confidence": 0.85, "hash_score": 0.8,
                         "embed_score": 0.9, "risk_score": 1.0},
            "asset": {"title": "My Logo", "license_type": "all_rights_reserved"},
            "discovery": {"source_url": "https://pirate-site.com"},
        }
        draft = _deterministic_draft(case_data)
        assert "My Logo" in draft
        assert "pirate-site.com" in draft


class TestRBAC:
    """Test role-based access control."""

    def test_password_hashing(self):
        from app.services.auth_service import hash_password, verify_password
        hashed = hash_password("test123")
        assert verify_password("test123", hashed)
        assert not verify_password("wrong", hashed)

    def test_token_creation(self):
        from app.services.auth_service import create_access_token, decode_token
        token = create_access_token("user-123", "admin")
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"

    def test_refresh_token(self):
        from app.services.auth_service import create_refresh_token, decode_token
        token = create_refresh_token("user-456")
        payload = decode_token(token)
        assert payload["sub"] == "user-456"
        assert payload["type"] == "refresh"
