import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.suppliers import Supplier

BASE = "/suppliers/SUP-TEST"
SUPPLIER = {
    "name": "Test provider",
    "service": "Hosted service",
    "owner": "Head of Engineering",
    "criticality": "HIGH",
    "information_access": "Restricted customer records",
    "agreement_terms": "Review signed security schedule annually.",
    "shared_responsibility": "Provider hosts; customer governs identities.",
    "exit_plan": "Export data and verify deletion before termination.",
    "review_date": "2026-10-01",
    "control_ref": "TP-002",
}
REVIEW = {
    "expected_revision": 1,
    "reviewed_on": "2026-09-01",
    "next_review": "2026-12-01",
    "result": "ACTION_REQUIRED",
    "note": "A source exception requires follow-up.",
    "evidence_ref": "EV-023",
    "action": "Obtain refreshed assurance evidence.",
    "action_owner": "Head of Legal & Compliance",
    "action_due": "2026-10-01",
}


def test_supplier_requires_review_date_and_real_links(client, auditor_client):
    assert auditor_client.put(BASE, json=SUPPLIER).status_code == 403
    assert client.put(BASE, json={**SUPPLIER, "review_date": None}).status_code == 422
    assert client.put(BASE, json={**SUPPLIER, "control_ref": "UNKNOWN"}).status_code == 422
    assert client.put(BASE, json={**SUPPLIER, "agreement_attachment_id": 999}).status_code == 422
    assert client.put(BASE, json=SUPPLIER).status_code == 200
    assert client.put(BASE, json=SUPPLIER).status_code == 422


def test_review_retains_snapshot_after_material_change(client):
    client.put(BASE, json=SUPPLIER)
    result = client.post(BASE + "/reviews", json=REVIEW)
    assert result.status_code == 201, result.text
    frozen = result.json()["snapshot"]
    assert (
        client.put(
            BASE, json={**SUPPLIER, "expected_revision": 2, "service": "Changed hosted service"}
        ).status_code
        == 200
    )
    assert client.get(BASE).json()["status"] == "DRAFT"
    assert client.get(BASE + "/reviews").json()[0]["snapshot"] == frozen
    review_id = result.json()["id"]
    assert (
        client.post(
            f"{BASE}/reviews/{review_id}/complete",
            json={
                "completed_on": "2026-09-03",
                "evidence_ref": "EV-023",
                "note": "Follow-up evidence reviewed.",
            },
        ).status_code
        == 200
    )
    assert client.get(BASE + "/reviews").json()[0]["snapshot"] == frozen


def test_review_cannot_approve_hints_or_unowned_actions(client):
    client.put(BASE, json={**SUPPLIER, "agreement_terms": "TODO AUTHOR:BENNY - inspect contract"})
    assert client.post(BASE + "/reviews", json=REVIEW).status_code == 422
    client.put(BASE, json={**SUPPLIER, "expected_revision": 1})
    assert (
        client.post(
            BASE + "/reviews", json={**REVIEW, "expected_revision": 2, "action_due": None}
        ).status_code
        == 422
    )
    assert (
        client.post(
            BASE + "/reviews", json={**REVIEW, "expected_revision": 2, "next_review": "2026-08-01"}
        ).status_code
        == 422
    )


def test_supplier_dependency_cycle_is_refused(client):
    client.put(BASE, json=SUPPLIER)
    client.put("/suppliers/SUP-OTHER", json={**SUPPLIER, "dependency_ref": "SUP-TEST"})
    assert (
        client.put(
            BASE, json={**SUPPLIER, "dependency_ref": "SUP-OTHER", "expected_revision": 1}
        ).status_code
        == 422
    )


def test_database_requires_review_date(client, db_session):
    client.put(BASE, json=SUPPLIER)
    row = db_session.scalar(select(Supplier).where(Supplier.supplier_ref == "SUP-TEST"))
    with pytest.raises(IntegrityError), db_session.begin_nested():
        row.review_date = None
        db_session.flush()


def test_sample_is_not_an_approved_supplier(client):
    row = client.get("/suppliers/SUP-001").json()
    assert row["status"] == "DRAFT" and row["criticality"] == "UNASSESSED"
    assert "TODO AUTHOR:BENNY" in row["agreement_terms"]
