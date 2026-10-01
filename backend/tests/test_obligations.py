from datetime import date

from sqlalchemy import select

from app.models.acceptance import AcceptanceAuthority
from app.models.user import User

BASE = "/obligations/OBL-TEST"
OBLIGATION = {
    "title": "Contract review",
    "kind": "CONTRACTUAL",
    "source": "Signed test agreement",
    "source_version": "1",
    "jurisdiction": "Contract jurisdiction",
    "requirement": "Review security assurance annually.",
    "owner": "Head of Legal & Compliance",
    "review_date": "2026-12-01",
    "control_ref": "TP-003",
    "supplier_ref": "SUP-001",
}
DECISION = {
    "expected_revision": 1,
    "kind": "APPLICABILITY",
    "decided_on": "2026-09-01",
    "result": "APPLICABLE",
    "note": "The agreement governs the scoped service.",
    "evidence_ref": "EV-023",
}


def grant(db):
    actor = db.scalar(select(User).where(User.username == "isms.manager"))
    db.add(
        AcceptanceAuthority(
            user_id=actor.id,
            business_role="Head of Legal & Compliance",
            grant_reason="Fixture authority",
            granted_by="fixture.admin",
            expires_on=date(2027, 1, 1),
        )
    )
    db.flush()


def test_applicability_requires_authority_and_retains_exact_source(client, db_session):
    assert client.put(BASE, json=OBLIGATION).status_code == 200
    assert client.post(BASE + "/decisions", json=DECISION).status_code == 403
    grant(db_session)
    result = client.post(BASE + "/decisions", json=DECISION)
    assert result.status_code == 201, result.text
    frozen = result.json()["snapshot"]
    assert (
        client.put(
            BASE, json={**OBLIGATION, "expected_revision": 2, "source_version": "2"}
        ).status_code
        == 200
    )
    assert client.get(BASE).json()["applicability"] == "UNASSESSED"
    assert client.get(BASE + "/decisions").json()[0]["snapshot"] == frozen


def test_evaluation_requires_approved_applicability_and_owned_remediation(client, db_session):
    client.put(BASE, json=OBLIGATION)
    evaluation = {**DECISION, "kind": "EVALUATION", "result": "ACTION_REQUIRED"}
    assert client.post(BASE + "/decisions", json=evaluation).status_code == 422
    grant(db_session)
    client.post(BASE + "/decisions", json=DECISION)
    assert (
        client.post(BASE + "/decisions", json={**evaluation, "expected_revision": 2}).status_code
        == 422
    )
    assert (
        client.post(
            BASE + "/decisions",
            json={**evaluation, "expected_revision": 2, "remediation_ref": "REM-017"},
        ).status_code
        == 201
    )


def test_unknown_source_links_and_unwritten_judgment_are_refused(client, db_session):
    assert client.put(BASE, json={**OBLIGATION, "supplier_ref": "MISSING"}).status_code == 422
    client.put(BASE, json=OBLIGATION)
    grant(db_session)
    assert (
        client.post(
            BASE + "/decisions", json={**DECISION, "note": "TODO AUTHOR:BENNY - decide"}
        ).status_code
        == 422
    )
    assert client.get("/obligations/OBL-001").json()["applicability"] == "UNASSESSED"
