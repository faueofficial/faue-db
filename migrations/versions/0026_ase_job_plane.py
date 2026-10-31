"""ase: job plane columns, memory events, kill switches, model-call source, approved-content view

Revision ID: 0026_ase_job_plane
Revises: 0025_workspace_indexes
Create Date: 2026-10-21

EXPAND-ONLY. Columns added to ase.look_jobs and ase.looks are nullable or carry a server default; two tables are new;
one view is new. Nothing is dropped or renamed, so this can ship before the code that uses it.

`ase.approved_content` is the one way ASE learns what a reviewer has signed off. It selects from gateway.content_reviews
(owned by the gateway) so ASE never reads the gateway schema directly and the exposure is a single read-only view: kind,
id, exact content hash and tradition of every APPROVED version, nothing else.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0026_ase_job_plane'
down_revision = '0025_workspace_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('look_jobs', sa.Column('kind', sa.Text(), server_default='generate', nullable=False), schema='ase')
    op.add_column('look_jobs', sa.Column('idempotency_key', sa.Text(), nullable=True), schema='ase')
    op.add_column('look_jobs', sa.Column('attempts', sa.SmallInteger(), server_default='0', nullable=False), schema='ase')
    op.add_column('look_jobs', sa.Column('counted', sa.Boolean(), server_default='false', nullable=False), schema='ase')
    op.add_column('look_jobs', sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True), schema='ase')
    op.add_column('look_jobs', sa.Column('provenance', postgresql.JSONB(astext_type=sa.Text()), nullable=True), schema='ase')
    # One job per (person, key): a retried request finds the first job instead of making another.
    op.create_index('uq_look_jobs_user_key', 'look_jobs', ['user_id', 'idempotency_key'], unique=True, schema='ase',
                    postgresql_where=sa.text('idempotency_key IS NOT NULL'))

    op.add_column('looks', sa.Column('parent_look_id', sa.UUID(), nullable=True), schema='ase')
    op.add_column('looks', sa.Column('mode', sa.Text(), nullable=True), schema='ase')
    op.add_column('looks', sa.Column('pack_hash', sa.Text(), nullable=True), schema='ase')
    op.add_column('looks', sa.Column('record', postgresql.JSONB(astext_type=sa.Text()), nullable=True), schema='ase')

    op.create_table(
        'memory_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('kind', sa.Text(), nullable=False),
        sa.Column('at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False),
        sa.Column('half_life', sa.Float(), nullable=False),
        sa.Column('look_id', sa.UUID(), nullable=True),
        sa.Column('item_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('colours', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('fabrics', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('occasion', sa.Text(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('exploration', sa.Boolean(), server_default='false', nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_memory_events')),
        schema='ase',
    )
    op.create_index('ix_ase_memory_events_user_id', 'memory_events', ['user_id'], schema='ase')
    op.create_index('ix_ase_memory_events_workspace_id', 'memory_events', ['workspace_id'], schema='ase')

    op.add_column('model_calls', sa.Column('source', sa.Text(), nullable=True), schema='ase')
    op.add_column('model_calls', sa.Column('reason', sa.Text(), nullable=True), schema='ase')

    op.create_table(
        'kill_switches',
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('disabled', sa.Boolean(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('set_by', sa.UUID(), nullable=False),
        sa.Column('set_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('name', name=op.f('pk_kill_switches')),
        schema='ase',
    )

    # A skill reference file (skills/<name>/references/...) is reviewable content too. Widening a CHECK is safe to ship first.
    op.drop_constraint(op.f('ck_content_reviews_kind'), 'content_reviews', schema='gateway', type_='check')
    op.create_check_constraint(
        op.f('ck_content_reviews_kind'), 'content_reviews',
        "content_kind IN ('style_card', 'rule', 'archetype', 'garment', 'fabric', 'reference')", schema='gateway')

    op.execute("""
        CREATE VIEW ase.approved_content AS
        SELECT content_kind, content_id, content_hash, tradition
        FROM gateway.content_reviews
        WHERE status = 'approved'
    """)
    # ase reads the view and nothing else of the gateway's. Default privileges cover new tables, but a view is explicit.
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'faue_ase') THEN
                GRANT SELECT ON ase.approved_content TO faue_ase;
            END IF;
        END $$
    """)


def downgrade() -> None:
    op.execute('DROP VIEW IF EXISTS ase.approved_content')
    op.execute("DELETE FROM gateway.content_reviews WHERE content_kind = 'reference'")
    op.drop_constraint(op.f('ck_content_reviews_kind'), 'content_reviews', schema='gateway', type_='check')
    op.create_check_constraint(
        op.f('ck_content_reviews_kind'), 'content_reviews',
        "content_kind IN ('style_card', 'rule', 'archetype', 'garment', 'fabric')", schema='gateway')
    op.drop_table('kill_switches', schema='ase')
    op.drop_column('model_calls', 'reason', schema='ase')
    op.drop_column('model_calls', 'source', schema='ase')
    op.drop_index('ix_ase_memory_events_workspace_id', table_name='memory_events', schema='ase')
    op.drop_index('ix_ase_memory_events_user_id', table_name='memory_events', schema='ase')
    op.drop_table('memory_events', schema='ase')
    for col in ('record', 'pack_hash', 'mode', 'parent_look_id'):
        op.drop_column('looks', col, schema='ase')
    op.drop_index('uq_look_jobs_user_key', table_name='look_jobs', schema='ase')
    for col in ('provenance', 'result', 'counted', 'attempts', 'idempotency_key', 'kind'):
        op.drop_column('look_jobs', col, schema='ase')
