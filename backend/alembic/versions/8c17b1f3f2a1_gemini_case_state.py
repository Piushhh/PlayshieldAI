"""gemini_case_state

Revision ID: 8c17b1f3f2a1
Revises: ba4f1295473c
Create Date: 2026-04-23 21:05:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8c17b1f3f2a1"
down_revision: Union[str, None] = "ba4f1295473c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cases", sa.Column("gemini_status", sa.String(length=50), nullable=False, server_default="pending"))
    op.add_column("cases", sa.Column("gemini_rationale", sa.Text(), nullable=True))
    op.add_column("cases", sa.Column("gemini_model", sa.String(length=100), nullable=True))
    op.add_column("cases", sa.Column("gemini_provider", sa.String(length=50), nullable=True, server_default="vertex_ai"))
    op.add_column("cases", sa.Column("gemini_error", sa.Text(), nullable=True))
    op.add_column("cases", sa.Column("gemini_incomplete_reason", sa.Text(), nullable=True))
    op.add_column("cases", sa.Column("gemini_is_incomplete", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("cases", sa.Column("gemini_is_fallback", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("cases", sa.Column("gemini_last_attempted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("cases", sa.Column("gemini_generated_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("takedown_drafts", sa.Column("draft_kind", sa.String(length=50), nullable=False, server_default="gemini"))
    op.add_column("takedown_drafts", sa.Column("parent_draft_id", sa.UUID(), nullable=True))
    op.add_column("takedown_drafts", sa.Column("edited_by_user_id", sa.UUID(), nullable=True))
    op.add_column("takedown_drafts", sa.Column("reviewed_by_user_id", sa.UUID(), nullable=True))
    op.add_column("takedown_drafts", sa.Column("is_reviewed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("takedown_drafts", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_takedown_drafts_parent_draft_id",
        "takedown_drafts",
        "takedown_drafts",
        ["parent_draft_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_takedown_drafts_edited_by_user_id",
        "takedown_drafts",
        "users",
        ["edited_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_takedown_drafts_reviewed_by_user_id",
        "takedown_drafts",
        "users",
        ["reviewed_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "gemini_calls",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("operation", sa.String(length=50), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("is_incomplete", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("request_json", sa.JSON(), nullable=True),
        sa.Column("response_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gemini_calls_case", "gemini_calls", ["case_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_gemini_calls_case", table_name="gemini_calls")
    op.drop_table("gemini_calls")

    op.drop_constraint("fk_takedown_drafts_reviewed_by_user_id", "takedown_drafts", type_="foreignkey")
    op.drop_constraint("fk_takedown_drafts_edited_by_user_id", "takedown_drafts", type_="foreignkey")
    op.drop_constraint("fk_takedown_drafts_parent_draft_id", "takedown_drafts", type_="foreignkey")
    op.drop_column("takedown_drafts", "reviewed_at")
    op.drop_column("takedown_drafts", "is_reviewed")
    op.drop_column("takedown_drafts", "reviewed_by_user_id")
    op.drop_column("takedown_drafts", "edited_by_user_id")
    op.drop_column("takedown_drafts", "parent_draft_id")
    op.drop_column("takedown_drafts", "draft_kind")

    op.drop_column("cases", "gemini_generated_at")
    op.drop_column("cases", "gemini_last_attempted_at")
    op.drop_column("cases", "gemini_is_fallback")
    op.drop_column("cases", "gemini_is_incomplete")
    op.drop_column("cases", "gemini_incomplete_reason")
    op.drop_column("cases", "gemini_error")
    op.drop_column("cases", "gemini_provider")
    op.drop_column("cases", "gemini_model")
    op.drop_column("cases", "gemini_rationale")
    op.drop_column("cases", "gemini_status")
