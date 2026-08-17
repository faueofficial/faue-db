# faue-db

All SQLAlchemy models and the single Alembic project. Services install this as a
pinned dependency.

**Design:** [`docs/20-services/faue-db.md`](../docs/20-services/faue-db.md)
**ADR:** [0004 — one Alembic project](../docs/80-adr/0004-single-alembic-project-in-faue-db.md),
[0021 — workspace tenancy](../docs/80-adr/0021-workspace-tenancy-model.md)

## Why one project

Autogenerate needs the models, so co-locating models and migrations is the only
way to get a **mechanical** guarantee rather than a convention: a model edited
without a migration cannot merge.

Centralising the schema does not mean losing ownership — `CODEOWNERS` gates
review, and Postgres role grants make cross-schema access fail at the database.

## Workflow

```bash
alembic revision --autogenerate -m "add wear_count to vault_items"
$EDITOR migrations/versions/<rev>_*.py     # ALWAYS read the generated migration
alembic upgrade head
alembic downgrade -1 && alembic upgrade head
pytest
```

Autogenerate misses column renames (it emits a drop and an add, losing data),
server defaults, expression indexes, and anything involving `vector` columns.
Treat it as a draft.

## CI gates

| Gate | Catches |
|---|---|
| `alembic upgrade head` | A migration that does not apply |
| `alembic check` | **A model edited without a migration** |
| `downgrade -1 && upgrade head` | A broken downgrade, at author time rather than during an incident |
| `test_no_cross_schema_foreign_keys` | An FK that would make the service split impossible |
| `test_user_owned_models_are_workspace_scoped` | A table that silently un-reserves ADR 0021 |
| `test_sensitive_columns_are_encrypted_or_indexed` | A direct identifier stored in plaintext |
| `test_timestamps_are_timezone_aware` | Naive timestamps |

## Deploy ordering

Fixed and not negotiable:

```
1  migrations (EXPAND ONLY — additive, nullable, new tables)
2  service code
3  a LATER release contracts (drop columns, tighten constraints)
```

Expand-contract is what makes rollback safe. A breaking migration shipped with
the code that needs it means rolling back the code leaves the database ahead of
it — and rolling back the database loses everything written in between.

## Vector columns

Dimension is deliberately unconstrained: several embedding models coexist during
a migration and they have different dimensions. HNSW indexes are created per
`model_id` in raw SQL inside the migration, because autogenerate does not handle
partial vector indexes.
