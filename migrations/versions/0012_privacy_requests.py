"""restriction flag and data exports

Revision ID: 0012_privacy_requests
Revises: 0011_imported_pins
Create Date: 2026-10-14

`users.restricted_at` backs `POST /privacy/restrict`. `data_exports` holds the
archive a person asked for until it expires.

EXPAND-ONLY: one nullable column and one new table.
"""

from alembic import op
import sqlalchemy as sa

revision = '0012_privacy_requests'
down_revision = '0011_imported_pins'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('restricted_at', sa.DateTime(timezone=True), nullable=True), schema='gateway')
    op.create_table(
        'data_exports',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('payload', sa.LargeBinary(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('downloaded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['gateway.users.id'], name=op.f('fk_data_exports_user_id'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_data_exports')),
        schema='gateway',
    )
    op.create_index(op.f('ix_gateway_data_exports_workspace_id'), 'data_exports', ['workspace_id'], unique=False, schema='gateway')
    op.create_index('ix_data_exports_user', 'data_exports', ['user_id'], unique=False, schema='gateway')


def downgrade() -> None:
    op.drop_index('ix_data_exports_user', table_name='data_exports', schema='gateway')
    op.drop_index(op.f('ix_gateway_data_exports_workspace_id'), table_name='data_exports', schema='gateway')
    op.drop_table('data_exports', schema='gateway')
    op.drop_column('users', 'restricted_at', schema='gateway')
