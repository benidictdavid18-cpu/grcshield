"""The database serializes reference allocation in the caller's transaction."""

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.models.reference import ReferenceCounter


def allocate(db, column, prefix, width=3):
    # The initial high-water mark preserves existing authored references. Concurrent
    # first writers use ON CONFLICT, followed by one atomic UPDATE ... RETURNING.
    dialect = db.get_bind().dialect.name
    insert = {"sqlite": sqlite_insert, "postgresql": pg_insert}[dialect]
    if db.get(ReferenceCounter, prefix) is None:
        refs = db.scalars(select(column)).all()
        high = max(
            (
                int(ref.rsplit("-", 1)[-1])
                for ref in refs
                if ref.startswith(prefix + "-") and ref.rsplit("-", 1)[-1].isdigit()
            ),
            default=0,
        )
        db.execute(
            insert(ReferenceCounter)
            .values(prefix=prefix, last_value=high)
            .on_conflict_do_nothing(index_elements=["prefix"])
        )
    value = db.scalar(
        update(ReferenceCounter)
        .where(ReferenceCounter.prefix == prefix)
        .values(last_value=ReferenceCounter.last_value + 1)
        .returning(ReferenceCounter.last_value)
    )
    return f"{prefix}-{value:0{width}d}"
