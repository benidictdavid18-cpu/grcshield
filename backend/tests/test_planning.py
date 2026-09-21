from datetime import date
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models.planning import ISMSPlan
from app.models.context import ContextEntry
from app.models.acceptance import AcceptanceAuthority
from app.models.user import User

PLAN={"kind":"OBJECTIVE","title":"A measurable security objective","owner":"Head of Engineering","resources":"One engineer and the approved review time.","rationale":"Address the reviewed customer requirement.","context_ref":"CTX-002","risk_ref":"RISK-004","kri_ref":"KRI-001","due_date":"2026-12-31","measure_definition":"Percentage of the explicitly scoped privileged population with MFA.","target_value":100,"direction":"HIGHER_IS_BETTER"}

def authorize(db):
    user=db.scalar(select(User).where(User.username=="isms.manager"))
    db.add(AcceptanceAuthority(user_id=user.id,business_role="Chief Executive Officer",grant_reason="Fixture management authority",granted_by="fixture.admin",expires_on=date(2027,1,1)))
    context=db.scalar(select(ContextEntry).where(ContextEntry.context_ref=="CTX-002"))
    context.owner="Head of Legal & Compliance"
    context.relevance="RELEVANT"
    context.decision_note="Reviewed customer security requirements drive this objective."
    context.status="REVIEWED"
    context.reviewed_by="isms.manager"
    context.reviewed_on=date(2026,9,4)
    db.flush()

def test_sample_does_not_invent_objective_targets(client):
    row=client.get("/isms/plans/OBJ-001").json()
    assert row["status"]=="DRAFT" and row["target_value"] is None and row["due_date"] is None
    assert "TODO AUTHOR:BENNY" in row["resources"]
    guidance=client.get("/documents/DOC-RISK-SCALE/revisions").json()[0]
    assert guidance["status"]=="DRAFT" and "TODO AUTHOR:BENNY" in guidance["content"]

def test_authority_reviewed_context_and_target_are_required(client,db_session):
    assert client.put("/isms/plans/OBJ-TEST",json={**PLAN,"target_value":None}).status_code==200
    assert client.post("/isms/plans/OBJ-TEST/approve",json={"note":"Approve"}).status_code==403
    authorize(db_session)
    assert client.post("/isms/plans/OBJ-TEST/approve",json={"note":"Approve"}).status_code==422

def test_evaluations_retain_observations_without_asserting_success(client,db_session):
    authorize(db_session)
    assert client.put("/isms/plans/OBJ-TEST",json=PLAN).status_code==200
    response=client.post("/isms/plans/OBJ-TEST/approve",json={"note":"Leadership commits the stated target, resources and date."})
    assert response.status_code==200,response.text
    snapshot=response.json()["approved_snapshot"]
    payload={"observed_on":"2026-09-04","observed_value":75,"evidence_ref":"EV-002","evaluation_note":"Observed value is below the agreed target; further work is required."}
    assert client.post("/isms/plans/OBJ-TEST/evaluations",json=payload).status_code==201
    assert client.post("/isms/plans/OBJ-TEST/evaluations",json={**payload,"observed_value":80,"evaluation_note":"A second observation remains below target."}).status_code==201
    assert len(client.get("/isms/plans/OBJ-TEST/evaluations").json())==2
    row=client.get("/isms/plans/OBJ-TEST").json()
    assert row["status"]=="EVALUATED" and row["approved_snapshot"]==snapshot
    assert client.put("/isms/plans/OBJ-TEST",json={**PLAN,"expected_revision":1}).status_code==422

def test_change_requires_impact_rollback_implementation_then_evaluation(client,db_session):
    authorize(db_session)
    payload={**PLAN,"kind":"CHANGE","title":"Controlled publication change","impact_assessment":"Review changed responsibilities and training before publication.","rollback_plan":"Retain the prior published revision and restore it through a new authorized publication."}
    assert client.put("/isms/plans/CHG-TEST",json=payload).status_code==200
    assert client.post("/isms/plans/CHG-TEST/approve",json={"note":"Approve the assessed change and resources."}).status_code==200
    evaluation={"observed_on":"2026-09-04","evidence_ref":"EV-029","evaluation_note":"The author evaluated the changed publication process."}
    assert client.post("/isms/plans/CHG-TEST/evaluations",json=evaluation).status_code==422
    result=client.post("/isms/plans/CHG-TEST/implement",json={"implemented_on":"2026-09-04","evidence_ref":"EV-029","note":"The author records implementation against the retained evidence."})
    assert result.status_code==200,result.text
    assert client.post("/isms/plans/CHG-TEST/evaluations",json=evaluation).status_code==201

def test_nonexistent_sources_and_future_observations_are_refused(client,db_session):
    assert client.put("/isms/plans/OBJ-BAD",json={**PLAN,"context_ref":"CTX-MISSING"}).status_code==422
    authorize(db_session)
    client.put("/isms/plans/OBJ-TEST",json=PLAN)
    client.post("/isms/plans/OBJ-TEST/approve",json={"note":"Approved."})
    assert client.post("/isms/plans/OBJ-TEST/evaluations",json={"observed_on":"2027-01-01","observed_value":100,"evidence_ref":"EV-002","evaluation_note":"An observation cannot be from the future."}).status_code==422

def test_database_refuses_uncommitted_plan_as_approved(db_session):
    row=db_session.scalar(select(ISMSPlan).where(ISMSPlan.plan_ref=="OBJ-001"))
    with pytest.raises(IntegrityError),db_session.begin_nested():
        row.status="APPROVED"
        db_session.flush()

def test_auditor_cannot_commit_objectives(auditor_client):
    assert auditor_client.put("/isms/plans/OBJ-TEST",json=PLAN).status_code==403
