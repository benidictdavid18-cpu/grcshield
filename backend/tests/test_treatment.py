from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.acceptance import AcceptanceAuthority
from app.models.risk import Risk
from app.models.treatment import TreatmentMilestone, TreatmentPlan
from app.models.user import User
from tests.test_migrations import migrated  # noqa: F401 - real migrated database fixture

PLAN={"risk_ref":"RISK-004","title":"Privileged MFA delivery","owner":"Chief Technology Officer","resources":"Author commits one engineer and the approved change window.","rationale":"Complete the privileged MFA work before risk review.","control_refs":["AC-002"]}
MILE={"title":"Deliver privileged MFA coverage","owner":"Head of Engineering","due_date":"2026-09-20","remediation_ref":"REM-001"}

def grant(db):
    user=db.scalar(select(User).where(User.username=="isms.manager"))
    db.add(AcceptanceAuthority(user_id=user.id,business_role="Chief Technology Officer",grant_reason="Fixture approval authority",granted_by="fixture.admin",expires_on=date(2027,1,1)))
    db.flush()

def setup(client):
    response=client.put("/treatment-plans/TPL-TEST",json=PLAN)
    assert response.status_code==200,response.text
    first=client.put("/treatment-plans/TPL-TEST/milestones/M1",json=MILE)
    assert first.status_code==200,first.text
    return first.json()["id"]

def test_seed_plan_retains_scheduling_conflict_as_author_task(client):
    row=client.get("/treatment-plans/TPL-004-DRAFT").json()
    assert row["status"]=="DRAFT"
    assert "TODO AUTHOR:BENNY" in row["resources"]
    assert row["review_deadline"]=="2026-09-28"

def test_milestone_after_risk_review_is_refused(client):
    setup(client)
    result=client.put("/treatment-plans/TPL-TEST/milestones/LATE",json={**MILE,"due_date":"2026-10-01"})
    assert result.status_code==422 and "next review" in result.text

def test_dependency_cycles_are_refused(client):
    setup(client)
    result=client.put("/treatment-plans/TPL-TEST/milestones/M2",json={**MILE,"dependency_ref":"M1"})
    assert result.status_code==200
    assert client.put("/treatment-plans/TPL-TEST/milestones/M1",json={**MILE,"dependency_ref":"M2"}).status_code==422

def test_plan_approval_requires_actual_business_authority(client,db_session):
    setup(client)
    path="/treatment-plans/TPL-TEST/approve"
    assert client.post(path,json={"note":"I approve"}).status_code==403
    grant(db_session)
    response=client.post(path,json={"note":"Business owner commits the recorded resources and schedule."})
    assert response.status_code==200,response.text
    assert response.json()["approved_snapshot"]["milestones"]
    assert client.put("/treatment-plans/TPL-TEST/milestones/M1",json=MILE).status_code==422

def test_completion_requires_dependencies_and_does_not_change_residual(client,db_session):
    before=client.get("/risks/RISK-004").json()["residual"]
    first=setup(client)
    second=client.put("/treatment-plans/TPL-TEST/milestones/M2",json={**MILE,"dependency_ref":"M1"}).json()["id"]
    grant(db_session)
    assert client.post("/treatment-plans/TPL-TEST/approve",json={"note":"Approved resources and delivery."}).status_code==200
    payload={"evidence_ref":"EV-002","note":"The author evaluated the recorded delivery evidence."}
    assert client.post(f"/treatment-milestones/{second}/complete",json=payload).status_code==422
    assert client.post("/treatment-plans/TPL-TEST/close",json=payload).status_code==422
    assert client.post(f"/treatment-milestones/{first}/complete",json=payload).status_code==200
    assert client.post(f"/treatment-milestones/{second}/complete",json=payload).status_code==200
    result=client.post("/treatment-plans/TPL-TEST/close",json=payload)
    assert result.status_code==200,result.text
    assert result.json()["status"]=="COMPLETED"
    assert client.get("/risks/RISK-004").json()["residual"]==before

def test_database_refuses_milestone_after_its_plan_deadline(db_session):
    plan=db_session.scalar(select(TreatmentPlan))
    with pytest.raises(IntegrityError),db_session.begin_nested():
        db_session.add(TreatmentMilestone(plan_id=plan.id,review_deadline=plan.review_deadline,milestone_ref="BAD",title="Too late",owner="Owner",due_date=date(2027,1,1),status="OPEN"))
        db_session.flush()

def test_migrated_database_enforces_cross_record_risk_review(migrated, db_session):  # noqa: F811
    seed=db_session.scalar(select(Risk).where(Risk.risk_ref=="RISK-004"))
    values={c.name:getattr(seed,c.name) for c in Risk.__table__.columns}
    with Session(migrated) as db:
        db.execute(Risk.__table__.insert().values(**values))
        db.commit()
        with pytest.raises(IntegrityError),db.begin_nested():
            db.add(TreatmentPlan(plan_ref="LATE",risk_id=seed.id,title="Late plan",owner="Owner",resources="Resources",rationale="Reason",review_deadline=date(2027,1,1),status="DRAFT",revision=1))
            db.flush()
        db.add(TreatmentPlan(plan_ref="VALID",risk_id=seed.id,title="Valid plan",owner="Owner",resources="Resources",rationale="Reason",review_deadline=seed.next_review,status="DRAFT",revision=1))
        db.commit()
        with pytest.raises(IntegrityError),db.begin_nested():
            db.execute(Risk.__table__.update().where(Risk.id==seed.id).values(next_review=date(2026,9,1)))

def test_auditor_cannot_change_treatment(auditor_client):
    assert auditor_client.put("/treatment-plans/TPL-TEST",json=PLAN).status_code==403
