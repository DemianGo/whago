"""add subscription fields to users

Revision ID: 013_add_subscription_fields
Revises: 012_create_api_keys
Create Date: 2025-11-13 20:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "013_add_subscription_fields"
down_revision = "012_create_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adicionar campos de assinatura à tabela users
    op.add_column("users", sa.Column("subscription_id", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("subscription_status", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("subscription_gateway", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("subscription_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("subscription_cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("next_billing_date", sa.DateTime(timezone=True), nullable=True))
    
    # Criar índice para subscription_id (para consultas rápidas)
    op.create_index("ix_users_subscription_id", "users", ["subscription_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_subscription_id", table_name="users")
    op.drop_column("users", "next_billing_date")
    op.drop_column("users", "subscription_cancelled_at")
    op.drop_column("users", "subscription_started_at")
    op.drop_column("users", "subscription_gateway")
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "subscription_id")

