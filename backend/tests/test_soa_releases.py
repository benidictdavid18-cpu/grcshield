from datetime import date
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models.acceptance import AcceptanceAuthority
from app.models.user import User
from app.models.soa_release import SoARelease
from app.models.soa import SoAEntry,RemediationStatus


def grant(db):
    user=db.scalar(select(User).where(User.username=="isms.manager"))
    db.add(AcceptanceAuthority(user_id=user.id,business_role="Chief Executive Officer",grant_reason="Explicit fixture authority for release workflow tests",granted_by="fixture.admin",expires_on=date(2027,1,1)))
    db.flush()

def create(client,version="release-test-1"):
    result=client.post("/soa-releases",json={"version":version,"change_note":"The author prepared this exact applicability snapshot for management review."})
    assert result.status_code==201,result.text
    return result.json()["id"]

def approve(client,ident,ack=True):
    return client.post(f"/soa-releases/{ident}/approve",json={"note":"Management approves applicability and has reviewed the disclosed evidence limitations.","acknowledge_evidence_limitations":ack})

def test_source_snapshot_is_not_an_invented_approval(client):
    rows=client.get("/soa-releases").json()
    assert rows[0]["status"]=="DRAFT" and rows[0]["entry_count"]==93
    assert "TODO AUTHOR:BENNY" in rows[0]["change_note"]
    assert client.get("/soa/overview").json()["approval_state"]=="WORKING_DRAFT"

def test_management_authority_and_evidence_acknowledgement_are_required(client,db_session):
    ident=create(client)
    assert approve(client,ident).status_code==403
    grant(db_session)
    result=approve(client,ident,False)
    assert result.status_code==422,result.text
    assert "evidence" in result.text.lower()

def test_approved_snapshot_survives_working_copy_edits_and_diff_explains_them(client,db_session):
    grant(db_session)
    ident=create(client)
    result=approve(client,ident)
    assert result.status_code==200,result.text
    before=result.json()["entries"]
    assert client.get("/soa/overview").json()["approval_state"]=="APPROVED"
    changed=client.patch("/soa/A.8.5",json={"owner":"Chief Technology Officer"})
    assert changed.status_code==200,changed.text
    assert client.get(f"/soa-releases/{ident}").json()["entries"]==before
    assert client.get("/soa/overview").json()["has_unreleased_changes"] is True
    changes=client.get(f"/soa-releases/{ident}/diff").json()["changes"]
    assert any(c["control_ref"]=="A.8.5" and "owner" in c["changed_fields"] for c in changes)
    assert approve(client,ident).status_code==422

def test_changed_working_copy_cannot_receive_stale_release_approval(client,db_session):
    grant(db_session)
    ident=create(client)
    client.patch("/soa/A.8.5",json={"owner":"Chief Technology Officer"})
    assert approve(client,ident).status_code==422

def test_approved_scope_drives_crosswalk_without_deleting_mapping_history(client,db_session):
    grant(db_session)
    result=client.patch("/soa/A.8.5",json={"applicable":False,"justification_exclusion":"Sample test decision: authentication responsibility moved outside the scoped service and is retained as a supplier obligation."})
    assert result.status_code==200,result.text
    ident=create(client)
    result=approve(client,ident)
    assert result.status_code==200,result.text
    control=client.get("/frameworks/ISO27001/controls/A.8.5")
    # Use the catalogue's canonical code supplied by the API, not an invented control ID.
    if control.status_code==404:
        frameworks=client.get("/frameworks").json()
        code=next(f["code"] for f in frameworks if f["scope_status"]=="PRIMARY")
        control=client.get(f"/frameworks/{code}/controls/A.8.5")
    assert control.json()["in_scope"] is False
    assert control.json()["mappings"]==[]

def test_completed_remediation_cannot_cover_an_open_gap(client,db_session):
    entry=db_session.scalar(select(SoAEntry).where(SoAEntry.control_ref=="A.8.5"))
    for item in entry.linked_remediation: item.status=RemediationStatus.COMPLETED
    db_session.flush()
    result=client.patch("/soa/A.8.5",json={"owner":"Chief Technology Officer"})
    assert result.status_code==422
    assert "active remediation" in result.text

def test_database_refuses_unsigned_approved_snapshot(db_session):
    row=db_session.scalar(select(SoARelease))
    with pytest.raises(IntegrityError),db_session.begin_nested():
        row.status="APPROVED"
        db_session.flush()

def test_readonly_auditor_cannot_prepare_release(auditor_client):
    assert auditor_client.post("/soa-releases",json={"version":"no","change_note":"Read-only attempt"}).status_code==403
