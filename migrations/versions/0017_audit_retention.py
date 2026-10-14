"""audit log retention function

Revision ID: 0017_audit_retention
Revises: 0016_feature_flags
Create Date: 2026-10-14

The audit log is append-only for the service role (migration 0007 revokes
UPDATE and DELETE), which is what makes it evidence. Seven years later it has to
be deletable, so this adds exactly one way to delete from it: a function that
removes rows older than a floor it enforces itself.

SECURITY DEFINER, so it runs with the owner's rights and the service role still
holds no DELETE of its own. The floor is inside the function: a caller cannot
ask for `'1 day'`, and a bug in the application cannot shorten the period.

EXPAND-ONLY: one new function.
"""

from alembic import op

revision = '0017_audit_retention'
down_revision = '0016_feature_flags'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION gateway.purge_audit_log(keep interval DEFAULT interval '7 years')
        RETURNS bigint
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = gateway, pg_temp
        AS $$
        DECLARE
            removed bigint;
        BEGIN
            IF keep < interval '7 years' THEN
                RAISE EXCEPTION 'audit log must be kept for at least 7 years (asked for %)', keep;
            END IF;
            WITH gone AS (
                DELETE FROM gateway.audit_log
                WHERE occurred_at < now() - keep
                RETURNING 1
            )
            SELECT count(*) INTO removed FROM gone;
            RETURN removed;
        END;
        $$
    """)
    op.execute("REVOKE ALL ON FUNCTION gateway.purge_audit_log(interval) FROM PUBLIC")
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'faue_gateway') THEN
                GRANT EXECUTE ON FUNCTION gateway.purge_audit_log(interval) TO faue_gateway;
            END IF;
        END
        $$
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS gateway.purge_audit_log(interval)")
