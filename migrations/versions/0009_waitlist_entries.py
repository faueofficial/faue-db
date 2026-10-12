"""waitlist entries

Revision ID: 0009_waitlist_entries
Revises: 0008_contact_messages
Create Date: 2026-10-12

People who took the Style DNA quiz on the website and asked to be told when FAUE
opens. One new table, no change to any existing one.

EXPAND-ONLY: safe to run before the code that uses it and safe to leave in place
if that code is rolled back.

`email_bidx` and `username_key` are unique, so a repeat submission and a handle
collision are both decided by the database rather than by a check-then-insert
race. Default privileges from `0007` already grant the service role access.
"""

from alembic import op
import sqlalchemy as sa
# autogenerate emits these types without importing them
import pgvector.sqlalchemy
import faue_db.types
from sqlalchemy.dialects import postgresql

revision = '0009_waitlist_entries'
down_revision = '0008_contact_messages'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('waitlist_entries',
    sa.Column('email_enc', faue_db.types.EncryptedStr(), nullable=False),
    sa.Column('email_bidx', faue_db.types.BlindIndex(length=64), nullable=False),
    sa.Column('username', sa.String(length=24), nullable=False),
    sa.Column('username_key', sa.String(length=24), nullable=False),
    sa.Column('dna_quiz_version', sa.Text(), nullable=False),
    sa.Column('dna_answers', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('dna_scores', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('dna_dominant', sa.Text(), nullable=False),
    sa.Column('dna_alter_ego', sa.Text(), nullable=True),
    sa.Column('dna_wildcard', sa.Text(), nullable=True),
    sa.Column('status', sa.Text(), server_default='waiting', nullable=False),
    sa.Column('source', sa.Text(), server_default='web_quiz', nullable=False),
    sa.Column('policy_version', sa.Text(), nullable=False),
    sa.Column('consented_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('ip_bidx', faue_db.types.BlindIndex(length=64), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('welcomed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('invited_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('unsubscribed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint("status IN ('waiting', 'invited', 'joined', 'unsubscribed')", name=op.f('ck_waitlist_entries_status')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_waitlist_entries')),
    sa.UniqueConstraint('email_bidx', name=op.f('uq_waitlist_entries_email_bidx')),
    sa.UniqueConstraint('username_key', name=op.f('uq_waitlist_entries_username_key')),
    schema='gateway'
    )
    op.create_index(op.f('ix_gateway_waitlist_entries_created_at'), 'waitlist_entries', ['created_at'], unique=False, schema='gateway')
    op.create_index(op.f('ix_gateway_waitlist_entries_dna_dominant'), 'waitlist_entries', ['dna_dominant'], unique=False, schema='gateway')


def downgrade() -> None:
    op.drop_index(op.f('ix_gateway_waitlist_entries_dna_dominant'), table_name='waitlist_entries', schema='gateway')
    op.drop_index(op.f('ix_gateway_waitlist_entries_created_at'), table_name='waitlist_entries', schema='gateway')
    op.drop_table('waitlist_entries', schema='gateway')
