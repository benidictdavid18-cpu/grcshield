"""An isolated PostgreSQL schema; CI supplies a disposable database."""

import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.core.config import get_settings
from tests.test_migrations import _config


@pytest.mark.skipif(
    not os.environ.get("TEST_POSTGRES_URL"),
    reason="Requires the explicit disposable PostgreSQL integration database",
)
def test_postgres_migrations_and_invalid_writes(monkeypatch):
    url = os.environ["TEST_POSTGRES_URL"]
    schema = "grc_test_" + uuid.uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA {schema}"))
    scoped = (
        make_url(url)
        .update_query_dict({"options": f"-csearch_path={schema}"})
        .render_as_string(hide_password=False)
    )
    engine = create_engine(scoped)
    try:
        monkeypatch.setenv("DATABASE_URL", scoped)
        get_settings.cache_clear()
        command.upgrade(_config(scoped), "head")
        with engine.begin() as connection:
            with pytest.raises(IntegrityError):
                connection.execute(
                    text("INSERT INTO reference_counters (prefix,last_value) VALUES ('BAD',-1)")
                )
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        admin.dispose()
        get_settings.cache_clear()
