from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.audit_trail import AuditEvent
from app.models.bootstrap import SampleBootstrap
from app.models.risk import Risk
from app.seed import run_seed
from app.services.bootstrap import prepare


def test_restart_preserves_authored_edits_and_links(db_session, monkeypatch):
    risk = db_session.scalar(select(Risk).where(Risk.risk_ref == "RISK-004"))
    risk.residual_justification = "Explicitly edited by the author before restart."
    risk.control_links[0].proof_note = "Retained author note."
    db_session.flush()

    @contextmanager
    def session():
        yield db_session

    monkeypatch.setattr(run_seed, "SessionLocal", session)

    def forbidden(*args):
        raise AssertionError("Startup must not reapply sample values")

    monkeypatch.setattr(run_seed, "seed_iso", forbidden)
    run_seed.main()
    run_seed.main()
    db_session.refresh(risk)
    assert risk.residual_justification == "Explicitly edited by the author before restart."
    assert risk.control_links[0].proof_note == "Retained author note."
    assert db_session.get(SampleBootstrap, 1).status == "PRESERVED"


def test_empty_database_initializes_only_once():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        assert prepare(db) is True
        db.commit()
        assert prepare(db) is False
    engine.dispose()


def test_explicit_reapplication_requires_reason_and_retains_operator_event(db_session):
    with pytest.raises(ValueError):
        prepare(db_session, reapply=True)
    assert prepare(
        db_session,
        reapply=True,
        reason="Restore authored demo for local review",
        operator="test.operator",
    )
    event = db_session.scalar(select(AuditEvent).where(AuditEvent.action == "SAMPLE_REAPPLIED"))
    assert event.actor_username == "test.operator"
    assert db_session.get(SampleBootstrap, 1).status == "REAPPLIED"


def test_database_refuses_second_bootstrap_identity(db_session):
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(SampleBootstrap(id=2, status="INITIALIZED", reason="Invalid singleton"))
        db_session.flush()


def test_bootstrap_status_refuses_anonymous_reads(anon_client):
    assert anon_client.get("/sample-bootstrap").status_code == 401


def test_bootstrap_status_is_readable_to_auditor(auditor_client):
    assert auditor_client.get("/sample-bootstrap").status_code == 200
