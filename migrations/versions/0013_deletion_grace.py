"""deletion waiting period

Revision ID: 0013_deletion_grace
Revises: 0012_privacy_requests
Create Date: 2026-10-14

A deletion request now waits before the data is removed, so one made by mistake
can be undone. `purge_after` is when removal happens; `cancelled_at` records a
request that was taken back.

EXPAND-ONLY: two nullable columns.
"""

from alembic import op
import sqlalchemy as sa

revision = '0013_deletion_grace'
down_revision = '0012_privacy_requests'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('deletion_ledger', sa.Column('purge_after', sa.DateTime(timezone=True), nullable=True), schema='gateway')
    op.add_column('deletion_ledger', sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True), schema='gateway')


def downgrade() -> None:
    op.drop_column('deletion_ledger', 'cancelled_at', schema='gateway')
    op.drop_column('deletion_ledger', 'purge_after', schema='gateway')
