"""advanced billing structures

Revision ID: 007_advanced_billing
Revises: 006_add_billing_fields
Create Date: 2025-11-09 14:32:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "007_advanced_billing"
down_revision = "006_add_billing_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("default_payment_method", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("billing_customer_reference", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("billing_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column(
        "users",
        sa.Column("billing_suspension_started_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column("transactions", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("transactions", sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"))

    op.execute("DROP TABLE IF EXISTS payment_attempts CASCADE")
    op.execute("DROP TABLE IF EXISTS invoices CASCADE")
    op.execute("DROP TYPE IF EXISTS invoice_status")
    op.execute("DROP TYPE IF EXISTS payment_attempt_status")

    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("number", sa.String(length=50), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "paid", "cancelled", name="invoice_status"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("pdf_url", sa.String(length=255), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("number"),
        sa.UniqueConstraint("transaction_id"),
    )

    op.create_table(
        "payment_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("success", "failed", name="payment_attempt_status"),
            nullable=False,
        ),
        sa.Column("response_code", sa.String(length=50), nullable=True),
        sa.Column("failure_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_id", "attempt_number", name="uq_payment_attempt_transaction"),
    )

    op.alter_column("transactions", "attempt_count", server_default=None)


def downgrade() -> None:
    op.drop_table("payment_attempts")
    op.drop_table("invoices")

    op.drop_column("transactions", "attempt_count")
    op.drop_column("transactions", "due_at")

    op.drop_column("users", "billing_suspension_started_at")
    op.drop_column("users", "billing_metadata")
    op.drop_column("users", "billing_customer_reference")
    op.drop_column("users", "default_payment_method")

    op.execute("DROP TYPE IF EXISTS invoice_status")
    op.execute("DROP TYPE IF EXISTS payment_attempt_status")


