"""create_media_gallery_table

Revision ID: e1753a979f3b
Revises: 016_create_proxy_tables
Create Date: 2025-11-26 12:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1753a979f3b'
down_revision = '016_create_proxy_tables'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('media_gallery',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('stored_name', sa.String(length=255), nullable=False),
    sa.Column('content_type', sa.String(length=100), nullable=False),
    sa.Column('size_bytes', sa.BigInteger(), nullable=False),
    sa.Column('category', sa.String(length=50), nullable=True),
    sa.Column('tags', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_media_gallery_user_id'), 'media_gallery', ['user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_media_gallery_user_id'), table_name='media_gallery')
    op.drop_table('media_gallery')

