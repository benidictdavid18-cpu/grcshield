from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import current_user
from app.db.session import get_db
from app.models.user import User
from app.models.privacy import RiskException
from app.models.acceptance import AcceptanceAuthority, AcceptanceDecision
from app.schemas.acceptance import AuthorityIn, DecisionIn
from app.services import acceptance, audit_trail
from app.api.routes.provenance import require, invoke
router = APIRouter(tags=["acceptance decisions"])

def authorized(fn,*args):
    try: return invoke(fn,*args)
    except PermissionError as e: raise HTTPException(403,str(e)) from e

@router.get("/acceptance-authorities")
def authorities(db: Session = Depends(get_db)):
    return [dict(id=x.id,user_id=x.user_id,business_role=x.business_role,expires_on=x.expires_on,granted_by=x.granted_by,disclaimer="Sample / Portfolio Assessment") for x in db.scalars(select(AcceptanceAuthority))]

@router.post("/acceptance-authorities",status_code=201)
def grant(payload: AuthorityIn,db: Session = Depends(get_db),actor: User = Depends(current_user)):
    user = require(db.scalar(select(User).where(User.username == payload.username)))
    row = authorized(acceptance.grant,db,actor,user,payload.business_role.strip(),payload.expires_on,payload.grant_reason)
    db.commit()
    return {"id":row.id,"business_role":row.business_role,"expires_on":row.expires_on,"disclaimer":"Sample / Portfolio Assessment"}

@router.get("/risk-exceptions/{exception_ref}/decisions")
def history(exception_ref: str,db: Session = Depends(get_db)):
    row = require(db.scalar(select(RiskException).where(RiskException.exception_ref == exception_ref)))
    return [{**audit_trail.snapshot(d,("id","decision","source","actor","business_role","note","approval_date","expiry_date","created_at")),"disclaimer":"Sample / Portfolio Assessment"} for d in db.scalars(select(AcceptanceDecision).where(AcceptanceDecision.exception_id == row.id).order_by(AcceptanceDecision.id))]

@router.post("/risk-exceptions/{exception_ref}/decisions",status_code=201)
def decide(exception_ref: str,payload: DecisionIn,db: Session = Depends(get_db),actor: User = Depends(current_user)):
    row = require(db.scalar(select(RiskException).where(RiskException.exception_ref == exception_ref).with_for_update()))
    signed = authorized(acceptance.decide,db,row,actor,payload.decision,payload.note,payload.expiry_date)
    db.commit()
    return {"decision_id":signed.id,"effective_state":acceptance.effective_state(row,acceptance.clock.today()),"disclaimer":"Sample / Portfolio Assessment"}
