"""create proxy tables

Revision ID: 016_create_proxy_tables
Revises: 015_create_admin_tables
Create Date: 2025-11-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '016_create_proxy_tables'
down_revision = '015_create_admin_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tabela: proxy_providers
    op.create_table(
        'proxy_providers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), unique=True, nullable=False),
        sa.Column('provider_type', sa.String(50), nullable=False, comment='residential, datacenter, mobile'),
        sa.Column('credentials', postgresql.JSONB, nullable=False, comment='{"server": "...", "port": 3120, "username": "...", "password": "...", "api_key": "..."}'),
        sa.Column('cost_per_gb', sa.Numeric(10, 4), nullable=False, server_default='25.00'),
        sa.Column('region', sa.String(10), server_default='BR'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Tabela: proxies
    op.create_table(
        'proxies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('provider_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('proxy_providers.id', ondelete='CASCADE')),
        sa.Column('proxy_type', sa.String(50), nullable=False, comment='rotating, static'),
        sa.Column('proxy_url', sa.Text, nullable=False, comment='URL completa ou template com {session}'),
        sa.Column('region', sa.String(10), server_default='BR'),
        sa.Column('protocol', sa.String(20), server_default='http', comment='http, https, socks5'),
        sa.Column('health_score', sa.Integer, server_default='100'),
        sa.Column('total_bytes_used', sa.BigInteger, server_default='0'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('last_health_check', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Tabela: chip_proxy_assignments
    op.create_table(
        'chip_proxy_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('chip_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chips.id', ondelete='CASCADE'), unique=True),
        sa.Column('proxy_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('proxies.id', ondelete='SET NULL')),
        sa.Column('session_identifier', sa.String(255), comment='Usado em sticky session para IP fixo'),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('released_at', sa.DateTime(timezone=True)),
    )

    # Tabela: proxy_usage_logs
    op.create_table(
        'proxy_usage_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE')),
        sa.Column('chip_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chips.id', ondelete='SET NULL')),
        sa.Column('proxy_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('proxies.id', ondelete='SET NULL')),
        sa.Column('bytes_sent', sa.BigInteger, server_default='0'),
        sa.Column('bytes_received', sa.BigInteger, server_default='0'),
        sa.Column('total_bytes', sa.BigInteger, server_default='0'),
        sa.Column('cost', sa.Numeric(10, 4), server_default='0'),
        sa.Column('session_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('session_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Índice para otimizar consultas de uso mensal
    op.create_index(
        'idx_proxy_usage_user_month',
        'proxy_usage_logs',
        ['user_id', 'session_start']
    )

    # Tabela: user_proxy_costs (agregação mensal)
    op.create_table(
        'user_proxy_costs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE')),
        sa.Column('month', sa.Date, nullable=False),
        sa.Column('total_bytes', sa.BigInteger, server_default='0'),
        sa.Column('total_cost', sa.Numeric(10, 4), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('user_id', 'month', name='uq_user_proxy_costs_user_month'),
    )

    # Adicionar campo proxy_gb_limit na tabela plans
    op.add_column('plans', sa.Column('proxy_gb_limit', sa.Numeric(10, 2), server_default='0.1', comment='GB/mês permitido'))


def downgrade() -> None:
    op.drop_column('plans', 'proxy_gb_limit')
    op.drop_table('user_proxy_costs')
    op.drop_index('idx_proxy_usage_user_month', 'proxy_usage_logs')
    op.drop_table('proxy_usage_logs')
    op.drop_table('chip_proxy_assignments')
    op.drop_table('proxies')
    op.drop_table('proxy_providers')

