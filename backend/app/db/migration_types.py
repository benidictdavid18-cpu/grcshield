"""Column types for the migrations.

The migrations create each PostgreSQL enum type explicitly, with ``checkfirst=True``, so
that a re-run against a half-migrated database is safe. ``op.create_table`` with a plain
``sa.Enum`` column would then emit a second ``CREATE TYPE`` for the same name -- which
PostgreSQL refuses, and SQLite, having no types, never notices. The test suite runs on
SQLite; the first PostgreSQL run was the first time anything noticed.

``pg_enum`` is ``sa.Enum`` everywhere except PostgreSQL, where it is the native ENUM with
``create_type=False``: the column refers to the type, and creating and dropping it stays
the migration's explicit job.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def pg_enum(*values: str, name: str) -> sa.Enum:
    return sa.Enum(*values, name=name).with_variant(
        postgresql.ENUM(*values, name=name, create_type=False), "postgresql"
    )
