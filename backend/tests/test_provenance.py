"""Mutation-based proofs: the seed cascade alone cannot establish this behavior."""
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models.risk import RiskControl, Risk, Control
from app.models.audit import ControlTest
from app.models.provenance import Reassessment
from test_testing_api import BASE_TEST

def control(client, risk, ref):
    return next(c for c in client.get(f"/risks/{risk}").json()["controls"] if c["control_id"] == ref)

def test_seed_links_distinguish_workforce_and_privileged_populations(client):
    assert control(client, "RISK-001", "AC-002")["supporting_test_ref"] == "TEST-002"
    assert control(client, "RISK-004", "AC-002")["supporting_test_ref"] == "TEST-003"
    assert control(client, "RISK-004", "AC-002")["test_population"]
    missing = control(client, "RISK-003", "TP-002")
    assert missing["proof_state"] == "MISSING"
    assert "TODO AUTHOR:BENNY" in missing["proof_note"]

def test_binding_refuses_other_control_and_unsupported_conclusion(client):
    path = "/risks/RISK-001/controls/AC-002/proof"
    assert client.put(path, json={"test_ref":"TEST-001", "note":"Same assessment population."}).status_code == 422
    assert client.put(path, json={"test_ref":"TEST-003", "note":"Same assessment population."}).status_code == 422
    assert client.put(path, json={"test_ref":"TEST-002", "note":"Workforce population as recorded in ADR-008."}).status_code == 200

def test_database_rejects_test_for_another_control(db_session):
    link = db_session.scalar(select(RiskControl).join(Risk).join(Control).where(Risk.risk_ref == "RISK-001", Control.control_id == "AC-002"))
    test = db_session.scalar(select(ControlTest).where(ControlTest.test_ref == "TEST-008"))
    with pytest.raises(IntegrityError), db_session.begin_nested():
        link.supporting_test_id = test.id
        db_session.flush()

def test_failed_write_queues_cascade_without_inventing_decisions(client):
    before = client.get("/risks/RISK-008").json()["residual"]
    result = client.post("/control-tests", json={**BASE_TEST, "control_id":"DP-005", "conclusion":"FAIL", "exceptions_count":2, "exception_details":"Masking absent in two stores."})
    assert result.status_code == 201, result.text
    queue = client.get("/reassessments").json()
    refs = {(q["record_type"],q["record_ref"]) for q in queue}
    assert {("RISK","RISK-008"), ("RISK","RISK-018"), ("SOA","A.8.11"), ("DPIA","DPIA-001"), ("ROPA","ROPA-003")} <= refs
    assert client.get("/risks/RISK-008").json()["residual"] == before
    assert control(client,"RISK-008","DP-005")["proof_state"] == "REASSESSMENT_REQUIRED"
    item = next(q for q in queue if q["record_ref"] == "RISK-008")
    path = f"/reassessments/{item['id']}/resolve"
    assert client.post(path, json={"evidence_ref":"EV-001","resolution":" "}).status_code == 422
    assert client.post(path, json={"evidence_ref":"EV-001","resolution":"The author reviewed the scope and retained the current decision."}).status_code == 200

def test_older_clean_test_does_not_erase_newer_failure(client):
    failed = client.post("/control-tests", json={**BASE_TEST,"conclusion":"FAIL","exceptions_count":3,"exception_details":"Three exceptions."})
    assert failed.status_code == 201
    clean = client.post("/control-tests", json={**BASE_TEST,"test_date":"2026-07-10"})
    assert clean.status_code == 201
    row = next(c for c in client.get("/internal-controls").json() if c["control_id"] == "AC-006")
    assert row["operating_effectiveness"] == "INEFFECTIVE"
    assert row["last_tested"] == "2026-08-10"

def test_supersession_requires_same_population_and_retains_history(client):
    original = client.get("/control-tests/TEST-003").json()
    # A different population's clean pass cannot erase privileged exceptions.
    assert client.post("/control-tests/TEST-003/disposition", json={"replacement_ref":"TEST-002","reason":"Replaced."}).status_code == 422
    result = client.post("/control-tests", json={**BASE_TEST,"control_id":"AC-002","population_description":original["population_description"],"test_date":"2026-08-20","review_date":"2026-08-21"})
    assert result.status_code == 201, result.text
    response = client.post("/control-tests/TEST-003/disposition", json={"replacement_ref":result.json()["test_ref"],"reason":"Reviewed retest of the same privileged population."})
    assert response.status_code == 201, response.text
    assert client.get("/control-tests/TEST-003").status_code == 200
    assert control(client,"RISK-004","AC-002")["proof_state"] == "REASSESSMENT_REQUIRED"

def test_withdrawn_workpaper_cannot_be_bound_again(client):
    assert client.post("/control-tests/TEST-002/disposition", json={"reason":"Author withdrew the workpaper after identifying a collection error."}).status_code == 201
    assert client.put("/risks/RISK-001/controls/AC-002/proof", json={"test_ref":"TEST-002","note":"Use workforce test."}).status_code == 422

def test_readonly_auditor_cannot_bind_or_dispose(auditor_client):
    assert auditor_client.put("/risks/RISK-001/controls/AC-002/proof",json={"test_ref":"TEST-002","note":"Workforce scope."}).status_code == 403
    assert auditor_client.post("/control-tests/TEST-002/disposition",json={"reason":"Withdraw."}).status_code == 403
    assert auditor_client.get("/reassessments").status_code == 200

def test_database_refuses_resolution_without_evidence(db_session):
    test = db_session.scalar(select(ControlTest).where(ControlTest.test_ref == "TEST-008"))
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(Reassessment(trigger_test_id=test.id,record_type="RISK",record_ref="RISK-008",owner="DPO",reason="Review adverse test",status="RESOLVED"))
        db_session.flush()
