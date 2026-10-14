"""imported pins

Revision ID: 0011_imported_pins
Revises: 0010_waitlist_gender
Create Date: 2026-10-13

Pins a user chose to import from a connected account (Pinterest). One new table,
no change to any existing one.

EXPAND-ONLY: safe to run before the code that uses it and safe to leave in place
if that code is rolled back. Default privileges from `0007` already grant the
service role access.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0011_imported_pins'
down_revision = '0010_waitlist_gender'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'imported_pins',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.Text(), nullable=False),
        sa.Column('board_id', sa.Text(), nullable=False),
        sa.Column('board_name', sa.Text(), nullable=False),
        sa.Column('pin_id', sa.Text(), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.Column('asset_id', sa.UUID(), nullable=True),
        sa.Column('image_status', sa.Text(), nullable=False),
        sa.Column('imported_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['gateway.assets.id'], name=op.f('fk_imported_pins_asset_id'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['gateway.users.id'], name=op.f('fk_imported_pins_user_id'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_imported_pins')),
        sa.UniqueConstraint('user_id', 'provider', 'pin_id', name=op.f('uq_imported_pins_user_id')),
        schema='gateway',
    )
    op.create_index(op.f('ix_gateway_imported_pins_workspace_id'), 'imported_pins', ['workspace_id'], unique=False, schema='gateway')
    op.create_index('ix_imported_pins_user_board', 'imported_pins', ['user_id', 'board_id'], unique=False, schema='gateway')


def downgrade() -> None:
    op.drop_index(op.f('ix_gateway_imported_pins_workspace_id'), table_name='imported_pins', schema='gateway')
    op.drop_index('ix_imported_pins_user_board', table_name='imported_pins', schema='gateway')
    op.drop_table('imported_pins')
