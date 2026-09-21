from datetime import date
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models.context import ContextEntry

PAYLOAD={"kind":"ISSUE","topic":"GENERAL","title":"A scoped issue","statement":"The author has identified an external dependency.","source":"Author review of the dependency inventory","owner":"Chief Operating Officer","review_date":"2027-01-31","relevance":"RELEVANT","decision_note":"The dependency affects the availability of the scoped service."}

def review_all(client):
    refs=[]
    for row in client.get("/isms/context").json():
        payload={**PAYLOAD,"kind":row["kind"],"topic":row["topic"],"expected_revision":row["revision"]}
        ref=row["context_ref"]
        assert client.put(f"/isms/context/{ref}",json=payload).status_code==200
        assert client.post(f"/isms/context/{ref}/review").status_code==200
        refs.append(ref)
    return refs

def scope_payload(refs):
    return dict(version="reviewed-1",statement="The authored ISMS scope.",interfaces="Supplier and customer interfaces defined by the author.",exclusions="The author has documented the organizational boundary.",owner="Chief Operating Officer",review_date="2027-01-31",context_refs=refs)

def test_sample_context_is_draft_and_does_not_invent_climate_relevance(client):
    rows=client.get("/isms/context").json()
    assert len(rows)==4
    climate=next(x for x in rows if x["topic"]=="CLIMATE")
    assert climate["relevance"]=="UNASSESSED"
    assert "TODO AUTHOR:BENNY" in climate["decision_note"]
    assert client.post(f"/isms/context/{climate['context_ref']}/review").status_code==422

def test_context_requires_owner_and_real_risk(client):
    assert client.put("/isms/context/CTX-NEW",json={**PAYLOAD,"owner":" "}).status_code==422
    assert client.put("/isms/context/CTX-NEW",json={**PAYLOAD,"risk_ref":"RISK-999"}).status_code==422
    assert client.put("/isms/context/CTX-NEW",json=PAYLOAD).status_code==200

def test_review_is_invalidated_by_edit_and_stale_revision_is_refused(client):
    client.put("/isms/context/CTX-NEW",json=PAYLOAD)
    assert client.post("/isms/context/CTX-NEW/review").json()["status"]=="REVIEWED"
    changed=client.put("/isms/context/CTX-NEW",json={**PAYLOAD,"expected_revision":1,"statement":"A changed dependency."})
    assert changed.json()["status"]=="DRAFT"
    assert client.put("/isms/context/CTX-NEW",json={**PAYLOAD,"expected_revision":1}).status_code==422

def test_scope_approval_freezes_reviewed_inputs_and_old_version_survives(client):
    refs=review_all(client)
    created=client.post("/isms/scope-revisions",json=scope_payload(refs))
    assert created.status_code==201,created.text
    ident=created.json()["id"]
    approved=client.post(f"/isms/scope-revisions/{ident}/approve",json={"note":"The author approves these boundaries and their reviewed inputs."})
    assert approved.status_code==200,approved.text
    frozen=approved.json()["context_snapshot"]
    assert client.post(f"/isms/scope-revisions/{ident}/approve",json={"note":"Approve again"}).status_code==422
    current=client.get(f"/isms/context/{refs[0]}").json()
    client.put(f"/isms/context/{refs[0]}",json={**PAYLOAD,"expected_revision":current["revision"]})
    scopes=client.get("/isms/scope-revisions").json()
    assert next(s for s in scopes if s["id"]==ident)["context_snapshot"]==frozen

def test_scope_cannot_approve_unreviewed_or_stale_inputs(client):
    refs=review_all(client)
    created=client.post("/isms/scope-revisions",json=scope_payload(refs)).json()
    current=client.get(f"/isms/context/{refs[0]}").json()
    client.put(f"/isms/context/{refs[0]}",json={**PAYLOAD,"expected_revision":current["revision"]})
    assert client.post(f"/isms/scope-revisions/{created['id']}/approve",json={"note":"Approve"}).status_code==422

def test_database_refuses_unreviewed_judgment_as_reviewed(db_session):
    row=db_session.scalar(select(ContextEntry).where(ContextEntry.topic=="CLIMATE"))
    with pytest.raises(IntegrityError),db_session.begin_nested():
        row.status="REVIEWED"
        row.reviewed_by="test"
        row.reviewed_on=date(2026,9,4)
        db_session.flush()

def test_auditor_cannot_author_context(auditor_client):
    assert auditor_client.put("/isms/context/CTX-NEW",json=PAYLOAD).status_code==403
    assert auditor_client.post("/isms/context/CTX-003/review").status_code==403
