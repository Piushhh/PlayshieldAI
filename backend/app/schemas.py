"""Pydantic schemas for API request/response models."""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


# ─── Auth ───────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    is_verified: bool
    email_notifications: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserSettingsUpdate(BaseModel):
    email_notifications: bool | None = None


# ─── Assets ─────────────────────────────────────────────
class AssetCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    license_type: str = "all_rights_reserved"
    allowed_use_notes: str | None = None
    allowed_sources_json: list[str] = Field(default_factory=list)
    media_type: str = "image"  # "image" or "video"


class AssetOut(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    license_type: str
    allowed_use_notes: str | None = None
    allowed_sources_json: list | None = None
    media_gcs_uri: str | None = None
    media_local_path: str | None = None
    media_type: str
    created_at: datetime
    open_case_count: int = 0
    latest_case_id: uuid.UUID | None = None
    latest_case_status: str | None = None
    latest_confidence: float | None = None
    gemini_status: str | None = None
    gemini_rationale: str | None = None
    highest_risk_label: str | None = None

    class Config:
        from_attributes = True


# ─── Discoveries ────────────────────────────────────────
class DiscoveryOut(BaseModel):
    id: uuid.UUID
    source_url: str
    media_url: str | None = None
    platform: str | None = None
    captured_at: datetime
    meta_json: dict | None = None

    class Config:
        from_attributes = True


# ─── Detections ─────────────────────────────────────────
class DetectionOut(BaseModel):
    id: uuid.UUID
    discovery_id: uuid.UUID
    asset_id: uuid.UUID
    hash_score: float
    embed_score: float
    risk_score: float
    confidence: float
    evidence_json: dict | None = None
    created_at: datetime
    discovery: DiscoveryOut | None = None
    asset: AssetOut | None = None

    class Config:
        from_attributes = True


# ─── Cases ──────────────────────────────────────────────
class CaseOut(BaseModel):
    id: uuid.UUID
    detection_id: uuid.UUID
    owner_id: uuid.UUID | None = None
    status: str
    priority: str
    assigned_to: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    gemini_status: str = "pending"
    gemini_rationale: str | None = None
    gemini_model: str | None = None
    gemini_provider: str | None = None
    gemini_error: str | None = None
    gemini_incomplete_reason: str | None = None
    gemini_is_incomplete: bool = True
    gemini_is_fallback: bool = False
    gemini_last_attempted_at: datetime | None = None
    gemini_generated_at: datetime | None = None
    detection: DetectionOut | None = None
    takedown_drafts: list["TakedownDraftOut"] | None = None
    current_draft: Optional["TakedownDraftOut"] = None

    class Config:
        from_attributes = True


class CaseDecisionRequest(BaseModel):
    status: str  # "review", "actioned", "rejected"
    notes: str | None = None


class CaseFromDetectionRequest(BaseModel):
    priority: str = "medium"
    assigned_to: uuid.UUID | None = None


# ─── Takedown Drafts ───────────────────────────────────
class TakedownDraftOut(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    draft_text: str
    model: str
    draft_kind: str
    parent_draft_id: uuid.UUID | None = None
    edited_by_user_id: uuid.UUID | None = None
    reviewed_by_user_id: uuid.UUID | None = None
    is_reviewed: bool = False
    reviewed_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class DraftEditRequest(BaseModel):
    draft_text: str = Field(..., min_length=20)


class GeminiCallOut(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    actor_user_id: uuid.UUID | None = None
    actor_email: str | None = None
    operation: str
    provider: str
    model: str | None = None
    status: str
    is_incomplete: bool
    error_message: str | None = None
    request_json: dict | None = None
    response_json: dict | None = None
    created_at: datetime
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class GeminiSummaryOut(BaseModel):
    case_id: uuid.UUID
    status: str
    rationale: str | None = None
    model: str | None = None
    provider: str | None = None
    error_message: str | None = None
    incomplete_reason: str | None = None
    is_incomplete: bool = True
    is_fallback: bool = False
    generated_at: datetime | None = None
    last_attempted_at: datetime | None = None
    current_draft: TakedownDraftOut | None = None
    draft_history: list[TakedownDraftOut] = Field(default_factory=list)
    recent_calls: list[GeminiCallOut] = Field(default_factory=list)


# ─── Audit Logs ─────────────────────────────────────────
class AuditLogOut(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID | None = None
    actor_email: str | None = None
    entity_type: str
    entity_id: uuid.UUID
    action: str
    before_json: dict | None = None
    after_json: dict | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Notifications ─────────────────────────────────────
class NotificationOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    message: str
    case_id: uuid.UUID | None = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Crawl ──────────────────────────────────────────────
class CrawlRequest(BaseModel):
    sources: list[str] | None = None  # Optional override; uses defaults if not provided


class ScanRequest(BaseModel):
    discovery_ids: list[uuid.UUID] | None = None  # Optional; scans all pending if empty


# ─── Health ─────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    db: str = "connected"
    redis: str = "connected"


# ─── Dashboard Stats ───────────────────────────────────
class DashboardStats(BaseModel):
    total_assets: int = 0
    total_scans: int = 0
    open_cases: int = 0
    total_detections: int = 0
    high_confidence_count: int = 0
    medium_confidence_count: int = 0
    low_confidence_count: int = 0
    trend_data: list[dict] = Field(default_factory=list)
    top_flagged_sources: list[dict[str, Any]] = Field(default_factory=list)
    gemini_overview: list[dict[str, Any]] = Field(default_factory=list)
