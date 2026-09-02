"""assets — uploaded images after the PII pipeline

Revision ID: 0005_assets
Revises: 0004_admin_totp
Create Date: 2026-09-02 15:37:41.963789

EXPAND-ONLY. This migration must be safe to run BEFORE the code that needs it,
and safe to leave in place if that code is rolled back. Additive columns are
nullable or defaulted; drops and tightening belong in a LATER release.
"""

from alembic import op
import sqlalchemy as sa
# autogenerate emits these types without importing them
import pgvector.sqlalchemy
import faue_db.types


revision = '0005_assets'
down_revision = '0004_admin_totp'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('assets',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('rejection_reason', sa.Text(), nullable=True),
    sa.Column('storage_key', sa.Text(), nullable=True),
    sa.Column('thumb_key', sa.Text(), nullable=True),
    sa.Column('preview_key', sa.Text(), nullable=True),
    sa.Column('content_type', sa.Text(), nullable=True),
    sa.Column('width', sa.Integer(), nullable=True),
    sa.Column('height', sa.Integer(), nullable=True),
    sa.Column('bytes', sa.Integer(), nullable=True),
    sa.Column('exif_stripped', sa.Boolean(), nullable=False),
    sa.Column('faces_redacted', sa.Boolean(), nullable=False),
    sa.Column('faces_found', sa.Integer(), nullable=False),
    sa.Column('ocr_redacted', sa.Boolean(), nullable=False),
    sa.Column('safety_verdict', sa.Text(), nullable=True),
    sa.Column('original_retained', sa.Boolean(), nullable=False),
    sa.Column('retention_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('workspace_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['gateway.users.id'], name=op.f('fk_assets_user_id'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_assets')),
    schema='gateway'
    )
    op.create_index(op.f('ix_gateway_assets_user_id'), 'assets', ['user_id'], unique=False, schema='gateway')
    op.create_index(op.f('ix_gateway_assets_workspace_id'), 'assets', ['workspace_id'], unique=False, schema='gateway')


def downgrade() -> None:
    op.drop_index(op.f('ix_gateway_assets_workspace_id'), table_name='assets', schema='gateway')
    op.drop_index(op.f('ix_gateway_assets_user_id'), table_name='assets', schema='gateway')
    op.drop_table('assets', schema='gateway')
