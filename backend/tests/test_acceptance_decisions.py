from datetime import date
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models.acceptance import AcceptanceAuthority, AcceptanceDecision
from app.models.privacy import RiskException
from app.models.user import User
from app.services import acceptance
from tests.test_registers_api import VALID_EXCEPTION

def grant_for_test(db):
    user = db.scalar(select(User).where(User.username == "isms.manager"))
    db.add(AcceptanceAuthority(user_id=user.id,business_role="Chief Technology Officer",grant_reason="Test fixture: designated business approver",granted_by="fixture.admin",expires_on=date(2027,1,1)))
    db.flush()

def test_imported_approval_is_explicitly_unverified_and_cannot_cover(client):
    result = client.post("/risk-exceptions",json={**VALID_EXCEPTION,"risk_ref":"RISK-004"})
    assert result.status_code == 201
    body = result.json()
    assert body["state"] == "APPROVED"  # retained recorded-claim contract
    assert body["effective_state"] == "UNVERIFIED"
    assert body["approval_verified"] is False
    assert "RISK-004" in client.get("/risk-exceptions/summary").json()["uncovered_breaches"]

def test_pending_near_expiry_never_counts_as_approval(client):
    result = client.post("/risk-exceptions",json={**VALID_EXCEPTION,"risk_ref":"RISK-004","status":"PENDING","approval_date":None,"expiry_date":"2026-09-05"})
    assert result.status_code == 201
    assert result.json()["effective_state"] == result.json()["state"] == "PENDING"
    summary = client.get("/risk-exceptions/summary").json()
    assert "RISK-004" in summary["uncovered_breaches"]
    assert summary["expiring_soon"] == 1

def test_role_string_does_not_authorize_a_decision(client):
    ref = client.post("/risk-exceptions",json=VALID_EXCEPTION).json()["exception_ref"]
    assert client.post(f"/risk-exceptions/{ref}/decisions",json={"decision":"APPROVED","note":"I approve."}).status_code == 403
    assert client.post("/acceptance-authorities",json={"username":"isms.manager","business_role":"Chief Technology Officer","expires_on":"2027-01-01","grant_reason":"Self appointed"}).status_code == 403

def test_authorized_approval_renewal_and_withdrawal_retain_history(client,db_session):
    grant_for_test(db_session)
    ref = client.post("/risk-exceptions",json={**VALID_EXCEPTION,"status":"PENDING","approval_date":None}).json()["exception_ref"]
    path=f"/risk-exceptions/{ref}/decisions"
    assert client.post(path,json={"decision":"APPROVED","note":"Authorized business decision."}).status_code == 201
    assert client.post(path,json={"decision":"APPROVED","note":"Renewed following review.","expiry_date":"2027-03-01"}).status_code == 201
    assert client.post(path,json={"decision":"WITHDRAWN","note":"Treatment now required."}).status_code == 201
    history=client.get(path).json()
    assert [x["decision"] for x in history] == ["APPROVED","APPROVED","WITHDRAWN"]
    assert history[0]["expiry_date"] == "2026-12-31"
    assert all(x["actor"] == "isms.manager" for x in history)

def test_signed_record_change_invalidates_coverage(db_session):
    row=db_session.scalar(select(RiskException).where(RiskException.exception_ref == "EXC-002"))
    assert acceptance.covers(row,date(2026,9,4))
    row.business_justification += " Altered after signature."
    assert not acceptance.covers(row,date(2026,9,4))

def test_expired_authority_cannot_sign(client,db_session):
    grant_for_test(db_session)
    db_session.scalar(select(AcceptanceAuthority)).expires_on=date(2026,9,3)
    db_session.flush()
    ref=client.post("/risk-exceptions",json=VALID_EXCEPTION).json()["exception_ref"]
    assert client.post(f"/risk-exceptions/{ref}/decisions",json={"decision":"APPROVED","note":"Approve."}).status_code == 403

def test_database_refuses_approval_without_date(db_session):
    row=db_session.scalar(select(RiskException).where(RiskException.exception_ref == "EXC-001"))
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(AcceptanceDecision(exception_id=row.id,record_digest="0"*64,decision="APPROVED",source="AUTHENTICATED",actor="test",business_role=row.approver_role,note="Test approval",expiry_date=date(2027,1,1)))
        db_session.flush()

def test_seed_decisions_disclose_fictional_origin(client):
    history=client.get("/risk-exceptions/EXC-002/decisions").json()
    assert history[0]["source"] == "SAMPLE_AUTHORED"
    assert history[0]["actor"] == "Chief Executive Officer"
