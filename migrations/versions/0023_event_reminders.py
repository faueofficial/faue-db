"""events: several reminders per event

Revision ID: 0023_event_reminders
Revises: 0022_studio
Create Date: 2026-10-15

EXPAND-ONLY: two JSONB columns. `remind` stays and is kept in step by the gateway.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0023_event_reminders'
down_revision = '0022_studio'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('user_events', sa.Column('reminders', postgresql.JSONB(), server_default='[]', nullable=False), schema='gateway')
    op.add_column('user_events', sa.Column('reminded', postgresql.JSONB(), server_default='[]', nullable=False), schema='gateway')
    op.execute("UPDATE gateway.user_events SET reminders = jsonb_build_array(remind) WHERE remind <> 'none'")


def downgrade() -> None:
    op.drop_column('user_events', 'reminded', schema='gateway')
    op.drop_column('user_events', 'reminders', schema='gateway')
