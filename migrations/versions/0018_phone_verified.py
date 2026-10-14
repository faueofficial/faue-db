"""phone verification flag

Revision ID: 0018_phone_verified
Revises: 0017_audit_retention
Create Date: 2026-10-14

SMS and WhatsApp send only to a number the person proved they hold.
EXPAND-ONLY: one column with a default.
"""

from alembic import op
import sqlalchemy as sa

revision = '0018_phone_verified'
down_revision = '0017_audit_retention'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'auth_identities',
        sa.Column('phone_verified', sa.Boolean(), server_default=sa.false(), nullable=False),
        schema='gateway',
    )


def downgrade() -> None:
    op.drop_column('auth_identities', 'phone_verified', schema='gateway')
