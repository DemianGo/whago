"""criação inicial de planos e usuários"""

from __future__ import annotations

from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_create_users_table"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column(
            "tier",
            sa.Enum("FREE", "BUSINESS", "ENTERPRISE", name="plan_tier", native_enum=False),
            nullable=False,
        ),
        sa.Column("price", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("max_chips", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("monthly_messages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "features",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
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
        sa.UniqueConstraint("name", name="uq_plans_name"),
        sa.UniqueConstraint("slug", name="uq_plans_slug"),
    )

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
        nullable=False,
        primary_key=True,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("company_name", sa.String(length=150), nullable=True),
        sa.Column("document", sa.String(length=18), nullable=True),
        sa.Column("credits", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_suspended", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("plans.id", ondelete="SET NULL"), nullable=True),
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
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.Index("ix_users_email", "email"),
    )

    plans_table = sa.table(
        "plans",
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("tier", sa.String()),
        sa.column("price", sa.Numeric()),
        sa.column("max_chips", sa.Integer()),
        sa.column("monthly_messages", sa.Integer()),
        sa.column("features", postgresql.JSONB()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    now = datetime.utcnow()
    op.bulk_insert(
        plans_table,
        [
            {
                "name": "Plano Free",
                "slug": "free",
                "tier": "FREE",
                "price": 0,
                "max_chips": 1,
                "monthly_messages": 500,
                "features": {
                    "campaigns_active": 1,
                    "contacts_per_list": 100,
                    "support": "Sem suporte prioritário",
                    "data_retention_days": 30,
                    "min_interval_seconds": 10,
                    "scheduling": False,
                    "api_access": False,
                    "chip_maturation": False,
                    "chip_rotation": False,
                },
                "created_at": now,
                "updated_at": now,
            },
            {
                "name": "Plano Business",
                "slug": "business",
                "tier": "BUSINESS",
                "price": 97,
                "max_chips": 3,
                "monthly_messages": 5000,
                "features": {
                    "campaigns_active": "Ilimitadas",
                    "contacts_per_list": 10000,
                    "support": "Email prioritário (24h)",
                    "data_retention_days": 90,
                    "min_interval_seconds": 5,
                    "scheduling": True,
                    "advanced_stats": True,
                    "report_export": True,
                    "api_access": False,
                    "chip_maturation": True,
                    "chip_rotation": True,
                },
                "created_at": now,
                "updated_at": now,
            },
            {
                "name": "Plano Enterprise",
                "slug": "enterprise",
                "tier": "ENTERPRISE",
                "price": 297,
                "max_chips": 10,
                "monthly_messages": 20000,
                "features": {
                    "campaigns_active": "Ilimitadas",
                    "contacts_per_list": "Ilimitados",
                    "support": "Prioritário (2h)",
                    "data_retention_days": -1,
                    "min_interval_seconds": 3,
                    "scheduling": True,
                    "advanced_stats": True,
                    "report_export": "Personalizados",
                    "api_access": True,
                    "chip_maturation": "Com IA",
                    "chip_rotation": "Inteligente",
                    "multi_user": 5,
                    "webhooks": True,
                },
                "created_at": now,
                "updated_at": now,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("users")
    op.drop_table("plans")
    op.execute("DROP TYPE IF EXISTS plan_tier")


