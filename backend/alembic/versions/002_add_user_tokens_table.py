"""adiciona tabela user_tokens"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "002_add_user_tokens_table"
down_revision = "001_create_users_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "CREATE TYPE token_type AS ENUM ('refresh', 'reset_password'); "
            "EXCEPTION WHEN duplicate_object THEN NULL; "
            "END $$;"
        )
    )

    op.create_table(
        "user_tokens",
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
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column(
            "token_type",
            postgresql.ENUM(
                "refresh",
                "reset_password",
                name="token_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.UniqueConstraint("token_hash", name="uq_user_tokens_token_hash"),
    )


def downgrade() -> None:
    op.drop_table("user_tokens")
    op.execute("DROP TYPE IF EXISTS token_type")


