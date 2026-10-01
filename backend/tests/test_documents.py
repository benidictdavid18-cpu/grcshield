import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.document import DocumentRevision

META={"title":"Test policy","owner":"Head of Legal & Compliance","classification":"INTERNAL","source_kind":"INTERNAL","distribution":"Authenticated personnel through the policy register","review_date":"2027-04-30"}
CONTENT="Sample / Portfolio Assessment. Personnel follow the authored access approval procedure."

def draft(client,version="1"):
    assert client.put("/documents/DOC-TEST",json=META).status_code==200
    result=client.post("/documents/DOC-TEST/revisions",json={"version":version,"content":CONTENT,"change_note":"Author supplied the sample content."})
    assert result.status_code==201,result.text
    return result.json()["id"]

def action(client,ident,name,note="The author reviewed this revision and its intended distribution."):
    return client.post(f"/document-revisions/{ident}/{name}",json={"note":note})

def test_missing_sample_policy_cannot_be_approved(client):
    row=client.get("/documents/DOC-001/revisions").json()[0]
    assert "TODO AUTHOR:BENNY" in row["content"]
    assert action(client,row["id"],"approve").status_code==422

def test_external_document_requires_source(client):
    assert client.put("/documents/DOC-EXT",json={**META,"source_kind":"EXTERNAL"}).status_code==422
    assert client.put("/documents/DOC-EXT",json={**META,"source_kind":"EXTERNAL","external_source":"Controlled publisher release, revision 3"}).status_code==200

def test_publication_requires_approval_and_retains_old_content(client):
    first=draft(client)
    assert action(client,first,"publish").status_code==422
    assert action(client,first,"approve").status_code==200
    assert action(client,first,"publish").status_code==200
    second=draft(client,"2")
    assert action(client,second,"approve").status_code==200
    assert action(client,second,"publish").status_code==200
    rows=client.get("/documents/DOC-TEST/revisions").json()
    assert {x["id"]:x["status"] for x in rows}=={first:"SUPERSEDED",second:"PUBLISHED"}
    download=client.get(f"/document-revisions/{first}/download")
    assert download.status_code==200 and CONTENT in download.text
    assert "Sample / Portfolio Assessment" in download.text

def test_acknowledgement_names_actual_actor_and_revision(client):
    ident=draft(client)
    assert client.post(f"/document-revisions/{ident}/acknowledgements").status_code==422
    action(client,ident,"approve")
    action(client,ident,"publish")
    first=client.post(f"/document-revisions/{ident}/acknowledgements")
    second=client.post(f"/document-revisions/{ident}/acknowledgements")
    assert first.status_code==second.status_code==201
    rows=client.get(f"/document-revisions/{ident}/acknowledgements").json()
    assert len(rows)==1 and rows[0]["username"]=="isms.manager"

def test_content_tampering_blocks_download(client,db_session):
    ident=draft(client)
    row=db_session.get(DocumentRevision,ident)
    row.content="Changed outside the controlled write path."
    db_session.flush()
    assert client.get(f"/document-revisions/{ident}/download").status_code==409

def test_database_refuses_publication_without_approval(db_session):
    row=db_session.scalar(select(DocumentRevision))
    with pytest.raises(IntegrityError),db_session.begin_nested():
        row.status="PUBLISHED"
        db_session.flush()

def test_withdrawn_content_remains_retrievable_and_cannot_be_acknowledged(client):
    ident=draft(client)
    action(client,ident,"approve")
    action(client,ident,"publish")
    assert action(client,ident,"withdraw","Superseded requirement needs fresh author review.").status_code==200
    assert client.get(f"/document-revisions/{ident}/download").status_code==200
    assert client.post(f"/document-revisions/{ident}/acknowledgements").status_code==422

def test_auditor_can_read_but_cannot_publish(auditor_client):
    row=auditor_client.get("/documents/DOC-001/revisions").json()[0]
    assert auditor_client.get(f"/document-revisions/{row['id']}/download").status_code==200
    assert action(auditor_client,row["id"],"approve").status_code==403
