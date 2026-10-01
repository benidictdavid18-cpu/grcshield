from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.api.routes.acceptance import authorized
from app.api.routes.context import commit
from app.api.routes.provenance import require
from app.db.session import get_db
from app.models.soa_release import SoARelease
from app.models.user import User
from app.schemas.soa_release import ReleaseApprovalIn, ReleaseIn, ReleaseOut
from app.services import soa_releases

router=APIRouter(prefix="/soa-releases",tags=["SoA releases"])

@router.get("",response_model=list[ReleaseOut])
def listing(db: Session=Depends(get_db)):
    return db.scalars(select(SoARelease).order_by(SoARelease.id.desc())).all()

@router.post("",response_model=ReleaseOut,status_code=201)
def create(payload: ReleaseIn,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=authorized(soa_releases.create,db,payload,actor)
    commit(db)
    return row

@router.get("/{release_id}",response_model=ReleaseOut)
def detail(release_id: int,db: Session=Depends(get_db)):
    return require(db.get(SoARelease,release_id))

@router.get("/{release_id}/diff")
def diff(release_id: int,other_id: int | None=None,db: Session=Depends(get_db)):
    row=require(db.get(SoARelease,release_id))
    other=require(db.get(SoARelease,other_id)).entries if other_id is not None else soa_releases.capture(db)[0]
    return {"from_version":row.version,"to":"working copy" if other_id is None else other_id,"changes":soa_releases.diff(row.entries,other),"disclaimer":"Sample / Portfolio Assessment"}

@router.post("/{release_id}/approve",response_model=ReleaseOut)
def approve(release_id: int,payload: ReleaseApprovalIn,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=require(db.scalar(select(SoARelease).where(SoARelease.id==release_id).with_for_update()))
    authorized(soa_releases.approve,db,row,payload,actor)
    commit(db)
    return row
