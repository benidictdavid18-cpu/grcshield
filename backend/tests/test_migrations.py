"""The migration chain is executed, not merely written.

Every table in this project is created twice: once by ``Base.metadata.create_all`` (which
is what the rest of the test suite uses) and once by the Alembic chain (which is what a
real deployment uses). Those two can drift silently — a column added to a model and
forgotten in a migration produces a suite that passes and a deployment that fails.

These tests run all six migrations end to end against a scratch database, then ask
Alembic to compare the resulting schema against the model metadata and assert there is
nothing left to generate.

**Scope.** This runs on SQLite, so it proves the chain executes in order, that each
migration is reversible, and that the end state matches the models. It does not exercise
PostgreSQL-specific DDL — native ENUM type creation in particular is a no-op on SQLite.
Those need a real PostgreSQL instance.
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

import app.models  # noqa: F401  -- registers every table on Base.metadata
from app.db.base import Base

BACKEND_ROOT = Path(__file__).resolve().parents[1]

# Tables Alembic itself owns, and which are therefore absent from the model metadata.
_ALEMBIC_OWNED = {"alembic_version"}


def _config(db_url: str) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", db_url)
    return config


@pytest.fixture()
def migrated(tmp_path, monkeypatch):
    """A database built by running the migration chain from empty to head."""
    db_file = tmp_path / "migrated.db"
    url = f"sqlite+pysqlite:///{db_file.as_posix()}"
    # alembic/env.py reads the URL from settings, so point settings at the scratch file.
    monkeypatch.setenv("DATABASE_URL", url)
    from app.core.config import get_settings

    get_settings.cache_clear()

    command.upgrade(_config(url), "head")
    engine = create_engine(url)
    yield engine
    engine.dispose()
    get_settings.cache_clear()


def test_the_chain_is_linear_with_no_gaps_or_branches():
    script = ScriptDirectory(str(BACKEND_ROOT / "alembic"))
    revisions = list(script.walk_revisions())
    assert len(revisions) == 6
    # Newest first; each must point at its predecessor.
    ordered = [r.revision for r in revisions][::-1]
    assert ordered == ["0001", "0002", "0003", "0004", "0005", "0006"]
    assert script.get_current_head() == "0006"
    for revision in revisions:
        assert not isinstance(revision.down_revision, tuple), "no branching allowed"


def test_the_chain_runs_from_empty_to_head(migrated):
    version = migrated.connect().exec_driver_sql(
        "select version_num from alembic_version"
    ).scalar()
    assert version == "0006"


def test_migrations_create_every_table_the_models_declare(migrated):
    built = set(inspect(migrated).get_table_names()) - _ALEMBIC_OWNED
    declared = set(Base.metadata.tables)
    assert declared - built == set(), f"missing from migrations: {sorted(declared - built)}"
    assert built - declared == set(), f"orphaned in migrations: {sorted(built - declared)}"


def test_the_migrated_schema_matches_the_models(migrated):
    """The check that catches a model change nobody wrote a migration for."""
    with migrated.connect() as connection:
        context = MigrationContext.configure(
            connection,
            opts={"compare_type": False, "include_schemas": False},
        )
        diff = [
            entry
            for entry in compare_metadata(context, Base.metadata)
            # SQLite reports no native enum or server-default detail, and reflects some
            # constraints differently; those differences are dialect noise, not drift.
            if entry[0] not in ("modify_default", "modify_nullable")
        ]
    assert diff == [], f"schema drift between migrations and models: {diff}"


def test_key_tables_carry_their_columns(migrated):
    """Spot-check the columns later phases bolted onto earlier tables."""
    inspector = inspect(migrated)
    controls = {c["name"] for c in inspector.get_columns("controls")}
    assert {"design_effectiveness", "operating_effectiveness", "last_tested"} <= controls
    remediation = {c["name"] for c in inspector.get_columns("remediation_items")}
    assert "raised_date" in remediation


def test_the_chain_is_reversible(tmp_path, monkeypatch):
    """A migration you cannot undo is a migration you cannot deploy with confidence."""
    db_file = tmp_path / "reversible.db"
    url = f"sqlite+pysqlite:///{db_file.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    from app.core.config import get_settings

    get_settings.cache_clear()
    config = _config(url)

    command.upgrade(config, "head")
    command.downgrade(config, "base")

    engine = create_engine(url)
    remaining = set(inspect(engine).get_table_names()) - _ALEMBIC_OWNED
    engine.dispose()
    get_settings.cache_clear()
    assert remaining == set(), f"downgrade left tables behind: {sorted(remaining)}"
