"""create payment gateway configs table

Revision ID: 014_create_payment_gateway_configs
Revises: 013_add_subscription_fields
Create Date: 2025-11-14 00:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '014_payment_gateways'
down_revision: Union[str, None] = '013_add_subscription_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create payment_gateway_configs table
    op.create_table(
        'payment_gateway_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('gateway', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active_mode_production', sa.Boolean(), nullable=False, server_default='false'),
        
        # Sandbox credentials
        sa.Column('sandbox_access_token', sa.Text(), nullable=True),
        sa.Column('sandbox_public_key', sa.String(255), nullable=True),
        sa.Column('sandbox_client_id', sa.String(255), nullable=True),
        sa.Column('sandbox_client_secret', sa.Text(), nullable=True),
        sa.Column('sandbox_webhook_secret', sa.Text(), nullable=True),
        
        # Production credentials
        sa.Column('production_access_token', sa.Text(), nullable=True),
        sa.Column('production_public_key', sa.String(255), nullable=True),
        sa.Column('production_client_id', sa.String(255), nullable=True),
        sa.Column('production_client_secret', sa.Text(), nullable=True),
        sa.Column('production_webhook_secret', sa.Text(), nullable=True),
        
        # Additional config
        sa.Column('extra_config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    
    # Insert default configurations
    op.execute("""
        INSERT INTO payment_gateway_configs (id, gateway, name, is_enabled, is_active_mode_production, 
                                             sandbox_access_token, sandbox_public_key, sandbox_webhook_secret,
                                             description)
        VALUES 
        (
            gen_random_uuid(),
            'mercadopago',
            'Mercado Pago',
            true,
            false,
            'TEST-6266967508496749-102011-9d5e58c0bd298f8ef2dc5210014a9245-2937021508',
            'TEST-1007ffce-416a-49cc-8888-ded9dd8cf368',
            'mercadopago-webhook-secret',
            'Gateway de pagamento Mercado Pago - Configurado em modo sandbox'
        ),
        (
            gen_random_uuid(),
            'paypal',
            'PayPal',
            false,
            false,
            NULL,
            NULL,
            NULL,
            'Gateway de pagamento PayPal - Aguardando configuração'
        ),
        (
            gen_random_uuid(),
            'stripe',
            'Stripe',
            false,
            false,
            NULL,
            NULL,
            NULL,
            'Gateway de pagamento Stripe - Aguardando configuração'
        )
    """)


def downgrade() -> None:
    op.drop_table('payment_gateway_configs')

