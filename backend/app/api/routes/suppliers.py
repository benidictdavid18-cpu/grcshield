from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.api.routes.context import commit
from app.api.routes.provenance import invoke, require
from app.db.session import get_db
from app.models.suppliers import Supplier, SupplierReview
from app.models.user import User
from app.schemas.assurance import CompletionIn
from app.schemas.suppliers import ReviewIn, SupplierIn, SupplierOut
from app.services import suppliers
from app.services.assurance import snapshot

router = APIRouter(prefix="/suppliers", tags=["Supplier oversight"])


def find(db, ref):
    return require(
        db.scalar(select(Supplier).where(Supplier.supplier_ref == ref).with_for_update())
    )


@router.get("", response_model=list[SupplierOut])
def listing(db: Session = Depends(get_db)):
    return db.scalars(select(Supplier).order_by(Supplier.supplier_ref)).all()


@router.get("/{ref}", response_model=SupplierOut)
def detail(ref: str, db: Session = Depends(get_db)):
    return find(db, ref)


@router.put("/{ref}", response_model=SupplierOut)
def save(
    ref: str,
    payload: SupplierIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    row = invoke(suppliers.save, db, ref, payload, actor)
    commit(db)
    return row


@router.get("/{ref}/reviews")
def reviews(ref: str, db: Session = Depends(get_db)):
    row = find(db, ref)
    return [
        dict(snapshot(x), disclaimer="Sample / Portfolio Assessment")
        for x in db.scalars(
            select(SupplierReview)
            .where(SupplierReview.supplier_id == row.id)
            .order_by(SupplierReview.id)
        )
    ]


@router.post("/{ref}/reviews", status_code=201)
def review(
    ref: str, payload: ReviewIn, db: Session = Depends(get_db), actor: User = Depends(current_user)
):
    row = invoke(suppliers.review, db, find(db, ref), payload, actor)
    commit(db)
    return dict(snapshot(row), disclaimer="Sample / Portfolio Assessment")


@router.post("/{ref}/reviews/{review_id}/complete")
def complete(
    ref: str,
    review_id: int,
    payload: CompletionIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    supplier = find(db, ref)
    row = require(
        db.scalar(
            select(SupplierReview)
            .where(SupplierReview.id == review_id, SupplierReview.supplier_id == supplier.id)
            .with_for_update()
        )
    )
    invoke(suppliers.complete, db, row, payload, actor)
    commit(db)
    return dict(snapshot(row), disclaimer="Sample / Portfolio Assessment")
