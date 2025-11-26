"""add_campaign_steps

Revision ID: f284b1a80e4c
Revises: e1753a979f3b
Create Date: 2025-11-26 13:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f284b1a80e4c'
down_revision = 'e1753a979f3b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('campaigns', sa.Column('steps', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('campaign_messages', sa.Column('current_step', sa.Integer(), nullable=True, server_default='0'))


def downgrade():
    op.drop_column('campaign_messages', 'current_step')
    op.drop_column('campaigns', 'steps')

