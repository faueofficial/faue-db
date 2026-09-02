"""Alembic environment — one project, every schema.

`target_metadata` is the single registry, which is what makes `alembic check`
able to detect a model edited without a migration.
"""

from __future__ import annotations

import os
from logging.config import fileConfig
from pathlib import Path

from dotenv import load_dotenv

from alembic import context
from sqlalchemy import engine_from_config, pool

from faue_db.registry import metadata

# Read .env before anything looks at DATABASE_URL. Without this, `alembic
# upgrade head` fails with an empty URL in a shell where .env is right there.
#
# Walks up to the workspace root, nearest last, so a service .env overrides a
# shared one. Existing environment variables always win — Railway sets them and
# no file exists there.
def _load_env() -> None:
    origin = Path(__file__).resolve().parent
    found = []
    for directory in (origin, *origin.parents):
        candidate = directory / ".env"
        if candidate.is_file():
            found.append(candidate)
        if (directory / "docs" / "repos.yaml").is_file():
            break
    for path in reversed(found):
        load_dotenv(path)


_load_env()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.environ.get("DATABASE_URL")
if database_url:
    # asyncpg is the runtime driver; migrations run synchronously
    config.set_main_option("sqlalchemy.url", database_url.replace("+asyncpg", ""))

target_metadata = metadata

SCHEMAS = ("gateway", "ase", "catalog", "media")


#: Indexes managed by hand in migrations rather than declared on a model.
#: pgvector cannot index a dimensionless column, so these are cast-expression
#: partial indexes that SQLAlchemy cannot express — autogenerate would see them
#: as orphans and try to drop them on every run.
MANUAL_INDEX_MARKERS = ("_hnsw_",)


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    """Only manage our own schemas, and leave hand-written indexes alone."""
    if type_ == "table" and obj.schema not in SCHEMAS:
        return False
    if type_ == "index" and name and any(m in name for m in MANUAL_INDEX_MARKERS):
        return False
    return True


def _require_pgvector(connection) -> None:
    """Installing an extension needs superuser; running migrations does not.

    Keeping them separate means the migrator role stays unprivileged, and a
    missing extension produces a clear message instead of a permission error
    three frames deep.
    """
    installed = connection.exec_driver_sql(
        "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
    ).first()
    if installed is None:
        raise RuntimeError(
            "pgvector is not installed in this database.\n"
            "Run once as a superuser:  psql -d <db> -c 'CREATE EXTENSION vector;'"
        )


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        _require_pgvector(connection)
        for schema in SCHEMAS:
            connection.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_object=include_object,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
