"""Backup and restore for the platform's own data.

SECURITY.md carried this as an open gap, and it was the uncomfortable kind: the tool
that tracks FinFlow's backup control had no backup story of its own. An ISMS that
cannot be restored is an ISMS that exists until the first disk failure.

**One artifact, not two.** Evidence attachments are stored in the database as
``LargeBinary`` rather than on a filesystem, so a database archive is already an
attachment archive. That is worth stating, because the obvious design here -- dump the
database, then separately copy a blob directory -- would introduce the exact failure a
backup exists to prevent: two artifacts taken at different moments, restored together,
disagreeing about which attachments existed.

**Logical, not physical.** The archive is a gzipped JSON document built from the model
metadata, not a ``pg_dump`` or a copied SQLite file. That costs speed and size on a
large database, which this is not. It buys three things this project actually needs: it
restores across dialects, so a PostgreSQL deployment can be rehearsed against SQLite;
it is readable, so an auditor can see what was retained; and it does not require the
database's own tooling to be installed wherever the restore happens.

**What is refused.** A restore is the operation most likely to destroy the thing it is
meant to protect, so three refusals are enforced rather than warned about:

  - an archive whose body does not match its recorded digest is corrupt and is refused;
  - an archive written under a different migration revision is refused, because
    restoring yesterday's columns into today's schema loses the difference silently;
  - a non-empty target is refused unless the caller explicitly asks to replace it.
"""

import base64
import datetime as dt
import decimal
import enum
import gzip
import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

import app.models  # noqa: F401  -- registers every table on Base.metadata
from app.db.base import Base

ARCHIVE_VERSION = 1

# A marker, so a truncated or mis-typed file fails loudly rather than as a JSON error.
MAGIC = "grcshield-archive"


class BackupError(Exception):
    """Base class for the refusals below, so a caller can catch all three."""


class ArchiveCorrupt(BackupError):
    """The archive does not match its own digest, or is not an archive at all."""


class SchemaMismatch(BackupError):
    """The archive was written under a different migration revision."""


class TargetNotEmpty(BackupError):
    """The destination already holds data and replacement was not requested."""


@dataclass(frozen=True)
class Manifest:
    """What an archive says about itself, readable without touching a database."""

    version: int
    created_at: str
    revision: str | None
    table_counts: dict[str, int]
    digest: str
    rows: int

    @property
    def summary(self) -> str:
        return (
            f"{self.rows} rows across {len(self.table_counts)} tables, "
            f"revision {self.revision or 'unknown'}, taken {self.created_at}"
        )


def _revision(db: Session) -> str | None:
    """The migration the database is currently at, or None if it is unmanaged."""
    try:
        return db.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception:
        # A database built by create_all rather than by the chain has no such table.
        # That is a legitimate state for the test suite, and not a reason to refuse.
        return None


def _encode(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"__bytes__": base64.b64encode(value).decode("ascii")}
    if isinstance(value, dt.datetime):
        return {"__datetime__": value.isoformat()}
    if isinstance(value, dt.date):
        return {"__date__": value.isoformat()}
    # Numeric columns come back as Decimal. Carried as a string rather than a float,
    # because a money or tolerance figure that survives a backup as 0.1 + 0.2 is not
    # the figure that went in.
    if isinstance(value, decimal.Decimal):
        return {"__decimal__": str(value)}
    # Enum columns come back as members. Most of this schema's enums subclass str and
    # would serialise by accident; carrying the name explicitly means the archive does
    # not depend on that remaining true.
    if isinstance(value, enum.Enum):
        return {"__enum__": value.name}
    return value


def _decode(value: Any) -> Any:
    if isinstance(value, dict):
        if "__bytes__" in value:
            return base64.b64decode(value["__bytes__"])
        if "__datetime__" in value:
            return dt.datetime.fromisoformat(value["__datetime__"])
        if "__date__" in value:
            return dt.date.fromisoformat(value["__date__"])
        if "__decimal__" in value:
            return decimal.Decimal(value["__decimal__"])
        if "__enum__" in value:
            # SQLAlchemy resolves an Enum column from the member name on insert.
            return value["__enum__"]
    return value


def create(db: Session, *, now: dt.datetime | None = None) -> bytes:
    """Produce one archive holding every row, including attachment bytes."""
    tables: dict[str, list[dict[str, Any]]] = {}
    for table in Base.metadata.sorted_tables:
        tables[table.name] = [
            {k: _encode(v) for k, v in dict(row._mapping).items()}
            for row in db.execute(select(table))
        ]

    body = json.dumps(tables, separators=(",", ":"), sort_keys=True).encode("utf-8")
    header = {
        "magic": MAGIC,
        "version": ARCHIVE_VERSION,
        "created_at": (now or dt.datetime.now(dt.UTC)).isoformat(),
        "revision": _revision(db),
        "table_counts": {name: len(rows) for name, rows in tables.items()},
        "sha256": hashlib.sha256(body).hexdigest(),
    }
    document = json.dumps({"header": header, "body": body.decode("utf-8")}).encode("utf-8")
    return gzip.compress(document)


def inspect(archive: bytes) -> Manifest:
    """Read and verify an archive without a database. Raises ArchiveCorrupt."""
    try:
        document = json.loads(gzip.decompress(archive))
        header = document["header"]
        body = document["body"].encode("utf-8")
    except Exception as exc:
        raise ArchiveCorrupt(f"Not a readable archive: {type(exc).__name__}") from exc

    if header.get("magic") != MAGIC:
        raise ArchiveCorrupt("Missing archive marker; this file is not a GRCShield archive.")
    if hashlib.sha256(body).hexdigest() != header.get("sha256"):
        raise ArchiveCorrupt(
            "The archive body does not match its recorded digest. It has been truncated "
            "or altered, and restoring it would load data nobody can vouch for."
        )

    counts = header.get("table_counts", {})
    return Manifest(
        version=header.get("version", 0),
        created_at=header.get("created_at", "unknown"),
        revision=header.get("revision"),
        table_counts=counts,
        digest=header["sha256"],
        rows=sum(counts.values()),
    )


def restore(db: Session, archive: bytes, *, replace: bool = False) -> Manifest:
    """Load an archive into a database, refusing the three unsafe cases."""
    manifest = inspect(archive)

    target_revision = _revision(db)
    if manifest.revision and target_revision and manifest.revision != target_revision:
        raise SchemaMismatch(
            f"The archive was taken at migration {manifest.revision} and this database "
            f"is at {target_revision}. Bring the database to the archive's revision "
            "first; restoring across a schema change loses the difference silently."
        )

    occupied = [
        table.name
        for table in Base.metadata.sorted_tables
        if db.scalar(select(func.count()).select_from(table))
    ]
    if occupied and not replace:
        raise TargetNotEmpty(
            f"The target already holds data in {len(occupied)} table(s), including "
            f"{', '.join(occupied[:3])}. Pass replace=True to overwrite it deliberately."
        )

    tables = json.loads(json.loads(gzip.decompress(archive))["body"])

    # Children first on the way out, parents first on the way in.
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(delete(table))
    for table in Base.metadata.sorted_tables:
        rows = tables.get(table.name) or []
        if rows:
            db.execute(table.insert(), [{k: _decode(v) for k, v in row.items()} for row in rows])
    db.commit()
    return manifest
