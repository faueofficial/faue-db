"""Service roles can reach every table they own — including new ones.

`0001` ran `GRANT ... ON ALL TABLES`, which covers the tables existing at that
moment and says nothing about later ones. `assets`, added in `0005`, was
therefore unreadable and unwritable by `faue_gateway` until `0007`.

The failure mode is what makes this worth a guard: migrations succeed, the
service starts, health checks pass, and only the one feature touching the new
table returns `permission denied` — in whichever environment was deployed first.

These run against a real database because grants are a property of the database,
not of the models.
"""

import os

import pytest
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL_SYNC",
    "postgresql://faue_migrator:faue_local_dev@localhost:5432/faue_test",
)

#: The service role that owns each schema.
OWNERS = {"gateway": "faue_gateway", "ase": "faue_ase"}

#: Append-only. The service role may insert and read, never rewrite — this is
#: the guarantee the audit log rests on, and a blanket re-GRANT would undo it.
APPEND_ONLY = {"audit_log", "quiz_responses"}


@pytest.fixture(scope="module")
def connection():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        yield conn
    engine.dispose()


def _tables(connection, schema: str) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = :schema AND table_type = 'BASE TABLE'"
            ),
            {"schema": schema},
        )
    }


def _granted(connection, schema: str, role: str) -> dict[str, set[str]]:
    grants: dict[str, set[str]] = {}
    for table, privilege in connection.execute(
        text(
            "SELECT table_name, privilege_type FROM information_schema.role_table_grants "
            "WHERE table_schema = :schema AND grantee = :role"
        ),
        {"schema": schema, "role": role},
    ):
        grants.setdefault(table, set()).add(privilege)
    return grants


@pytest.mark.parametrize("schema,role", OWNERS.items())
def test_every_table_is_reachable_by_its_service_role(connection, schema, role):
    """The guard that would have caught `assets`.

    A new table with no grant is invisible until the first request touches it,
    and by then it is in production.
    """
    tables = _tables(connection, schema)
    grants = _granted(connection, schema, role)

    missing = sorted(tables - set(grants))
    assert not missing, (
        f"{role} has no grant on {missing}. A GRANT ON ALL TABLES only covers "
        "tables that existed when it ran — see migration 0007."
    )


@pytest.mark.parametrize("schema,role", OWNERS.items())
def test_every_table_allows_the_four_operations(connection, schema, role):
    tables = _tables(connection, schema)
    grants = _granted(connection, schema, role)

    for table in sorted(tables):
        expected = {"SELECT", "INSERT"} | (
            set() if table in APPEND_ONLY else {"UPDATE", "DELETE"}
        )
        assert expected <= grants.get(table, set()), (
            f"{role} is missing {sorted(expected - grants.get(table, set()))} "
            f"on {schema}.{table}"
        )


def test_append_only_tables_stay_append_only(connection):
    """A blanket re-GRANT hands back exactly what was deliberately revoked.

    `0007` had to re-revoke these for that reason, and this is what notices if a
    future migration forgets.
    """
    grants = _granted(connection, "gateway", "faue_gateway")

    for table in APPEND_ONLY:
        held = grants.get(table, set())
        assert "UPDATE" not in held, f"{table} must never be updatable"
        assert "DELETE" not in held, f"{table} must never be deletable"


@pytest.mark.parametrize("schema,role", [("gateway", "faue_ase"), ("ase", "faue_gateway")])
def test_a_service_role_cannot_reach_the_other_schema(connection, schema, role):
    """Cross-schema isolation fails at the database rather than by convention —
    that is what keeps one migration project from becoming a free-for-all."""
    assert _granted(connection, schema, role) == {}


@pytest.mark.parametrize("schema,role", OWNERS.items())
def test_future_tables_are_granted_automatically(connection, schema, role):
    """`ALTER DEFAULT PRIVILEGES`, asserted by creating a table and checking.

    Without it, every table added from here repeats the `assets` failure, and
    the next person to notice is a user.
    """
    connection.execute(text(f"CREATE TABLE {schema}._grant_probe (id int)"))
    try:
        granted = _granted(connection, schema, role).get("_grant_probe", set())
        assert {"SELECT", "INSERT", "UPDATE", "DELETE"} <= granted, (
            f"a newly created table in {schema} was not granted to {role}"
        )
    finally:
        connection.execute(text(f"DROP TABLE {schema}._grant_probe"))
        connection.commit()
