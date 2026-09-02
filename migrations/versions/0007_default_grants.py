"""grants for new tables, now and in future

Revision ID: 0007_default_grants
Revises: 0006_asset_backup
Create Date: 2026-09-02 18:20:00.000000

`0001` ran `GRANT ... ON ALL TABLES`, which grants on the tables that existed at
that moment and says nothing about later ones. Every table added since —
`assets` in `0005` — has therefore been unreadable and unwritable by the service
role, and every future table would be too.

The symptom is `permission denied for table <new table>` on the first request
that touches it, in whichever environment was deployed first. It is silent until
then: migrations succeed, the service starts, and only the feature using the new
table fails.

`ALTER DEFAULT PRIVILEGES` fixes it going forward. It attaches to the creating
role, so it is scoped to `faue_migrator`, which is the only role that runs DDL.
"""

from alembic import op
import sqlalchemy as sa


revision = '0007_default_grants'
down_revision = '0006_asset_backup'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Catch up the tables added since 0001.
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA gateway "
        "TO faue_gateway"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ase TO faue_ase"
    )
    op.execute("GRANT USAGE ON ALL SEQUENCES IN SCHEMA gateway TO faue_gateway")
    op.execute("GRANT USAGE ON ALL SEQUENCES IN SCHEMA ase TO faue_ase")

    # And every table created from here on. Attached to faue_migrator because
    # default privileges follow the role that creates the object, and that role
    # is the only one holding DDL.
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE faue_migrator IN SCHEMA gateway "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO faue_gateway"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE faue_migrator IN SCHEMA ase "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO faue_ase"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE faue_migrator IN SCHEMA gateway "
        "GRANT USAGE ON SEQUENCES TO faue_gateway"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE faue_migrator IN SCHEMA ase "
        "GRANT USAGE ON SEQUENCES TO faue_ase"
    )

    # Re-assert the append-only tables. The blanket GRANT above would otherwise
    # have handed back the UPDATE and DELETE that 0001 deliberately revoked —
    # which is the whole guarantee behind the audit log.
    op.execute("REVOKE UPDATE, DELETE ON gateway.audit_log FROM faue_gateway")
    op.execute("REVOKE UPDATE, DELETE ON gateway.quiz_responses FROM faue_gateway")


def downgrade() -> None:
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE faue_migrator IN SCHEMA gateway "
        "REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM faue_gateway"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE faue_migrator IN SCHEMA ase "
        "REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM faue_ase"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE faue_migrator IN SCHEMA gateway "
        "REVOKE USAGE ON SEQUENCES FROM faue_gateway"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE faue_migrator IN SCHEMA ase "
        "REVOKE USAGE ON SEQUENCES FROM faue_ase"
    )
