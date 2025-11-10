"""create webhooks tables

Revision ID: 010_create_webhooks_tables
Revises: 009_create_audit_logs_table
Create Date: 2025-11-10 02:20:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "010_create_webhooks_tables"
down_revision: str | None = "009_create_audit_logs_table"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS webhook_subscriptions (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            url VARCHAR(500) NOT NULL,
            secret VARCHAR(255),
            events JSONB NOT NULL DEFAULT '[]'::jsonb,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_delivery_at TIMESTAMPTZ,
            failure_count INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_webhook_subscriptions_user_active
        ON webhook_subscriptions(user_id, is_active);
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS webhook_delivery_logs (
            id UUID PRIMARY KEY,
            subscription_id UUID NOT NULL REFERENCES webhook_subscriptions(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            event VARCHAR(80) NOT NULL,
            url VARCHAR(500) NOT NULL,
            payload JSONB NOT NULL,
            status_code INTEGER,
            success BOOLEAN NOT NULL DEFAULT false,
            response_body TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_webhook_delivery_logs_user_created
        ON webhook_delivery_logs(user_id, created_at);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_webhook_delivery_logs_user_created;")
    op.execute("DROP TABLE IF EXISTS webhook_delivery_logs;")
    op.execute("DROP INDEX IF EXISTS ix_webhook_subscriptions_user_active;")
    op.execute("DROP TABLE IF EXISTS webhook_subscriptions;")


