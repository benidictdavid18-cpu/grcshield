"""Backup is only a control if the restore has been exercised.

An untested backup is a belief. These run the round trip and the three refusals, so the
claim in SECURITY.md is backed by something that fails the build when it stops holding.
"""

import datetime as dt
import gzip
import json

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  -- registers every table on Base.metadata
from app.db.base import Base
from app.models.risk import Risk
from app.services import backup


@pytest.fixture()
def empty_db():
    """A second database, schema only, to restore into."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_an_archive_round_trips_into_an_empty_database(db_session, empty_db):
    """Every table comes back with the row count it went in with."""
    archive = backup.create(db_session)
    manifest = backup.restore(empty_db, archive)

    assert manifest.rows > 0, "an archive of an empty database would prove nothing"
    for table in Base.metadata.sorted_tables:
        restored = empty_db.scalar(select(func.count()).select_from(table))
        assert restored == manifest.table_counts[table.name], table.name

    # And the data is the data, not merely the right number of rows.
    risk = empty_db.scalar(select(Risk).where(Risk.risk_ref == "RISK-004"))
    assert risk is not None
    assert risk.inherent_likelihood == 4
    assert risk.inherent_impact == 5


def test_binary_and_date_columns_survive_encoding():
    """Attachment bytes are the payload most likely to be quietly corrupted.

    They live in the database as LargeBinary, so the archive carries them as base64
    rather than as text that happens to decode today.
    """
    for value in (
        b"\x00\x01\x02\xff PDF bytes",
        dt.date(2026, 10, 2),
        dt.datetime(2026, 10, 2, 9, 15),
    ):
        assert backup._decode(backup._encode(value)) == value


def test_a_corrupted_archive_is_refused(db_session):
    """A digest that does not match its body means nobody can vouch for the contents."""
    archive = backup.create(db_session)
    document = json.loads(gzip.decompress(archive))
    document["body"] = document["body"].replace("RISK-004", "RISK-XXX", 1)
    tampered = gzip.compress(json.dumps(document).encode("utf-8"))

    with pytest.raises(backup.ArchiveCorrupt, match="does not match its recorded digest"):
        backup.inspect(tampered)


def test_a_file_that_is_not_an_archive_is_refused():
    with pytest.raises(backup.ArchiveCorrupt):
        backup.inspect(b"not gzip, not json, not ours")


def test_a_schema_mismatch_is_refused(db_session, empty_db, monkeypatch):
    """Restoring yesterday's columns into today's schema loses the difference."""
    monkeypatch.setattr(backup, "_revision", lambda db: "0027")
    archive = backup.create(db_session)
    monkeypatch.setattr(backup, "_revision", lambda db: "0028")

    with pytest.raises(backup.SchemaMismatch, match="0027"):
        backup.restore(empty_db, archive)


def test_a_non_empty_target_is_refused_unless_replacement_is_asked_for(db_session):
    """The restore most likely to destroy data is the one into a live database."""
    archive = backup.create(db_session)

    with pytest.raises(backup.TargetNotEmpty, match="replace=True"):
        backup.restore(db_session, archive)


def test_the_manifest_reads_without_a_database(db_session):
    """An operator checking an archive should not need to connect to anything."""
    manifest = backup.inspect(backup.create(db_session))
    assert manifest.version == backup.ARCHIVE_VERSION
    assert "rows across" in manifest.summary
    assert len(manifest.digest) == 64
