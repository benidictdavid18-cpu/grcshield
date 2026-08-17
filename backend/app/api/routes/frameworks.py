from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.framework import ControlMapping, Framework, FrameworkControl
from app.schemas.framework import (
    ControlDetailOut,
    ControlOut,
    FrameworkDetailOut,
    FrameworkOut,
    GroupSummary,
    MappedCriterion,
)

router = APIRouter(prefix="/frameworks", tags=["frameworks"])


def _control_counts(db: Session) -> dict[int, int]:
    rows = db.execute(
        select(FrameworkControl.framework_id, func.count(FrameworkControl.id)).group_by(
            FrameworkControl.framework_id
        )
    ).all()
    return {framework_id: count for framework_id, count in rows}


@router.get("", response_model=list[FrameworkOut])
def list_frameworks(db: Session = Depends(get_db)) -> list[FrameworkOut]:
    frameworks = db.scalars(select(Framework).order_by(Framework.sort_order)).all()
    counts = _control_counts(db)
    return [
        FrameworkOut(
            id=f.id,
            code=f.code,
            name=f.name,
            version=f.version,
            publisher=f.publisher,
            scope_status=f.scope_status,
            scope_note=f.scope_note,
            control_count=counts.get(f.id, 0),
        )
        for f in frameworks
    ]


@router.get("/{code}", response_model=FrameworkDetailOut)
def get_framework(code: str, db: Session = Depends(get_db)) -> FrameworkDetailOut:
    framework = db.scalar(select(Framework).where(Framework.code == code.upper()))
    if framework is None:
        raise HTTPException(status_code=404, detail=f"Unknown framework '{code}'")

    rows = db.execute(
        select(
            FrameworkControl.group_ref,
            FrameworkControl.group_title,
            func.count(FrameworkControl.id),
            func.count(FrameworkControl.id).filter(FrameworkControl.in_scope.is_(True)),
            func.min(FrameworkControl.sort_order),
        )
        .where(FrameworkControl.framework_id == framework.id)
        .group_by(FrameworkControl.group_ref, FrameworkControl.group_title)
        .order_by(func.min(FrameworkControl.sort_order))
    ).all()

    groups = [
        GroupSummary(
            group_ref=group_ref,
            group_title=group_title,
            total=total,
            in_scope=in_scope,
            out_of_scope=total - in_scope,
        )
        for group_ref, group_title, total, in_scope, _ in rows
    ]

    return FrameworkDetailOut(
        id=framework.id,
        code=framework.code,
        name=framework.name,
        version=framework.version,
        publisher=framework.publisher,
        scope_status=framework.scope_status,
        scope_note=framework.scope_note,
        control_count=sum(g.total for g in groups),
        groups=groups,
    )


@router.get("/{code}/controls", response_model=list[ControlOut])
def list_controls(
    code: str,
    group_ref: str | None = Query(default=None, description="Filter to one theme or criteria group"),
    in_scope: bool | None = Query(default=None),
    q: str | None = Query(default=None, description="Substring match on reference or title"),
    db: Session = Depends(get_db),
) -> list[ControlOut]:
    framework = db.scalar(select(Framework).where(Framework.code == code.upper()))
    if framework is None:
        raise HTTPException(status_code=404, detail=f"Unknown framework '{code}'")

    stmt = select(FrameworkControl).where(FrameworkControl.framework_id == framework.id)
    if group_ref:
        stmt = stmt.where(FrameworkControl.group_ref == group_ref)
    if in_scope is not None:
        stmt = stmt.where(FrameworkControl.in_scope.is_(in_scope))
    if q:
        needle = f"%{q.lower()}%"
        stmt = stmt.where(
            func.lower(FrameworkControl.control_ref).like(needle)
            | func.lower(FrameworkControl.title).like(needle)
        )

    controls = db.scalars(stmt.order_by(FrameworkControl.sort_order)).all()
    return [ControlOut.model_validate(c) for c in controls]


@router.get("/{code}/controls/{control_ref}", response_model=ControlDetailOut)
def get_control(code: str, control_ref: str, db: Session = Depends(get_db)) -> ControlDetailOut:
    control = db.scalar(
        select(FrameworkControl)
        .join(Framework)
        .where(Framework.code == code.upper(), FrameworkControl.control_ref == control_ref)
        .options(selectinload(FrameworkControl.framework))
    )
    if control is None:
        raise HTTPException(status_code=404, detail=f"Unknown control '{control_ref}' in '{code}'")

    mapping_rows = db.execute(
        select(ControlMapping, FrameworkControl)
        .join(FrameworkControl, ControlMapping.target_control_id == FrameworkControl.id)
        .where(ControlMapping.source_control_id == control.id)
        .order_by(FrameworkControl.sort_order)
    ).all()

    return ControlDetailOut(
        id=control.id,
        control_ref=control.control_ref,
        title=control.title,
        group_ref=control.group_ref,
        group_title=control.group_title,
        in_scope=control.in_scope,
        scope_note=control.scope_note,
        framework_code=control.framework.code,
        mappings=[
            MappedCriterion(
                control_ref=target.control_ref,
                title=target.title,
                group_ref=target.group_ref,
                group_title=target.group_title,
                relationship_type=mapping.relationship_type,
            )
            for mapping, target in mapping_rows
        ],
    )
