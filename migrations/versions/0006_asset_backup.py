"""asset backup replication

Revision ID: 0006_asset_backup
Revises: 0005_assets
Create Date: 2026-09-02 17:05:28.388301

EXPAND-ONLY. This migration must be safe to run BEFORE the code that needs it,
and safe to leave in place if that code is rolled back. Additive columns are
nullable or defaulted; drops and tightening belong in a LATER release.
"""

from alembic import op
import sqlalchemy as sa
# autogenerate emits these types without importing them
import pgvector.sqlalchemy
import faue_db.types


revision = '0006_asset_backup'
down_revision = '0005_assets'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable, and null on every existing row. That is correct rather than a
    # shortcut: those assets genuinely are not on the backup yet, and the
    # reconciliation worker will find them exactly because this is null.
    op.add_column('assets', sa.Column('backed_up_at', sa.DateTime(timezone=True), nullable=True), schema='gateway')


def downgrade() -> None:
    op.drop_column('assets', 'backed_up_at', schema='gateway')
