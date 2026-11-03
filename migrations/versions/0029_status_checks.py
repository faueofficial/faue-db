"""status checks: one row per probe of each part of the system, kept 90 days

Revision ID: 0029_status_checks
Revises: 0028_model_choices
Create Date: 2026-11-03

EXPAND-ONLY: one new table. The status_probe worker writes it and the admin console reads it; a gateway that predates it
never touches it, so either can deploy first.
"""

import sqlalchemy as sa
from alembic import op

revision = '0029_status_checks'
down_revision = '0028_model_choices'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'status_checks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('component', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('reason', sa.String(length=500), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('checked_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('up', 'degraded', 'down')", name=op.f('ck_status_checks_status_known')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_status_checks')),
        schema='gateway',
    )
    op.create_index('ix_status_checks_component_checked_at', 'status_checks', ['component', 'checked_at'], schema='gateway')
    op.create_index('ix_status_checks_checked_at', 'status_checks', ['checked_at'], schema='gateway')


def downgrade() -> None:
    op.drop_index('ix_status_checks_checked_at', table_name='status_checks', schema='gateway')
    op.drop_index('ix_status_checks_component_checked_at', table_name='status_checks', schema='gateway')
    op.drop_table('status_checks', schema='gateway')
