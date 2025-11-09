"""cria tabelas de chips e eventos"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "004_chips_events"
down_revision = "003_transactions_credit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "CREATE TYPE chip_status AS ENUM ('waiting_qr', 'connecting', 'connected', 'disconnected', 'maturing', 'banned', 'maintenance'); "
            "EXCEPTION WHEN duplicate_object THEN NULL; "
            "END $$;"
        )
    )
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "CREATE TYPE chip_event_type AS ENUM ('info', 'warning', 'error', 'status_change', 'message_sent', 'message_failed', 'system'); "
            "EXCEPTION WHEN duplicate_object THEN NULL; "
            "END $$;"
        )
    )

    op.create_table(
        "chips",
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
        sa.Column("alias", sa.String(length=100), nullable=False),
        sa.Column("session_id", sa.String(length=100), nullable=False),
        sa.Column("phone_number", sa.String(length=20), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "waiting_qr",
                "connecting",
                "connected",
                "disconnected",
                "maturing",
                "banned",
                "maintenance",
                name="chip_status",
                create_type=False,
            ),
            nullable=False,
            server_default="waiting_qr",
        ),
        sa.Column("health_score", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("alias", name="uq_chips_alias"),
        sa.UniqueConstraint("session_id", name="uq_chips_session_id"),
    )

    op.create_table(
        "chip_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "chip_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chips.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "type",
            postgresql.ENUM(
                "info",
                "warning",
                "error",
                "status_change",
                "message_sent",
                "message_failed",
                "system",
                name="chip_event_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("chip_events")
    op.drop_table("chips")
    op.execute("DROP TYPE IF EXISTS chip_event_type")
    op.execute("DROP TYPE IF EXISTS chip_status")


