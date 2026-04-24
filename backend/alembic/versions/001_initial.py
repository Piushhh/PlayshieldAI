"""Initial migration — create all tables.

Revision ID: 001_initial
Revises: 
Create Date: 2026-04-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("user", "admin", "reviewer", name="userrole"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table("assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("license_type", sa.String(100), default="all_rights_reserved"),
        sa.Column("allowed_sources_json", postgresql.JSON, default=[]),
        sa.Column("media_gcs_uri", sa.String(1000)),
        sa.Column("media_local_path", sa.String(1000)),
        sa.Column("media_type", sa.Enum("image", "video", name="mediatype"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table("fingerprints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.Enum("phash", "ahash", "dhash", "whash", "clip_embedding", name="fingerprintkind"), nullable=False),
        sa.Column("hash_value", sa.String(500)),
        sa.Column("vector", sa.LargeBinary),
        sa.Column("frame_ts", sa.Float),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fingerprints_asset_kind", "fingerprints", ["asset_id", "kind"])

    op.create_table("discoveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_url", sa.String(2000), nullable=False),
        sa.Column("media_url", sa.String(2000)),
        sa.Column("platform", sa.String(100)),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("meta_json", postgresql.JSON, default={}),
        sa.Column("screenshot_path", sa.String(1000)),
        sa.Column("local_media_path", sa.String(1000)),
    )

    op.create_table("detections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("discovery_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("discoveries.id"), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("hash_score", sa.Float, default=0.0),
        sa.Column("embed_score", sa.Float, default=0.0),
        sa.Column("risk_score", sa.Float, default=0.0),
        sa.Column("confidence", sa.Float, default=0.0),
        sa.Column("evidence_json", postgresql.JSON, default={}),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_detections_confidence", "detections", ["confidence"])

    op.create_table("cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("detection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("detections.id"), nullable=False),
        sa.Column("status", sa.Enum("new", "review", "actioned", "rejected", name="casestatus"), nullable=False),
        sa.Column("priority", sa.Enum("low", "medium", "high", "critical", name="casepriority"), nullable=False),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_cases_status", "cases", ["status"])

    op.create_table("takedown_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("draft_text", sa.Text, nullable=False),
        sa.Column("model", sa.String(100), default="deterministic"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table("audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("before_json", postgresql.JSON),
        sa.Column("after_json", postgresql.JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_entity", "audit_logs", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("takedown_drafts")
    op.drop_table("cases")
    op.drop_table("detections")
    op.drop_table("discoveries")
    op.drop_table("fingerprints")
    op.drop_table("assets")
    op.drop_table("users")
