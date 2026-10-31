"""admin: account notes and holds, reviewer profiles, content reviews

Revision ID: 0024_admin_actions
Revises: 0023_event_reminders
Create Date: 2026-10-17

EXPAND-ONLY: four new tables. Nothing is altered, so this can be deployed before the code that uses it.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0024_admin_actions'
down_revision = '0023_event_reminders'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'account_notes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('admin_id', sa.UUID(), nullable=False),
        sa.Column('kind', sa.String(length=8), nullable=False),
        sa.Column('body', sa.String(length=1000), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['gateway.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_account_notes')),
        sa.CheckConstraint("kind IN ('note', 'flag')", name=op.f('ck_account_notes_kind')),
        schema='gateway',
    )
    op.create_index('ix_account_notes_user', 'account_notes', ['user_id', 'created_at'], schema='gateway')
    op.create_index('ix_gateway_account_notes_workspace_id', 'account_notes', ['workspace_id'], schema='gateway')

    op.create_table(
        'account_holds',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('kind', sa.String(length=16), nullable=False),
        sa.Column('reason', sa.String(length=500), nullable=False),
        sa.Column('set_by', sa.UUID(), nullable=False),
        sa.Column('set_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('lifted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('lifted_by', sa.UUID(), nullable=True),
        sa.Column('lift_reason', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['gateway.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_account_holds')),
        sa.CheckConstraint(
            "kind IN ('suspended', 'ai_blocked', 'upload_blocked', 'community_muted')",
            name=op.f('ck_account_holds_kind')),
        schema='gateway',
    )
    op.create_index(
        'ix_account_holds_active', 'account_holds', ['user_id', 'kind'], schema='gateway',
        postgresql_where=sa.text('lifted_at IS NULL'))
    op.create_index('ix_gateway_account_holds_workspace_id', 'account_holds', ['workspace_id'], schema='gateway')

    op.create_table(
        'reviewer_profiles',
        sa.Column('admin_id', sa.UUID(), nullable=False),
        sa.Column('display_name', sa.String(length=80), nullable=False),
        sa.Column('traditions', postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column('regions', postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column('languages', postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column('bio', sa.String(length=500), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['admin_id'], ['gateway.admin_users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('admin_id', name=op.f('pk_reviewer_profiles')),
        schema='gateway',
    )

    op.create_table(
        'content_reviews',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('content_kind', sa.String(length=16), nullable=False),
        sa.Column('content_id', sa.String(length=120), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('tradition', sa.String(length=40), nullable=True),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('submitted_by', sa.UUID(), nullable=True),
        sa.Column('assigned_to', sa.UUID(), nullable=True),
        sa.Column('decided_by', sa.UUID(), nullable=True),
        sa.Column('decision_note', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_content_reviews')),
        sa.CheckConstraint(
            "content_kind IN ('style_card', 'rule', 'archetype', 'garment', 'fabric')",
            name=op.f('ck_content_reviews_kind')),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'changes_requested', 'rejected')",
            name=op.f('ck_content_reviews_status')),
        sa.UniqueConstraint('content_kind', 'content_id', 'content_hash', name='uq_content_review_version'),
        schema='gateway',
    )
    op.create_index('ix_content_reviews_queue', 'content_reviews', ['status', 'tradition'], schema='gateway')


def downgrade() -> None:
    op.drop_table('content_reviews', schema='gateway')
    op.drop_table('reviewer_profiles', schema='gateway')
    op.drop_table('account_holds', schema='gateway')
    op.drop_table('account_notes', schema='gateway')
