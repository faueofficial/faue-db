"""shared items

Revision ID: 0014_shared_items
Revises: 0013_deletion_grace
Create Date: 2026-10-14

Looks shared to FAUE from TikTok, Instagram or Pinterest, or as an image.

EXPAND-ONLY: one new table.
"""

from alembic import op
import sqlalchemy as sa

revision = '0014_shared_items'
down_revision = '0013_deletion_grace'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'shared_items',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('author_name', sa.Text(), nullable=True),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('asset_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['gateway.assets.id'], name=op.f('fk_shared_items_asset_id'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['gateway.users.id'], name=op.f('fk_shared_items_user_id'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_shared_items')),
        sa.UniqueConstraint('user_id', 'source_url', name=op.f('uq_shared_items_user_id')),
        schema='gateway',
    )
    op.create_index(op.f('ix_gateway_shared_items_workspace_id'), 'shared_items', ['workspace_id'], unique=False, schema='gateway')
    op.create_index('ix_shared_items_user_created', 'shared_items', ['user_id', 'created_at'], unique=False, schema='gateway')


def downgrade() -> None:
    op.drop_index('ix_shared_items_user_created', table_name='shared_items', schema='gateway')
    op.drop_index(op.f('ix_gateway_shared_items_workspace_id'), table_name='shared_items', schema='gateway')
    op.drop_table('shared_items', schema='gateway')
