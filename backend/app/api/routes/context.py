from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.api.deps import current_user
from app.db.session import get_db
from app.models.context import ContextEntry,ScopeRevision
from app.models.user import User
from app.schemas.context import ContextIn,ContextOut,ScopeIn,ScopeOut,ApprovalIn
from app.services import context
from app.api.routes.provenance import require,invoke
router=APIRouter(prefix="/isms",tags=["ISMS context"])

def commit(db):
    try: db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(409,"A concurrent write used this reference; reload and retry.") from e

@router.get("/context",response_model=list[ContextOut])
def entries(db: Session=Depends(get_db)):
    return db.scalars(select(ContextEntry).order_by(ContextEntry.context_ref)).all()

@router.get("/context/{ref}",response_model=ContextOut)
def entry(ref: str,db: Session=Depends(get_db)):
    return require(db.scalar(select(ContextEntry).where(ContextEntry.context_ref==ref)))

@router.put("/context/{ref}",response_model=ContextOut)
def save(ref: str,payload: ContextIn,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=invoke(context.save_context,db,ref,payload,actor)
    commit(db)
    return row

@router.post("/context/{ref}/review",response_model=ContextOut)
def review(ref: str,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=require(db.scalar(select(ContextEntry).where(ContextEntry.context_ref==ref).with_for_update()))
    invoke(context.review_context,db,row,actor)
    commit(db)
    return row

@router.get("/scope-revisions",response_model=list[ScopeOut])
def scopes(db: Session=Depends(get_db)):
    return db.scalars(select(ScopeRevision).order_by(ScopeRevision.id.desc())).all()

@router.post("/scope-revisions",response_model=ScopeOut,status_code=201)
def scope(payload: ScopeIn,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=invoke(context.create_scope,db,payload,actor)
    commit(db)
    return row

@router.post("/scope-revisions/{scope_id}/approve",response_model=ScopeOut)
def approve(scope_id: int,payload: ApprovalIn,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=require(db.scalar(select(ScopeRevision).where(ScopeRevision.id==scope_id).with_for_update()))
    invoke(context.approve_scope,db,row,payload.note,actor)
    commit(db)
    return row
