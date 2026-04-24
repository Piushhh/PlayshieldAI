"""add gemini fields to asset

Revision ID: d4f1295473d
Revises: 8c17b1f3f2a1
Create Date: 2026-04-24 07:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "d4f1295473d"
down_revision: Union[str, None] = "8c17b1f3f2a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("assets", sa.Column("gemini_status", sa.String(length=50), nullable=True))
    op.add_column("assets", sa.Column("gemini_rationale", sa.Text(), nullable=True))

def downgrade() -> None:
    op.drop_column("assets", "gemini_rationale")
    op.drop_column("assets", "gemini_status")
