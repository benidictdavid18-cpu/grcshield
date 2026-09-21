from fastapi import APIRouter,Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import current_user
from app.db.session import get_db
from app.models.planning import ISMSPlan,PlanEvaluation
from app.models.user import User
from app.schemas.planning import ISMSPlanIn,ISMSPlanOut,EvaluationIn,EvaluationOut,ImplementationIn
from app.schemas.context import ApprovalIn
from app.services import planning
from app.api.routes.provenance import require
from app.api.routes.acceptance import authorized
from app.api.routes.context import commit
router=APIRouter(prefix="/isms/plans",tags=["ISMS objectives and changes"])
def load(db,ref): return require(db.scalar(select(ISMSPlan).where(ISMSPlan.plan_ref==ref).with_for_update()))

@router.get("",response_model=list[ISMSPlanOut])
def listing(db: Session=Depends(get_db)):
    return db.scalars(select(ISMSPlan).order_by(ISMSPlan.id)).all()

@router.get("/{ref}",response_model=ISMSPlanOut)
def detail(ref: str,db: Session=Depends(get_db)): return load(db,ref)

@router.put("/{ref}",response_model=ISMSPlanOut)
def save(ref: str,payload: ISMSPlanIn,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=authorized(planning.save,db,ref,payload,actor)
    commit(db)
    return row

@router.post("/{ref}/approve",response_model=ISMSPlanOut)
def approve(ref: str,payload: ApprovalIn,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=load(db,ref)
    authorized(planning.approve,db,row,payload.note,actor)
    commit(db)
    return row

@router.post("/{ref}/implement",response_model=ISMSPlanOut)
def implement(ref: str,payload: ImplementationIn,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=load(db,ref)
    authorized(planning.implement,db,row,payload,actor)
    commit(db)
    return row

@router.get("/{ref}/evaluations",response_model=list[EvaluationOut])
def evaluations(ref: str,db: Session=Depends(get_db)):
    row=load(db,ref)
    return db.scalars(select(PlanEvaluation).where(PlanEvaluation.plan_id==row.id).order_by(PlanEvaluation.observed_on,PlanEvaluation.id)).all()

@router.post("/{ref}/evaluations",response_model=EvaluationOut,status_code=201)
def evaluate(ref: str,payload: EvaluationIn,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    result=authorized(planning.evaluate,db,load(db,ref),payload,actor)
    commit(db)
    return result

@router.post("/{ref}/cancel",response_model=ISMSPlanOut)
def cancel(ref: str,payload: ApprovalIn,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=load(db,ref)
    authorized(planning.cancel,db,row,payload.note,actor)
    commit(db)
    return row
