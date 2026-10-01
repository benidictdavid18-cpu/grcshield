from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.incidents import SecurityEvent

BASE = "/incidents/EVT-TEST"
EVENT = {
    "title": "Reported access event",
    "description": "A user reported a suspicious session.",
    "source": "Service desk report",
    "occurred_on": "2026-08-01",
    "reported_on": "2026-08-02",
    "owner": "Head of Engineering",
    "risk_ref": "RISK-004",
    "control_ref": "AC-002",
    "finding_ref": "FIND-001",
}


def entry(client, kind, **extra):
    revision = client.get(BASE).json()["revision"]
    return client.post(
        BASE + "/timeline",
        json={
            "kind": kind,
            "occurred_on": "2026-08-03",
            "note": "The response owner recorded this decision after review.",
            "expected_revision": revision,
            **extra,
        },
    )


def test_seed_is_an_unassessed_event_not_a_breach(client):
    row = client.get("/incidents/EVT-001").json()
    assert row["status"] == "REPORTED" and row["severity"] == "UNASSESSED"
    assert "TODO AUTHOR:BENNY" in row["notification_decision"]
    assert row["disclaimer"] == "Sample / Portfolio Assessment"


def test_links_dates_and_write_access_are_enforced(client, auditor_client):
    assert auditor_client.post(BASE, json=EVENT).status_code == 403
    for change in (
        {"control_ref": "MISSING"},
        {"control_ref": "DP-005"},
        {"finding_ref": "FIND-003"},
        {"reported_on": "2026-07-01"},
        {"owner": " "},
    ):
        assert client.post(BASE, json={**EVENT, **change}).status_code == 422
    assert client.post(BASE, json=EVENT).status_code == 201
    assert client.post(BASE, json=EVENT).status_code == 422


def test_incident_lifecycle_retains_decisions_and_does_not_change_risk(client):
    risk = client.get("/risks/RISK-004").json()
    client.post(BASE, json=EVENT)
    assert entry(client, "TRIAGE", disposition="INCIDENT").status_code == 422
    assert (
        entry(
            client,
            "TRIAGE",
            disposition="INCIDENT",
            severity="HIGH",
            notification_decision="The response owner will assess notifications with legal counsel.",
        ).status_code
        == 201
    )
    assert (
        entry(
            client, "CLOSED", lessons="Update response playbook.", evidence_ref="EV-002"
        ).status_code
        == 422
    )
    assert entry(client, "CONTAINED").status_code == 201
    assert entry(client, "RECOVERED").status_code == 201
    assert (
        entry(
            client, "CLOSED", lessons="TODO AUTHOR:BENNY - review", evidence_ref="EV-002"
        ).status_code
        == 422
    )
    assert (
        entry(
            client, "CLOSED", lessons="Update response playbook.", evidence_ref="EV-002"
        ).status_code
        == 201
    )
    frozen = client.get(BASE + "/timeline").json()
    assert frozen[-1]["snapshot"]["status"] == "CLOSED"
    assert entry(client, "RESPONSE").status_code == 422
    assert entry(client, "REOPENED").status_code == 201
    assert client.get(BASE + "/timeline").json()[: len(frozen)] == frozen
    assert client.get("/risks/RISK-004").json() == risk


def test_stale_or_backdated_decision_is_refused(client):
    client.post(BASE, json=EVENT)
    assert entry(client, "RESPONSE").status_code == 201
    assert entry(client, "RESPONSE", expected_revision=1).status_code == 422
    assert entry(client, "RESPONSE", occurred_on="2026-08-02").status_code == 422
    assert (
        entry(
            client, "EVIDENCE", attachment_id=999, custody_note="Collected by analyst."
        ).status_code
        == 422
    )


def test_database_refuses_missing_control_and_unsigned_closure(client, db_session):
    client.post(BASE, json=EVENT)
    row = db_session.scalar(select(SecurityEvent).where(SecurityEvent.event_ref == "EVT-TEST"))
    with pytest.raises(IntegrityError), db_session.begin_nested():
        row.control_id = None
        db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        row.reported_on = date(2025, 1, 1)
        db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        row.status = "CLOSED"
        db_session.flush()
