"""admin totp secret

Revision ID: 0004_admin_totp
Revises: 0003_notify_channel_key
Create Date: 2026-09-02 13:52:34.185496

EXPAND-ONLY. This migration must be safe to run BEFORE the code that needs it,
and safe to leave in place if that code is rolled back. Additive columns are
nullable or defaulted; drops and tightening belong in a LATER release.
"""

from alembic import op
import sqlalchemy as sa
# autogenerate emits these types without importing them
import pgvector.sqlalchemy
import faue_db.types


revision = '0004_admin_totp'
down_revision = '0003_notify_channel_key'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Both nullable: existing admin rows have no secret and no enrolment date,
    # and an admin who has not enrolled must be able to reach the enrolment
    # endpoint rather than be locked out by a NOT NULL they cannot satisfy.
    op.add_column('admin_users', sa.Column('totp_secret_enc', faue_db.types.EncryptedStr(), nullable=True), schema='gateway')
    op.add_column('admin_users', sa.Column('mfa_enrolled_at', sa.DateTime(timezone=True), nullable=True), schema='gateway')


def downgrade() -> None:
    """Drops every enrolled secret. Reversing this means every admin re-enrols
    from a fresh QR code — recoverable, but not silent."""
    op.drop_column('admin_users', 'mfa_enrolled_at', schema='gateway')
    op.drop_column('admin_users', 'totp_secret_enc', schema='gateway')
