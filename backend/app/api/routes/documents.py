from fastapi import APIRouter,Depends,HTTPException,Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import current_user
from app.db.session import get_db
from app.models.user import User
from app.models.document import ControlledDocument,DocumentRevision,DocumentAcknowledgement
from app.schemas.document import DocumentIn,DocumentOut,RevisionIn,RevisionOut
from app.schemas.context import ApprovalIn
from app.services import documents
from app.api.routes.provenance import require,invoke
from app.api.routes.context import commit
router=APIRouter(tags=["controlled documents"])

def get_document(db,ref): return require(db.scalar(select(ControlledDocument).where(ControlledDocument.document_ref==ref)))

@router.get("/documents",response_model=list[DocumentOut])
def documents_list(db: Session=Depends(get_db)):
    return db.scalars(select(ControlledDocument).order_by(ControlledDocument.document_ref)).all()

@router.put("/documents/{ref}",response_model=DocumentOut)
def save(ref: str,payload: DocumentIn,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=invoke(documents.save,db,ref,payload,actor)
    commit(db)
    return row

@router.get("/documents/{ref}/revisions",response_model=list[RevisionOut])
def revisions(ref: str,db: Session=Depends(get_db)):
    document=get_document(db,ref)
    return db.scalars(select(DocumentRevision).where(DocumentRevision.document_id==document.id).order_by(DocumentRevision.id.desc())).all()

@router.post("/documents/{ref}/revisions",response_model=RevisionOut,status_code=201)
def revision(ref: str,payload: RevisionIn,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=invoke(documents.create_revision,db,get_document(db,ref),payload,actor)
    commit(db)
    return row

@router.get("/document-revisions/{revision_id}/download")
def download(revision_id: int,db: Session=Depends(get_db)):
    row=require(db.get(DocumentRevision,revision_id))
    if documents.digest(row.content)!=row.content_digest:
        raise HTTPException(409,"Document integrity check failed; contact the document owner.")
    return Response("Sample / Portfolio Assessment\n\n"+row.content,media_type="text/plain",headers={"Content-Disposition":f'attachment; filename="document-revision-{revision_id}.txt"',"X-Content-Type-Options":"nosniff"})

@router.post("/document-revisions/{revision_id}/acknowledgements",status_code=201)
def acknowledge(revision_id: int,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=require(db.get(DocumentRevision,revision_id))
    item=invoke(documents.acknowledge,db,row,actor)
    commit(db)
    return {"revision_id":row.id,"username":item.username,"recorded_at":item.created_at,"disclaimer":"Sample / Portfolio Assessment"}

@router.get("/document-revisions/{revision_id}/acknowledgements")
def acknowledgements(revision_id: int,db: Session=Depends(get_db)):
    require(db.get(DocumentRevision,revision_id))
    return [{"username":x.username,"recorded_at":x.created_at,"disclaimer":"Sample / Portfolio Assessment"} for x in db.scalars(select(DocumentAcknowledgement).where(DocumentAcknowledgement.revision_id==revision_id))]

@router.post("/document-revisions/{revision_id}/{action}",response_model=RevisionOut)
def transition(revision_id: int,action: str,payload: ApprovalIn,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=require(db.scalar(select(DocumentRevision).where(DocumentRevision.id==revision_id).with_for_update()))
    invoke(documents.transition,db,row,action,payload.note,actor)
    commit(db)
    return row

