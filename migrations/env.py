"""Alembic environment — one project, every schema.

`target_metadata` is the single registry, which is what makes `alembic check`
able to detect a model edited without a migration.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from faue_db.registry import metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.environ.get("DATABASE_URL")
if database_url:
    # asyncpg is the runtime driver; migrations run synchronously
    config.set_main_option("sqlalchemy.url", database_url.replace("+asyncpg", ""))

target_metadata = metadata

SCHEMAS = ("gateway", "ase", "catalog", "media")


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    """Only manage our own schemas — never touch anything in public."""
    if type_ == "table" and obj.schema not in SCHEMAS:
        return False
    return True


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
        for schema in SCHEMAS:
            connection.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        connection.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
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
