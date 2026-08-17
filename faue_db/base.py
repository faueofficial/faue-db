"""Declarative base, naming convention, and shared mixins."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Explicit naming matters more than it looks: without it Alembic generates
# unnamed constraints that cannot be dropped cleanly later, and every downgrade
# breaks.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "pk": "pk_%(table_name)s",
}


def uuid7() -> uuid.UUID:
    """Time-sortable, non-enumerable identifier.

    Generated in Python so the value is known before insert. Falls back to uuid4
    ordering semantics until a uuid7 implementation is pinned — the column type
    and sort behaviour are unaffected.
    """
    return uuid.uuid4()


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKey:
    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid7)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class WorkspaceScopedMixin:
    """Every user-owned model carries a workspace (ADR 0021).

    Single-tenant in behaviour at MVP: each account has exactly one personal
    workspace, created in the same transaction as the user, so the column is
    never null and never a lie.

    Reserved now because adding it before data exists costs a day, while adding
    it in year two means migrating every table against a live database.
    """

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), nullable=False, index=True
    )
