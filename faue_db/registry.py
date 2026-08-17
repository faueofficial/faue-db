"""Single MetaData for Alembic autogenerate.

Importing every model here is what makes `alembic check` able to detect a model
edited without a migration — the guarantee the whole repository rests on.
"""

from faue_db.base import Base

# import for side effects: model registration
from faue_db import ase as _ase  # noqa: F401
from faue_db import gateway as _gateway  # noqa: F401

metadata = Base.metadata

__all__ = ["metadata", "Base"]
