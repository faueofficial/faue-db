"""waitlist gender

Revision ID: 0010_waitlist_gender
Revises: 0009_waitlist_entries
Create Date: 2026-10-12

Adds `gender` to waitlist entries: 'female', 'male' or 'prefer_not_to_say', chosen from a dropdown on the
waitlist form. Used for one thing: choosing which model photograph sits behind the
person's Style DNA card. Nullable, because entries made before this column existed
have none and the API still accepts a request without it.

EXPAND-ONLY: a nullable column and a check that allows NULL. Safe to run before the
code that uses it and safe to leave in place if that code is rolled back.
"""

from alembic import op
import sqlalchemy as sa

revision = '0010_waitlist_gender'
down_revision = '0009_waitlist_entries'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('waitlist_entries', sa.Column('gender', sa.String(length=20), nullable=True), schema='gateway')
    op.create_check_constraint(
        op.f('ck_waitlist_entries_gender'), 'waitlist_entries',
        "gender IS NULL OR gender IN ('female', 'male', 'prefer_not_to_say')", schema='gateway',
    )


def downgrade() -> None:
    op.drop_constraint(op.f('ck_waitlist_entries_gender'), 'waitlist_entries', schema='gateway', type_='check')
    op.drop_column('waitlist_entries', 'gender', schema='gateway')
