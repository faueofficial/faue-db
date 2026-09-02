"""notify delivery uniqueness includes channel

Revision ID: 0003_notify_channel_key
Revises: 0002_revoked_reason
Create Date: 2026-08-23 00:44:00.000000

The old key was (user_id, template_id, event_id), which reads as correct
deduplication and is not. One row *is* one channel, so without `channel` in the
key the first channel to claim an event locks out every other: a message meant
for the inbox and email only ever reached whichever ran first, and the second
was recorded as a duplicate.

EXPAND-ONLY in effect: the new constraint is strictly weaker than the old one,
so every row that satisfied the old key satisfies the new one. Code written
against the old key keeps working — it simply could not use the second channel.
"""

from alembic import op
import sqlalchemy as sa
# autogenerate emits these types without importing them
import pgvector.sqlalchemy
import faue_db.types


revision = '0003_notify_channel_key'
down_revision = '0002_revoked_reason'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        'uq_notify_deliveries_user_id',
        'notify_deliveries',
        schema='gateway',
        type_='unique',
    )
    op.create_unique_constraint(
        'uq_notify_deliveries_user_id',
        'notify_deliveries',
        ['user_id', 'template_id', 'event_id', 'channel'],
        schema='gateway',
    )


def downgrade() -> None:
    """Reversing this can fail, and that is honest rather than a defect.

    Once multi-channel delivery has run, rows exist that share
    (user_id, template_id, event_id) and differ only by channel. The old,
    stricter constraint cannot be recreated over them without deleting real
    delivery records, and this migration will not do that silently.
    """
    op.drop_constraint(
        'uq_notify_deliveries_user_id',
        'notify_deliveries',
        schema='gateway',
        type_='unique',
    )
    op.create_unique_constraint(
        'uq_notify_deliveries_user_id',
        'notify_deliveries',
        ['user_id', 'template_id', 'event_id'],
        schema='gateway',
    )
