"""cria tabelas de transações e ledger de créditos"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "003_transactions_credit"
down_revision = "002_add_user_tokens_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "CREATE TYPE transaction_type AS ENUM ('subscription', 'credit_purchase', 'adjustment'); "
            "EXCEPTION WHEN duplicate_object THEN NULL; "
            "END $$;"
        )
    )
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "CREATE TYPE transaction_status AS ENUM ('pending', 'completed', 'failed', 'cancelled'); "
            "EXCEPTION WHEN duplicate_object THEN NULL; "
            "END $$;"
        )
    )
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "CREATE TYPE credit_source AS ENUM ('welcome', 'purchase', 'adjustment', 'consumption', 'refund'); "
            "EXCEPTION WHEN duplicate_object THEN NULL; "
            "END $$;"
        )
    )

    op.create_table(
        "transactions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("plans.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "type",
            postgresql.ENUM(
                "subscription",
                "credit_purchase",
                "adjustment",
                name="transaction_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "completed",
                "failed",
                "cancelled",
                name="transaction_status",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("credits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payment_method", sa.String(length=50), nullable=True),
        sa.Column("reference_code", sa.String(length=100), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("reference_code", name="uq_transactions_reference_code"),
    )

    op.create_table(
        "credit_ledger",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "source",
            postgresql.ENUM(
                "welcome",
                "purchase",
                "adjustment",
                "consumption",
                "refund",
                name="credit_source",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("credit_ledger")
    op.drop_table("transactions")
    op.execute("DROP TYPE IF EXISTS credit_source")
    op.execute("DROP TYPE IF EXISTS transaction_status")
    op.execute("DROP TYPE IF EXISTS transaction_type")


