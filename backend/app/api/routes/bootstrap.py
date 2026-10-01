from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.bootstrap import SampleBootstrap
from app.schemas.bootstrap import BootstrapOut

router=APIRouter(tags=["system"])
@router.get("/sample-bootstrap",response_model=BootstrapOut)
def bootstrap_state(db: Session = Depends(get_db)):
    row=db.get(SampleBootstrap,1)
    return BootstrapOut(status=row.status if row else "UNTRACKED",reason=row.reason if row else "No startup initialization decision recorded yet.")
