"""workspace_id indexes on the tables added in 0021 and 0022

Revision ID: 0025_workspace_indexes
Revises: 0024_admin_actions
Create Date: 2026-10-17

EXPAND-ONLY: seven indexes. The models declare `workspace_id` as indexed (the workspace mixin does), but the
migrations that created these tables did not, so `alembic check` reported drift. No data changes.
"""

from alembic import op

revision = '0025_workspace_indexes'
down_revision = '0024_admin_actions'
branch_labels = None
depends_on = None

TABLES = (
    'ase_notes', 'community_copies', 'community_likes', 'community_posts',
    'community_reports', 'tailors', 'user_events',
)


def upgrade() -> None:
    for table in TABLES:
        op.create_index(f'ix_gateway_{table}_workspace_id', table, ['workspace_id'], schema='gateway')


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_index(f'ix_gateway_{table}_workspace_id', table_name=table, schema='gateway')
