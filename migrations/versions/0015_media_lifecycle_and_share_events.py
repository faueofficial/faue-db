"""asset tombstones and share events

Revision ID: 0015_media_lifecycle
Revises: 0014_shared_items
Create Date: 2026-10-14

`assets.purged_at` marks a tombstone whose images were removed. `share_events`
counts FAUE content being shared out, without recording who.

EXPAND-ONLY: one nullable column and one new table.
"""

from alembic import op
import sqlalchemy as sa

revision = '0015_media_lifecycle'
down_revision = '0014_shared_items'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('assets', sa.Column('purged_at', sa.DateTime(timezone=True), nullable=True), schema='gateway')
    op.create_table(
        'share_events',
        sa.Column('kind', sa.Text(), nullable=False),
        sa.Column('surface', sa.Text(), nullable=False),
        sa.Column('persona', sa.String(length=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_share_events')),
        schema='gateway',
    )
    op.create_index('ix_share_events_created', 'share_events', ['created_at'], unique=False, schema='gateway')


def downgrade() -> None:
    op.drop_index('ix_share_events_created', table_name='share_events', schema='gateway')
    op.drop_table('share_events', schema='gateway')
    op.drop_column('assets', 'purged_at', schema='gateway')
