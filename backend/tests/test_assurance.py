from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.acceptance import AcceptanceAuthority
from app.models.assurance import AssuranceCycle, AuditProgramme
from app.models.user import User
from app.services.assurance import REVIEW_INPUTS

BASE = "/isms/assurance"
PROGRAMME = {
    "owner": "Audit lead",
    "risk_basis": "Prior failed testing and material service changes.",
    "coverage": "Access and data protection controls",
    "frequency": "Quarterly review of the annual programme",
    "methods": "Sampling and independent interviews",
    "reporting": "Report to leadership with accountable actions.",
    "starts_on": "2026-01-01",
    "ends_on": "2026-12-31",
    "review_date": "2026-12-01",
}
AUDIT = {
    "programme_ref": "AP-TEST",
    "title": "Independent access review",
    "scope": "Privileged access",
    "objectives": "Evaluate access control implementation",
    "criteria": "Approved access policy",
    "auditor": "Independent assessor",
    "independence_note": "The assessor does not operate or own the audited controls.",
    "planned_start": "2026-08-01",
    "planned_end": "2026-08-31",
    "actual_start": "2026-08-04",
    "actual_end": "2026-08-05",
    "outcome_summary": "An exception requires the recorded corrective action.",
}
REVIEW = {
    "review_date": "2026-08-31",
    "chair": "Chief Executive Officer",
    "attendees": "Leadership and ISMS owner",
    "inputs_considered": "All structured inputs considered.",
    "decisions": "Resource the tracked corrective action.",
    "actions": "Tracked actions capture the owner and deadline.",
    "next_review_date": "2026-12-31",
}
COMPLETE = {
    "completed_on": "2026-09-04",
    "evidence_ref": "EV-029",
    "note": "Completion records the assessment and agreed actions.",
}
NC = {
    "description": "Access process failed the stated criterion",
    "source": "INTERNAL_AUDIT",
    "identified_date": "2026-08-01",
    "identified_by": "Independent assessor",
    "owner": "Head of Engineering",
    "immediate_correction": "Removed the affected access.",
    "root_cause_analysis": "The exception was omitted from the review population.",
    "corrective_action": "Reconcile the full population before review.",
    "target_date": "2026-08-31",
    "finding_ref": "FIND-001",
}


def test_seed_does_not_resign_historical_assurance(client):
    rows = client.get(BASE + "/programmes").json()
    assert "TODO AUTHOR:BENNY" in rows[0]["risk_basis"]
    assert client.get(BASE + "/cycles").json() == []
    assert client.get(BASE + "/nonconformities/NC-001/verifications").json() == []


def test_audit_programme_dates_and_database_constraint(client, db_session):
    assert (
        client.put(
            BASE + "/programmes/AP-BAD", json={**PROGRAMME, "ends_on": "2025-01-01"}
        ).status_code
        == 422
    )
    row = db_session.scalar(select(AuditProgramme).where(AuditProgramme.programme_ref == "AP-001"))
    with pytest.raises(IntegrityError), db_session.begin_nested():
        row.ends_on = date(2025, 1, 1)
        db_session.flush()


def test_audit_completion_freezes_programme_record_and_actions(client):
    assert client.put(BASE + "/programmes/AP-TEST", json=PROGRAMME).status_code == 200
    assert client.put(BASE + "/audits/IA-TEST", json=AUDIT).status_code == 200
    action = {
        "action_ref": "ACT-TEST",
        "description": "Reconcile access review population",
        "owner": "Head of Engineering",
        "due_date": "2026-10-01",
        "finding_ref": "FIND-001",
    }
    assert client.post(BASE + "/cycles/IA-TEST/actions", json=action).status_code == 201
    response = client.post(BASE + "/cycles/IA-TEST/complete", json=COMPLETE)
    assert response.status_code == 200, response.text
    frozen = response.json()["completion_snapshot"]
    assert frozen["programme"]["risk_basis"] == PROGRAMME["risk_basis"]
    assert len(frozen["actions"]) == 1
    assert client.get("/isms/audits/IA-TEST").json()["status"] == "COMPLETED"
    assert (
        client.put(BASE + "/audits/IA-TEST", json={**AUDIT, "expected_revision": 2}).status_code
        == 422
    )
    assert client.post(BASE + "/actions/ACT-TEST/complete", json=COMPLETE).status_code == 200
    assert client.get(BASE + "/cycles/IA-TEST").json()["completion_snapshot"] == frozen


def test_audit_requires_actual_period_and_authored_independence(client):
    client.put(BASE + "/programmes/AP-TEST", json=PROGRAMME)
    assert (
        client.put(BASE + "/audits/IA-BAD", json={**AUDIT, "planned_end": "2027-01-01"}).status_code
        == 422
    )
    assert (
        client.put(
            BASE + "/audits/IA-TEST",
            json={**AUDIT, "independence_note": "TODO AUTHOR:BENNY - confirm independence."},
        ).status_code
        == 200
    )
    assert client.post(BASE + "/cycles/IA-TEST/complete", json=COMPLETE).status_code == 422


def test_management_review_requires_all_inputs_and_leadership(client, db_session):
    assert client.put(BASE + "/reviews/MR-TEST", json=REVIEW).status_code == 200
    assert client.post(BASE + "/cycles/MR-TEST/complete", json=COMPLETE).status_code == 403
    user = db_session.scalar(select(User).where(User.username == "isms.manager"))
    db_session.add(
        AcceptanceAuthority(
            user_id=user.id,
            business_role="Chief Executive Officer",
            grant_reason="Fixture leadership authority",
            granted_by="fixture.admin",
            expires_on=date(2027, 1, 1),
        )
    )
    db_session.flush()
    assert client.post(BASE + "/cycles/MR-TEST/complete", json=COMPLETE).status_code == 422
    assert (
        client.put(
            BASE + "/cycles/MR-TEST/inputs/CONTEXT_CHANGES",
            json={"consideration": "The relevant changes were considered."},
        ).status_code
        == 422
    )
    for category in REVIEW_INPUTS:
        response = client.put(
            BASE + "/cycles/MR-TEST/inputs/" + category,
            json={
                "consideration": "The source record was considered and discussed.",
                "evidence_ref": "EV-029",
            },
        )
        assert response.status_code == 200, response.text
    result = client.post(BASE + "/cycles/MR-TEST/complete", json=COMPLETE)
    assert result.status_code == 200, result.text
    assert len(result.json()["completion_snapshot"]["inputs"]) == len(REVIEW_INPUTS)
    assert (
        client.put(
            BASE + "/cycles/MR-TEST/inputs/CONTEXT_CHANGES",
            json={
                "consideration": "An attempt to overwrite the minutes.",
                "evidence_ref": "EV-029",
            },
        ).status_code
        == 422
    )


def test_corrective_verifications_retain_history_and_reopen_failures(client):
    assert client.put(BASE + "/nonconformities/NC-TEST", json=NC).status_code == 200
    verification = {
        "checked_on": "2026-09-04",
        "result": "EFFECTIVE",
        "note": "Reperformed the population reconciliation; the criterion was met.",
        "evidence_ref": "EV-002",
    }
    assert (
        client.post(
            BASE + "/nonconformities/NC-TEST/verifications",
            json={**verification, "evidence_ref": "MISSING"},
        ).status_code
        == 422
    )
    assert (
        client.post(BASE + "/nonconformities/NC-TEST/verifications", json=verification).status_code
        == 201
    )
    assert client.get("/isms/nonconformities/NC-TEST").json()["status"] == "CLOSED"
    assert client.put(BASE + "/nonconformities/NC-TEST", json=NC).status_code == 422
    assert (
        client.post(
            BASE + "/nonconformities/NC-TEST/verifications",
            json={
                **verification,
                "result": "INEFFECTIVE",
                "note": "A subsequent check found the reconciliation did not prevent recurrence.",
            },
        ).status_code
        == 201
    )
    row = client.get("/isms/nonconformities/NC-TEST").json()
    assert row["status"] == "CORRECTIVE_ACTION_IN_PROGRESS" and row["closure_date"] is None
    assert len(client.get(BASE + "/nonconformities/NC-TEST/verifications").json()) == 2


def test_incomplete_root_cause_or_future_verification_cannot_close(client):
    client.put(BASE + "/nonconformities/NC-TEST", json={**NC, "root_cause_analysis": None})
    payload = {
        "checked_on": "2026-09-04",
        "result": "EFFECTIVE",
        "note": "An unsupported closure attempt.",
        "evidence_ref": "EV-002",
    }
    assert (
        client.post(BASE + "/nonconformities/NC-TEST/verifications", json=payload).status_code
        == 422
    )
    client.put(BASE + "/nonconformities/NC-TEST", json=NC)
    assert (
        client.post(
            BASE + "/nonconformities/NC-TEST/verifications",
            json={**payload, "checked_on": "2027-01-01"},
        ).status_code
        == 422
    )


def test_database_and_readonly_role_refuse_unsigned_completion(client, db_session, auditor_client):
    client.put(BASE + "/reviews/MR-TEST", json=REVIEW)
    row = db_session.scalar(select(AssuranceCycle).where(AssuranceCycle.cycle_ref == "MR-TEST"))
    with pytest.raises(IntegrityError), db_session.begin_nested():
        row.status = "COMPLETED"
        db_session.flush()
    assert auditor_client.put(BASE + "/reviews/MR-READONLY", json=REVIEW).status_code == 403
