"""SQLAlchemy ORM models for IP Guardian."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.database import Base


# ─── Enums ──────────────────────────────────────────────
class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    REVIEWER = "reviewer"


class MediaType(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"


class FingerprintKind(str, enum.Enum):
    PHASH = "phash"
    AHASH = "ahash"
    DHASH = "dhash"
    WHASH = "whash"
    CLIP_EMBEDDING = "clip_embedding"


class CaseStatus(str, enum.Enum):
    NEW = "new"
    REVIEW = "review"
    ACTIONED = "actioned"
    REJECTED = "rejected"


class CasePriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ─── Users ──────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole, values_callable=lambda x: [e.value for e in x]), nullable=False, default=UserRole.USER)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255), nullable=True)
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)
    email_notifications = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    assets = relationship("Asset", back_populates="owner")
    assigned_cases = relationship("Case", back_populates="assignee", foreign_keys="Case.assigned_to")
    owned_cases = relationship("Case", back_populates="owner", foreign_keys="Case.owner_id")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


# ─── Assets ─────────────────────────────────────────────
class Asset(Base):
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=False)
    license_type = Column(String(100), default="all_rights_reserved")
    allowed_use_notes = Column(Text, nullable=True)
    allowed_sources_json = Column(JSON, default=list)
    media_gcs_uri = Column(String(1000), nullable=True)
    media_local_path = Column(String(1000), nullable=True)
    media_type = Column(Enum(MediaType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="assets")
    fingerprints = relationship("Fingerprint", back_populates="asset", cascade="all, delete-orphan")
    detections = relationship("Detection", back_populates="asset")


# ─── Fingerprints ───────────────────────────────────────
class Fingerprint(Base):
    __tablename__ = "fingerprints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    kind = Column(Enum(FingerprintKind, values_callable=lambda x: [e.value for e in x]), nullable=False)
    hash_value = Column(String(500), nullable=True)
    vector = Column(LargeBinary, nullable=True)
    frame_ts = Column(Float, nullable=True)  # timestamp in seconds for video frames
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    asset = relationship("Asset", back_populates="fingerprints")

    __table_args__ = (
        Index("ix_fingerprints_asset_kind", "asset_id", "kind"),
    )


# ─── Discoveries ────────────────────────────────────────
class Discovery(Base):
    __tablename__ = "discoveries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_url = Column(String(2000), nullable=False)
    media_url = Column(String(2000), nullable=True)
    platform = Column(String(100), nullable=True)
    captured_at = Column(DateTime(timezone=True), server_default=func.now())
    meta_json = Column(JSON, default=dict)
    screenshot_path = Column(String(1000), nullable=True)
    local_media_path = Column(String(1000), nullable=True)

    detections = relationship("Detection", back_populates="discovery")


# ─── Detections ─────────────────────────────────────────
class Detection(Base):
    __tablename__ = "detections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    discovery_id = Column(UUID(as_uuid=True), ForeignKey("discoveries.id"), nullable=False)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    hash_score = Column(Float, default=0.0)
    embed_score = Column(Float, default=0.0)
    risk_score = Column(Float, default=0.0)
    confidence = Column(Float, default=0.0)
    evidence_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    discovery = relationship("Discovery", back_populates="detections")
    asset = relationship("Asset", back_populates="detections")
    cases = relationship("Case", back_populates="detection")

    __table_args__ = (
        Index("ix_detections_confidence", "confidence"),
    )


# ─── Cases ──────────────────────────────────────────────
class Case(Base):
    __tablename__ = "cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    detection_id = Column(UUID(as_uuid=True), ForeignKey("detections.id"), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status = Column(Enum(CaseStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=CaseStatus.NEW)
    priority = Column(Enum(CasePriority, values_callable=lambda x: [e.value for e in x]), nullable=False, default=CasePriority.MEDIUM)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    gemini_status = Column(String(50), nullable=False, default="pending")
    gemini_rationale = Column(Text, nullable=True)
    gemini_model = Column(String(100), nullable=True)
    gemini_provider = Column(String(50), nullable=True, default="vertex_ai")
    gemini_error = Column(Text, nullable=True)
    gemini_incomplete_reason = Column(Text, nullable=True)
    gemini_is_incomplete = Column(Boolean, nullable=False, default=True)
    gemini_is_fallback = Column(Boolean, nullable=False, default=False)
    gemini_last_attempted_at = Column(DateTime(timezone=True), nullable=True)
    gemini_generated_at = Column(DateTime(timezone=True), nullable=True)

    detection = relationship("Detection", back_populates="cases")
    owner = relationship("User", back_populates="owned_cases", foreign_keys=[owner_id])
    assignee = relationship("User", back_populates="assigned_cases", foreign_keys=[assigned_to])
    takedown_drafts = relationship("TakedownDraft", back_populates="case", cascade="all, delete-orphan")
    gemini_calls = relationship("GeminiCall", back_populates="case", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_cases_status", "status"),
        Index("ix_cases_owner", "owner_id"),
    )

    @property
    def current_draft(self):
        if not self.takedown_drafts:
            return None
        return max(
            self.takedown_drafts,
            key=lambda draft: draft.created_at.timestamp() if draft.created_at else 0,
        )


# ─── Takedown Drafts ───────────────────────────────────
class TakedownDraft(Base):
    __tablename__ = "takedown_drafts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    draft_text = Column(Text, nullable=False)
    model = Column(String(100), default="deterministic")
    draft_kind = Column(String(50), nullable=False, default="gemini")
    parent_draft_id = Column(
        UUID(as_uuid=True),
        ForeignKey("takedown_drafts.id", ondelete="SET NULL"),
        nullable=True,
    )
    edited_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_reviewed = Column(Boolean, nullable=False, default=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    case = relationship("Case", back_populates="takedown_drafts")
    parent_draft = relationship("TakedownDraft", remote_side=[id])
    edited_by_user = relationship("User", foreign_keys=[edited_by_user_id])
    reviewed_by_user = relationship("User", foreign_keys=[reviewed_by_user_id])


# ─── Gemini Call Logs ──────────────────────────────────
class GeminiCall(Base):
    __tablename__ = "gemini_calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    operation = Column(String(50), nullable=False, default="generate_case_content")
    provider = Column(String(50), nullable=False, default="vertex_ai")
    model = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    is_incomplete = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    request_json = Column(JSON, nullable=True)
    response_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    case = relationship("Case", back_populates="gemini_calls")
    actor = relationship("User", foreign_keys=[actor_user_id])

    __table_args__ = (
        Index("ix_gemini_calls_case", "case_id", "created_at"),
    )

    @property
    def actor_email(self):
        return self.actor.email if self.actor else None


# ─── Audit Logs ─────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    entity_type = Column(String(50), nullable=False)  # case, asset, detection, etc.
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(String(100), nullable=False)
    before_json = Column(JSON, nullable=True)
    after_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    actor = relationship("User", foreign_keys=[actor_user_id])

    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
    )

    @property
    def actor_email(self):
        return self.actor.email if self.actor else None


# ─── Notifications ─────────────────────────────────────
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="SET NULL"), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")

    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "is_read"),
    )
