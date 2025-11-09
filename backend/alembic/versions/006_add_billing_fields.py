"""add billing fields to users

Revision ID: 006_add_billing_fields
Revises: 005_create_campaigns_tables
Create Date: 2025-11-09 12:25:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "006_add_billing_fields"
down_revision = "005_campaigns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "subscription_renewal_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column("pending_plan_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "failed_payment_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_foreign_key(
        "fk_users_pending_plan_id_plans",
        "users",
        "plans",
        ["pending_plan_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column(
        "users",
        "failed_payment_attempts",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_pending_plan_id_plans", "users", type_="foreignkey")
    op.drop_column("users", "failed_payment_attempts")
    op.drop_column("users", "pending_plan_id")
    op.drop_column("users", "subscription_renewal_at")


