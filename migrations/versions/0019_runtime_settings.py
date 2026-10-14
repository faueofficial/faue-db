"""runtime settings

Revision ID: 0019_runtime_settings
Revises: 0018_phone_verified
Create Date: 2026-10-14

Non-secret values an operator can tune from the console. EXPAND-ONLY: one table.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0019_runtime_settings'
down_revision = '0018_phone_verified'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'runtime_settings',
        sa.Column('key', sa.Text(), nullable=False),
        sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('key', name=op.f('pk_runtime_settings')),
        schema='gateway',
    )


def downgrade() -> None:
    op.drop_table('runtime_settings', schema='gateway')
