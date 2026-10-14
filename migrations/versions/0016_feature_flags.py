"""feature flags

Revision ID: 0016_feature_flags
Revises: 0015_media_lifecycle
Create Date: 2026-10-14

Operator-controlled switches. EXPAND-ONLY: one new table.
"""

from alembic import op
import sqlalchemy as sa

revision = '0016_feature_flags'
down_revision = '0015_media_lifecycle'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'feature_flags',
        sa.Column('key', sa.Text(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('key', name=op.f('pk_feature_flags')),
        schema='gateway',
    )


def downgrade() -> None:
    op.drop_table('feature_flags', schema='gateway')
