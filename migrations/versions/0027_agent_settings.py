"""agent settings: how the daily suggestion behaves for one person

Revision ID: 0027_agent_settings
Revises: 0026_ase_job_plane
Create Date: 2026-10-30

EXPAND-ONLY: one new table. Nothing reads it until the gateway that ships with it is deployed.
"""

import sqlalchemy as sa
from alembic import op

revision = '0027_agent_settings'
down_revision = '0026_ase_job_plane'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'agent_settings',
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('daily_enabled', sa.Boolean(), nullable=False),
        sa.Column('daily_hour_local', sa.SmallInteger(), nullable=False),
        sa.Column('use_weather', sa.Boolean(), nullable=False),
        sa.Column('autonomy_level', sa.SmallInteger(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['gateway.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', name=op.f('pk_agent_settings')),
        sa.CheckConstraint('daily_hour_local BETWEEN 0 AND 23', name=op.f('ck_agent_settings_hour')),
        sa.CheckConstraint('autonomy_level BETWEEN 0 AND 3', name=op.f('ck_agent_settings_level')),
        schema='gateway',
    )
    op.create_index(op.f('ix_gateway_agent_settings_workspace_id'), 'agent_settings', ['workspace_id'], schema='gateway')


def downgrade() -> None:
    op.drop_index(op.f('ix_gateway_agent_settings_workspace_id'), table_name='agent_settings', schema='gateway')
    op.drop_table('agent_settings', schema='gateway')
