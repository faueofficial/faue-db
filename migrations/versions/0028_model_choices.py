"""model choices: the models an admin chose for a tier or a task

Revision ID: 0028_model_choices
Revises: 0027_agent_settings
Create Date: 2026-10-31

EXPAND-ONLY: one new table. ase reads it if it is there and falls back to models.yaml if it is not, so either can deploy first.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0028_model_choices'
down_revision = '0027_agent_settings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'model_choices',
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('models', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('set_by', sa.UUID(), nullable=False),
        sa.Column('set_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('name', name=op.f('pk_model_choices')),
        schema='ase',
    )


def downgrade() -> None:
    op.drop_table('model_choices', schema='ase')
