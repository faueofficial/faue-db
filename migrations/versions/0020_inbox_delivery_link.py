"""inbox items remember their delivery

Revision ID: 0020_inbox_delivery_link
Revises: 0019_runtime_settings
Create Date: 2026-10-15

Reading an inbox item is the one reliable "opened" signal FAUE has for a
message, and lifecycle campaigns back off from people who stop opening. The item
needs to say which delivery it was.

EXPAND-ONLY: two nullable columns.
"""

from alembic import op
import sqlalchemy as sa

revision = '0020_inbox_delivery_link'
down_revision = '0019_runtime_settings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('notify_inbox', sa.Column('template_id', sa.Text(), nullable=True), schema='gateway')
    op.add_column('notify_inbox', sa.Column('event_id', sa.UUID(), nullable=True), schema='gateway')


def downgrade() -> None:
    op.drop_column('notify_inbox', 'event_id', schema='gateway')
    op.drop_column('notify_inbox', 'template_id', schema='gateway')
