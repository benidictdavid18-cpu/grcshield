import re
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import CheckConstraint, create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.ai import AiInteraction
from app.models.reference import ReferenceCounter
from app.services.references import allocate
from tests.test_migrations import migrated  # noqa: F401,F811


def test_concurrent_allocators_do_not_reuse_references(tmp_path):
    engine = create_engine(
        f'sqlite+pysqlite:///{(tmp_path / "references.db").as_posix()}',
        connect_args={"timeout": 15},
    )
    ReferenceCounter.__table__.create(engine)
    AiInteraction.__table__.create(engine)

    def allocate_one(_):
        with Session(engine) as db:
            ref = allocate(db, AiInteraction.interaction_ref, "AI", 6)
            db.commit()
            return ref

    with ThreadPoolExecutor(max_workers=4) as pool:
        refs = list(pool.map(allocate_one, range(16)))
    assert len(set(refs)) == 16
    assert sorted(refs) == [f"AI-{i:06d}" for i in range(1, 17)]
    engine.dispose()


def test_named_checks_match_migrated_database(migrated):  # noqa: F811
    inspector = inspect(migrated)
    def normalize(sql):
        return re.sub(r"\s+", "", sql).lower()
    for table in Base.metadata.sorted_tables:
        actual = {
            c["name"]: normalize(c["sqltext"])
            for c in inspector.get_check_constraints(table.name)
            if c["name"]
        }
        expected = {
            c.name: normalize(str(c.sqltext))
            for c in table.constraints
            if isinstance(c, CheckConstraint) and c.name
        }
        assert actual == expected, table.name


def test_migrated_database_refuses_impossible_bia(migrated):  # noqa: F811
    with migrated.begin() as connection:
        with pytest.raises(IntegrityError):
            connection.execute(
                text(
                    "INSERT INTO business_impact_analyses (bia_ref,process_name,process_description,owner_role,rto_hours,rpo_hours,mtpd_hours,currency,impact_1h,impact_24h,impact_1w,impact_note,workaround) VALUES ('BIA-INVALID','process','description','owner',10,1,2,'GBP',0,0,0,'note','workaround')"
                )
            )
