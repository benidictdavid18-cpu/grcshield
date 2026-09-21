from urllib.parse import quote
from fastapi import APIRouter,Depends,HTTPException,Request,Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import current_user
from app.db.session import get_db
from app.models.attachment import EvidenceAttachment
from app.models.soa import Evidence
from app.models.user import User
from app.schemas.attachment import AttachmentIn,AttachmentOut,RetentionIn
from app.schemas.context import ApprovalIn
from app.services import attachments
from app.api.routes.provenance import require
from app.api.routes.acceptance import authorized
from app.api.routes.context import commit
router=APIRouter(tags=["evidence attachments"])

async def upload_body(request: Request):
    # Bound the actual stream, including chunked requests, before JSON/base64 allocation.
    body=bytearray()
    async for chunk in request.stream():
        if len(body)+len(chunk)>12*1024*1024:
            raise HTTPException(413,"Attachment request exceeds 12 MiB; file limit is 8 MiB.")
        body.extend(chunk)
    try: return AttachmentIn.model_validate_json(body)
    except ValidationError as e:
        raise HTTPException(422,[{"field":".".join(str(x) for x in err["loc"]),"message":err["msg"]} for err in e.errors()]) from e

@router.get("/evidence/{evidence_ref}/attachments",response_model=list[AttachmentOut])
def listing(evidence_ref: str,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    evidence=require(db.scalar(select(Evidence).where(Evidence.evidence_ref==evidence_ref)))
    rows=db.scalars(select(EvidenceAttachment).where(EvidenceAttachment.evidence_id==evidence.id).order_by(EvidenceAttachment.id.desc())).all()
    return [r for r in rows if attachments.can_read(r,actor)]

@router.post("/evidence/{evidence_ref}/attachments",response_model=AttachmentOut,status_code=201,openapi_extra={"requestBody":{"required":True,"content":{"application/json":{"schema":AttachmentIn.model_json_schema()}}}})
def upload(evidence_ref: str,payload: AttachmentIn=Depends(upload_body),db: Session=Depends(get_db),actor: User=Depends(current_user)):
    evidence=require(db.scalar(select(Evidence).where(Evidence.evidence_ref==evidence_ref)))
    row=authorized(attachments.store,db,evidence,payload,actor)
    commit(db)
    return row

@router.get("/evidence-attachments/{attachment_id}/download")
def download(attachment_id: int,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=require(db.get(EvidenceAttachment,attachment_id))
    data=authorized(attachments.download,db,row,actor)
    commit(db)
    return Response(data,media_type=row.content_type,headers={"Content-Disposition":f"attachment; filename=artifact-{row.id}; filename*=UTF-8''{quote(row.filename,safe='')}","X-Content-Type-Options":"nosniff","Content-Security-Policy":"default-src 'none'","X-GRC-Disclaimer":"Sample / Portfolio Assessment","X-Artifact-SHA256":row.sha256})

@router.patch("/evidence-attachments/{attachment_id}/retention",response_model=AttachmentOut)
def retention(attachment_id: int,payload: RetentionIn,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=require(db.scalar(select(EvidenceAttachment).where(EvidenceAttachment.id==attachment_id).with_for_update()))
    authorized(attachments.retention,db,row,payload,actor)
    commit(db)
    return row

@router.post("/evidence-attachments/{attachment_id}/purge",response_model=AttachmentOut)
def purge(attachment_id: int,payload: ApprovalIn,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=require(db.scalar(select(EvidenceAttachment).where(EvidenceAttachment.id==attachment_id).with_for_update()))
    authorized(attachments.purge,db,row,payload.note,actor)
    commit(db)
    return row
