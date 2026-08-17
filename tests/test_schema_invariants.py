"""Schema invariants enforced at build time.

Each of these exists because of a specific failure that is invisible until it is
expensive:

* a cross-schema foreign key makes the future service split impossible, and
  nothing reveals it until you try;
* a user-owned table without `workspace_id` silently un-reserves the tenancy
  decision (ADR 0021), and the omission is only found when professional
  features are built;
* a sensitive column stored in plaintext is a compliance finding, not a bug
  report.
"""

from __future__ import annotations

import pytest
from sqlalchemy import inspect

from faue_db.base import Base, WorkspaceScopedMixin
from faue_db.registry import metadata

# Models legitimately outside a workspace. Every entry states WHY — an exemption
# without a reason is how this check quietly stops meaning anything.
NOT_WORKSPACE_SCOPED = {
    "gateway.workspaces": "defines workspaces; cannot belong to one",
    "gateway.workspace_members": "the membership edge itself",
    "gateway.users": "a user is a member of workspaces, not owned by one",
    "gateway.auth_identities": "identity precedes workspace resolution at login",
    "gateway.refresh_tokens": "session credential, bound to a user not a workspace",
    "gateway.deletion_ledger": "compliance record; outlives the user and workspace",
    "gateway.admin_users": "staff, not customers",
    "gateway.audit_log": "append-only compliance record across all workspaces",
    "gateway.outbox": "infrastructure",
    "ase.outbox": "infrastructure",
    "ase.style_embeddings": "shared style library content",
    "ase.style_library": "shared content",
    "ase.style_reference_images": "shared content",
    "ase.accessory_pairings": "shared content",
    "ase.spree_messages": "scoped through its parent session",
    "ase.weather_cache": "keyed by coarse geohash; no user",
    "ase.model_calls": "operational telemetry",
    "ase.budgets": "operational",
}

SENSITIVE_COLUMN_HINTS = ("email", "phone", "measurement", "height_cm", "token", "secret")
ALLOWED_PLAINTEXT = {
    "gateway.auth_identities.email_bidx",
    "gateway.auth_identities.phone_bidx",
    "gateway.admin_users.email_bidx",
    "gateway.refresh_tokens.token_hash",   # a hash, not the credential
    "gateway.notify_devices.token_enc",
}


def all_models() -> list[type]:
    return list(Base.registry.mappers)


def qualified(table) -> str:
    return f"{table.schema}.{table.name}"


def test_no_cross_schema_foreign_keys():
    """References across schemas are plain UUID columns. One accidental FK makes
    extracting a service impossible, and it is invisible until then."""
    offenders = []
    for table in metadata.tables.values():
        for fk in table.foreign_keys:
            if fk.column.table.schema != table.schema:
                offenders.append(
                    f"{qualified(table)}.{fk.parent.name} -> {qualified(fk.column.table)}"
                )
    assert not offenders, "cross-schema foreign keys found:\n  " + "\n  ".join(offenders)


def test_user_owned_models_are_workspace_scoped():
    """ADR 0021. A model with user_id must carry workspace_id, or be listed above
    with a reason."""
    offenders = []
    for mapper in all_models():
        table = mapper.local_table
        if table is None:
            continue
        name = qualified(table)
        has_user = "user_id" in table.columns
        has_workspace = "workspace_id" in table.columns
        if has_user and not has_workspace and name not in NOT_WORKSPACE_SCOPED:
            offenders.append(name)
    assert not offenders, (
        "user-owned tables missing workspace_id (ADR 0021):\n  "
        + "\n  ".join(offenders)
        + "\nAdd WorkspaceScopedMixin, or add an entry to NOT_WORKSPACE_SCOPED "
          "explaining why it is exempt."
    )


def test_workspace_exemptions_still_exist():
    """A stale exemption is a check that has stopped applying."""
    known = {qualified(t) for t in metadata.tables.values()}
    stale = set(NOT_WORKSPACE_SCOPED) - known
    assert not stale, f"exemptions for tables that no longer exist: {sorted(stale)}"


def test_workspace_column_is_not_nullable():
    """Nullable would make it a lie until it became true. The personal workspace
    is created in the same transaction as the user."""
    for table in metadata.tables.values():
        column = table.columns.get("workspace_id")
        if column is not None:
            assert not column.nullable, f"{qualified(table)}.workspace_id must be NOT NULL"


def test_sensitive_columns_are_encrypted_or_indexed():
    """Anything that looks like a direct identifier is either `_enc` (envelope
    encrypted) or `_bidx` (a blind index)."""
    from sqlalchemy import Boolean, Integer, Numeric, SmallInteger

    # A sensitive VALUE is stored as text or binary. A boolean flag
    # (email_verified) or an integer count (tokens_in) merely shares a substring
    # with one, and flagging those trains people to ignore this check.
    NON_VALUE_TYPES = (Boolean, Integer, SmallInteger, Numeric)

    offenders = []
    for table in metadata.tables.values():
        for column in table.columns:
            full = f"{qualified(table)}.{column.name}"
            if full in ALLOWED_PLAINTEXT:
                continue
            if isinstance(column.type, NON_VALUE_TYPES):
                continue
            if any(h in column.name for h in SENSITIVE_COLUMN_HINTS):
                if not (column.name.endswith("_enc") or column.name.endswith("_bidx")):
                    offenders.append(full)
    assert not offenders, (
        "sensitive columns stored in plaintext:\n  " + "\n  ".join(offenders)
    )


def test_every_table_has_a_schema():
    """No table may land in `public` — schema-per-service is what makes the role
    grants meaningful."""
    unscoped = [t.name for t in metadata.tables.values() if not t.schema]
    assert not unscoped, f"tables without an explicit schema: {unscoped}"


def test_naming_convention_is_applied():
    """Without explicit naming, Alembic emits unnamed constraints that cannot be
    dropped cleanly later, and every downgrade breaks."""
    assert metadata.naming_convention["pk"] == "pk_%(table_name)s"
    assert metadata.naming_convention["fk"] == "fk_%(table_name)s_%(column_0_name)s"


def test_timestamps_are_timezone_aware():
    offenders = []
    for table in metadata.tables.values():
        for column in table.columns:
            if column.name.endswith("_at") and hasattr(column.type, "timezone"):
                if not column.type.timezone:
                    offenders.append(f"{qualified(table)}.{column.name}")
    assert not offenders, "naive timestamps (must be TIMESTAMPTZ):\n  " + "\n  ".join(offenders)


@pytest.mark.parametrize("schema", ["gateway", "ase"])
def test_schema_has_tables(schema):
    assert any(t.schema == schema for t in metadata.tables.values())
