"""studio: events, tailors, ase notes

Revision ID: 0022_studio
Revises: 0021_community
Create Date: 2026-10-15

EXPAND-ONLY: three new tables.
"""

from alembic import op
import sqlalchemy as sa
import faue_db.types

revision = '0022_studio'
down_revision = '0021_community'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'user_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=80), nullable=False),
        sa.Column('kind', sa.String(length=16), nullable=False),
        sa.Column('starts_on', sa.Date(), nullable=False),
        sa.Column('city', sa.String(length=60), nullable=True),
        sa.Column('has_fabric', sa.Boolean(), nullable=False),
        sa.Column('remind', sa.String(length=8), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['gateway.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_events')),
        sa.CheckConstraint("kind IN ('wedding','owambe','church','naming','work','travel','other')", name=op.f('ck_user_events_kind')),
        sa.CheckConstraint("remind IN ('none','1d','3d','7d')", name=op.f('ck_user_events_remind')),
        schema='gateway',
    )
    op.create_index('ix_user_events_user_day', 'user_events', ['user_id', 'starts_on'], schema='gateway')

    op.create_table(
        'tailors',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('phone_enc', faue_db.types.EncryptedStr(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['gateway.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_tailors')),
        schema='gateway',
    )
    op.create_index('ix_tailors_user', 'tailors', ['user_id'], schema='gateway')

    op.create_table(
        'ase_notes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('text', sa.String(length=300), nullable=False),
        sa.Column('source', sa.String(length=8), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['gateway.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ase_notes')),
        sa.CheckConstraint("source IN ('user','learned')", name=op.f('ck_ase_notes_source')),
        schema='gateway',
    )
    op.create_index('ix_ase_notes_user', 'ase_notes', ['user_id', 'created_at'], schema='gateway')


def downgrade() -> None:
    op.drop_table('ase_notes', schema='gateway')
    op.drop_table('tailors', schema='gateway')
    op.drop_table('user_events', schema='gateway')
