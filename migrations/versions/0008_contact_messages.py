"""contact messages

Revision ID: 0008_contact_messages
Revises: 0007_default_grants
Create Date: 2026-10-09 17:49:55.634730

Website enquiries (contact and partners forms). One new table, no change to any
existing one.

EXPAND-ONLY: safe to run before the code that uses it and safe to leave in place
if that code is rolled back.

Personal columns are `_enc` / `_bidx` and nullable on purpose: the purge job
sets them to NULL 72 hours after `created_at`. The row itself stays, holding only
a reference, topic, status and dates. Default privileges from `0007` already
grant the service role access, so no GRANT is needed here.
"""

from alembic import op
import sqlalchemy as sa
# autogenerate emits these types without importing them
import pgvector.sqlalchemy
import faue_db.types


revision = '0008_contact_messages'
down_revision = '0007_default_grants'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('contact_messages',
    sa.Column('reference', sa.Text(), nullable=False),
    sa.Column('topic', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), server_default='new', nullable=False),
    sa.Column('name_enc', faue_db.types.EncryptedStr(), nullable=True),
    sa.Column('email_enc', faue_db.types.EncryptedStr(), nullable=True),
    sa.Column('email_bidx', faue_db.types.BlindIndex(length=64), nullable=True),
    sa.Column('message_enc', faue_db.types.EncryptedStr(), nullable=True),
    sa.Column('organisation_enc', faue_db.types.EncryptedStr(), nullable=True),
    sa.Column('role_enc', faue_db.types.EncryptedStr(), nullable=True),
    sa.Column('ip_bidx', faue_db.types.BlindIndex(length=64), nullable=True),
    sa.Column('partner_type', sa.Text(), nullable=True),
    sa.Column('reference_code', sa.Text(), nullable=True),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('policy_version', sa.Text(), nullable=False),
    sa.Column('idempotency_key', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('notified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('replied_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('handled_by', sa.UUID(), nullable=True),
    sa.Column('purged_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint("partner_type IS NULL OR partner_type IN ('tailor', 'designer', 'fabric_seller', 'event_planner', 'stylist_creator', 'media', 'other')", name=op.f('ck_contact_messages_partner_type')),
    sa.CheckConstraint("status IN ('new', 'replied', 'closed')", name=op.f('ck_contact_messages_status')),
    sa.CheckConstraint("topic IN ('support', 'data_request', 'press_partnership', 'other')", name=op.f('ck_contact_messages_topic')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_contact_messages')),
    sa.UniqueConstraint('idempotency_key', name=op.f('uq_contact_messages_idempotency_key')),
    sa.UniqueConstraint('reference', name=op.f('uq_contact_messages_reference')),
    schema='gateway'
    )
    op.create_index('ix_contact_messages_unpurged', 'contact_messages', ['created_at'], unique=False, schema='gateway', postgresql_where=sa.text('purged_at IS NULL'))
    op.create_index(op.f('ix_gateway_contact_messages_email_bidx'), 'contact_messages', ['email_bidx'], unique=False, schema='gateway')


def downgrade() -> None:
    op.drop_index(op.f('ix_gateway_contact_messages_email_bidx'), table_name='contact_messages', schema='gateway')
    op.drop_index('ix_contact_messages_unpurged', table_name='contact_messages', schema='gateway', postgresql_where=sa.text('purged_at IS NULL'))
    op.drop_table('contact_messages', schema='gateway')
