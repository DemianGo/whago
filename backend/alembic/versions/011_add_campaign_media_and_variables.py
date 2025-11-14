"""Add campaign media table

Revision ID: 011_add_campaign_media
Revises: 010_create_webhooks_tables
Create Date: 2025-11-10 22:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "011_add_campaign_media"
down_revision = "010_create_webhooks_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campaign_media",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("stored_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            name="fk_campaign_media_campaign_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_campaign_media_campaign_id",
        "campaign_media",
        ["campaign_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_campaign_media_campaign_id", table_name="campaign_media")
    op.drop_table("campaign_media")
