"""community posts

Revision ID: 0021_community
Revises: 0020_inbox_delivery_link
Create Date: 2026-10-14

Looks people chose to show to others, with likes, copies and reports.
EXPAND-ONLY: four new tables.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0021_community'
down_revision = '0020_inbox_delivery_link'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'community_posts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('look_id', sa.Text(), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('image_url', sa.Text(), nullable=False),
        sa.Column('occasion', sa.Text(), nullable=True),
        sa.Column('caption', sa.String(length=140), nullable=True),
        sa.Column('persona', sa.String(length=8), nullable=True),
        sa.Column('recipe', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('likes_count', sa.Integer(), nullable=False),
        sa.Column('copies_count', sa.Integer(), nullable=False),
        sa.Column('reports_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['gateway.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_community_posts')),
        sa.UniqueConstraint('user_id', 'look_id', name=op.f('uq_community_posts_user_id')),
        schema='gateway',
    )
    op.create_index('ix_community_posts_feed', 'community_posts', ['status', 'persona', 'created_at'], schema='gateway')
    for name in ('community_likes', 'community_copies'):
        op.create_table(
            name,
            sa.Column('workspace_id', sa.UUID(), nullable=False),
            sa.Column('post_id', sa.UUID(), nullable=False),
            sa.Column('user_id', sa.UUID(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['post_id'], ['gateway.community_posts.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['gateway.users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('post_id', 'user_id', name=op.f(f'pk_{name}')),
            schema='gateway',
        )
    op.create_table(
        'community_reports',
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('post_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['gateway.community_posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['gateway.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('post_id', 'user_id', name=op.f('pk_community_reports')),
        schema='gateway',
    )


def downgrade() -> None:
    op.drop_table('community_reports', schema='gateway')
    op.drop_table('community_copies', schema='gateway')
    op.drop_table('community_likes', schema='gateway')
    op.drop_index('ix_community_posts_feed', table_name='community_posts', schema='gateway')
    op.drop_table('community_posts', schema='gateway')
