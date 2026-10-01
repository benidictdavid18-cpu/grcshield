import base64
import hashlib
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.attachment import EvidenceAttachment
from app.models.user import Role, User

DATA=b"Sample / Portfolio Assessment. Attachment fixture for API verification."
PAYLOAD={"version":"test-1","filename":"sample.txt","content_type":"text/plain","content_base64":base64.b64encode(DATA).decode(),"source":"Ephemeral test fixture, not control effectiveness evidence","retention_until":"2026-09-04","retention_reason":"Retain through the test assessment date."}

def upload(client,**changes):
    return client.post("/evidence/EV-001/attachments",json={**PAYLOAD,**changes})

def admin(db):
    db.scalar(select(User).where(User.username=="isms.manager")).role=Role.ADMIN
    db.flush()

def test_exact_artifact_roundtrip_and_checksum(client):
    result=upload(client)
    assert result.status_code==201,result.text
    body=result.json()
    assert body["sha256"]==hashlib.sha256(DATA).hexdigest()
    assert "content_data" not in body and "content_base64" not in body
    response=client.get(f"/evidence-attachments/{body['id']}/download")
    assert response.status_code==200 and response.content==DATA
    assert response.headers["x-grc-disclaimer"]=="Sample / Portfolio Assessment"
    assert response.headers["content-disposition"].startswith("attachment;")
    assert len(client.get("/evidence/EV-001/attachments").json())==1

@pytest.mark.parametrize("filename",["../secret.txt","..\\secret.txt","bad\r\nheader.txt"])
def test_path_and_header_injection_names_are_refused(client,filename):
    assert upload(client,filename=filename).status_code==422

def test_type_mismatch_bad_encoding_and_duplicate_version_are_refused(client):
    assert upload(client,content_type="application/pdf").status_code==422
    assert upload(client,content_base64="%%%invalid").status_code==422
    assert upload(client).status_code==201
    assert upload(client).status_code==422

def test_actual_body_limit_applies_to_chunked_upload(client):
    chunks=(b" "*(1024*1024) for _ in range(13))
    response=client.post("/evidence/EV-001/attachments",content=chunks,headers={"content-type":"application/json"})
    assert response.status_code==413

def test_maintainer_only_attachment_is_hidden_from_auditor(client,db_session):
    result=upload(client,access_scope="MAINTAINERS")
    ident=result.json()["id"]
    user=db_session.scalar(select(User).where(User.username=="isms.manager"))
    user.role=Role.AUDITOR
    db_session.flush()
    assert client.get("/evidence/EV-001/attachments").json()==[]
    assert client.get(f"/evidence-attachments/{ident}/download").status_code==403

def test_legal_hold_and_unelapsed_retention_block_purge(client,db_session):
    admin(db_session)
    held=upload(client,legal_hold=True).json()["id"]
    future=upload(client,version="test-2",retention_until="2027-01-01").json()["id"]
    for ident in (held,future):
        assert client.post(f"/evidence-attachments/{ident}/purge",json={"note":"End of retention"}).status_code==422

def test_elapsed_retention_purge_retains_metadata_and_requires_admin(client,db_session):
    ident=upload(client).json()["id"]
    path=f"/evidence-attachments/{ident}/purge"
    assert client.post(path,json={"note":"Test retention elapsed."}).status_code==403
    admin(db_session)
    result=client.post(path,json={"note":"Test retention elapsed."})
    assert result.status_code==200,result.text
    assert result.json()["sha256"]==hashlib.sha256(DATA).hexdigest()
    assert client.get(f"/evidence-attachments/{ident}/download").status_code==422
    assert db_session.get(EvidenceAttachment,ident).content_data is None

def test_database_refuses_early_purge(client,db_session):
    ident=upload(client,retention_until="2027-01-01").json()["id"]
    row=db_session.get(EvidenceAttachment,ident)
    with pytest.raises(IntegrityError),db_session.begin_nested():
        row.content_data=None
        row.purged_on=date(2026,9,4)
        row.purged_by="fixture"
        row.purge_reason="Attempted early purge"
        db_session.flush()

def test_sample_has_no_fabricated_binary_evidence(client):
    assert client.get("/evidence/EV-029/attachments").json()==[]
