from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.audit import ControlTest
from app.models.risk import RiskAppetiteThreshold
from app.models.soa import (
    ImplementationStatus,
    SoAControlLink,
    SoAEntry,
    SoAEvidenceLink,
    SoARemediationLink,
    SoARiskLink,
)
from app.reports.soa_report import render_soa_gap_report
from app.schemas.soa import (
    EvidenceOut,
    LinkedInternalControlOut,
    LinkedRiskOut,
    LinkedTestOut,
    RemediationOut,
    SoADetailOut,
    SoAOverviewOut,
    SoASummaryOut,
    SoAUpdateIn,
    ThemeSummaryOut,
)
from app.seed.annex_a_2022 import THEME_TITLES
from app.services.risk_scoring import CATEGORY_LABELS
from app.services.soa_validation import AUTHOR_TODO_MARKER, entry_errors

router = APIRouter(prefix="/soa", tags=["statement of applicability"])


def _today() -> date:
    return date.today()


def _entry_query():
    return select(SoAEntry).options(
        selectinload(SoAEntry.control_links).selectinload(SoAControlLink.control),
        selectinload(SoAEntry.risk_links).selectinload(SoARiskLink.risk),
        selectinload(SoAEntry.evidence_links).selectinload(SoAEvidenceLink.evidence),
        selectinload(SoAEntry.remediation_links).selectinload(SoARemediationLink.remediation),
    )


def _justification_outstanding(entry: SoAEntry) -> bool:
    return AUTHOR_TODO_MARKER in (entry.justification_inclusion or "") or (
        AUTHOR_TODO_MARKER in (entry.justification_exclusion or "")
    )


def _summary(entry: SoAEntry, as_of: date) -> SoASummaryOut:
    return SoASummaryOut(
        control_ref=entry.control_ref,
        control_title=entry.control_title,
        theme=entry.theme,
        applicable=entry.applicable,
        implementation_status=entry.implementation_status,
        owner=entry.owner,
        is_gap=entry.is_gap,
        justification_outstanding=_justification_outstanding(entry),
        linked_risk_count=len(entry.risk_links),
        linked_control_count=len(entry.control_links),
        linked_evidence_count=len(entry.evidence_links),
        open_remediation_count=sum(1 for item in entry.linked_remediation if item.is_open),
        has_expired_evidence=any(item.is_expired(as_of) for item in entry.linked_evidence),
    )


def _sort_key(entry: SoAEntry) -> tuple[int, int]:
    """Annex A order, not lexicographic -- A.5.9 precedes A.5.10."""
    theme, number = entry.control_ref.removeprefix("A.").split(".")
    return int(theme), int(number)


@router.get("", response_model=list[SoASummaryOut])
def list_entries(
    theme: str | None = Query(default=None, description="A.5, A.6, A.7 or A.8"),
    applicable: bool | None = Query(default=None),
    implementation_status: ImplementationStatus | None = Query(default=None),
    gaps_only: bool = Query(default=False),
    q: str | None = Query(default=None, description="Substring match on reference or title"),
    db: Session = Depends(get_db),
) -> list[SoASummaryOut]:
    stmt = _entry_query()
    if theme:
        stmt = stmt.where(SoAEntry.theme == theme)
    if applicable is not None:
        stmt = stmt.where(SoAEntry.applicable.is_(applicable))
    if implementation_status is not None:
        stmt = stmt.where(SoAEntry.implementation_status == implementation_status)

    entries = sorted(db.scalars(stmt).unique().all(), key=_sort_key)
    if gaps_only:
        entries = [entry for entry in entries if entry.is_gap]
    if q:
        needle = q.lower()
        entries = [
            entry
            for entry in entries
            if needle in entry.control_ref.lower() or needle in entry.control_title.lower()
        ]

    as_of = _today()
    return [_summary(entry, as_of) for entry in entries]


@router.get("/overview", response_model=SoAOverviewOut)
def overview(db: Session = Depends(get_db)) -> SoAOverviewOut:
    as_of = _today()
    entries = sorted(db.scalars(_entry_query()).unique().all(), key=_sort_key)
    if not entries:
        raise HTTPException(status_code=503, detail="Statement of Applicability is not seeded")

    applicable = [e for e in entries if e.applicable]
    implemented = [
        e for e in applicable if e.implementation_status == ImplementationStatus.IMPLEMENTED
    ]
    partial = [
        e
        for e in applicable
        if e.implementation_status == ImplementationStatus.PARTIALLY_IMPLEMENTED
    ]
    not_implemented = [
        e for e in applicable if e.implementation_status == ImplementationStatus.NOT_IMPLEMENTED
    ]

    themes: list[ThemeSummaryOut] = []
    for theme_ref in sorted({e.theme for e in entries}):
        rows = [e for e in entries if e.theme == theme_ref]
        theme_applicable = [e for e in rows if e.applicable]
        themes.append(
            ThemeSummaryOut(
                theme=theme_ref,
                theme_title=THEME_TITLES.get(theme_ref, theme_ref),
                total=len(rows),
                applicable=len(theme_applicable),
                excluded=len(rows) - len(theme_applicable),
                implemented=sum(
                    1
                    for e in theme_applicable
                    if e.implementation_status == ImplementationStatus.IMPLEMENTED
                ),
                partially_implemented=sum(
                    1
                    for e in theme_applicable
                    if e.implementation_status == ImplementationStatus.PARTIALLY_IMPLEMENTED
                ),
                not_implemented=sum(
                    1
                    for e in theme_applicable
                    if e.implementation_status == ImplementationStatus.NOT_IMPLEMENTED
                ),
            )
        )

    open_remediation = {
        item.remediation_ref: item
        for entry in entries
        for item in entry.linked_remediation
        if item.is_open
    }

    first = entries[0]
    return SoAOverviewOut(
        total_controls=len(entries),
        applicable=len(applicable),
        excluded=len(entries) - len(applicable),
        implemented=len(implemented),
        partially_implemented=len(partial),
        not_implemented=len(not_implemented),
        # Denominator is applicable controls, not all 93. Counting excluded controls as
        # unimplemented would understate readiness; counting them as implemented would
        # overstate it. Neither is true -- they are simply not in scope.
        percent_implemented=round(100 * len(implemented) / len(applicable), 1) if applicable else 0.0,
        gaps=sum(1 for e in entries if e.is_gap),
        justifications_outstanding=sum(1 for e in entries if _justification_outstanding(e)),
        implemented_without_evidence=sum(1 for e in implemented if not e.evidence_links),
        expired_evidence=len(
            {
                item.evidence_ref
                for entry in entries
                for item in entry.linked_evidence
                if item.is_expired(as_of)
            }
        ),
        open_remediation=len(open_remediation),
        overdue_remediation=sum(1 for item in open_remediation.values() if item.is_overdue(as_of)),
        version=first.version,
        approved_by=first.approved_by,
        approved_date=first.approved_date,
        themes=themes,
    )


def _get_or_404(db: Session, control_ref: str) -> SoAEntry:
    entry = db.scalar(_entry_query().where(SoAEntry.control_ref == control_ref.upper()))
    if entry is None:
        raise HTTPException(status_code=404, detail=f"No SoA entry for control '{control_ref}'")
    return entry


def _tests_for(db: Session, entry: SoAEntry) -> list[LinkedTestOut]:
    """Workpapers reached through this entry's internal controls.

    The chain is SoA entry → internal control → control test. Nothing links a test
    directly to an Annex A control, because tests are performed against the thing
    FinFlow operates, not against the catalogue entry it satisfies.
    """
    control_ids = [link.control_id for link in entry.control_links]
    if not control_ids:
        return []
    tests = db.scalars(
        select(ControlTest)
        .options(selectinload(ControlTest.control), selectinload(ControlTest.linked_finding))
        .where(ControlTest.control_id.in_(control_ids))
        .order_by(ControlTest.test_date.desc())
    ).all()
    return [
        LinkedTestOut(
            test_ref=test.test_ref,
            control_id=test.control.control_id,
            test_date=test.test_date,
            conclusion=test.conclusion.value,
            exceptions_count=test.exceptions_count,
            sample_size=test.sample_size,
            population_size=test.population_size,
            finding_ref=test.linked_finding.finding_ref if test.linked_finding else None,
        )
        for test in tests
    ]


def _detail(entry: SoAEntry, thresholds: dict, as_of: date, tests: list[LinkedTestOut]) -> SoADetailOut:
    base = _summary(entry, as_of)
    return SoADetailOut(
        **base.model_dump(),
        justification_inclusion=entry.justification_inclusion,
        justification_exclusion=entry.justification_exclusion,
        implementation_description=entry.implementation_description,
        last_reviewed=entry.last_reviewed,
        next_review=entry.next_review,
        approved_by=entry.approved_by,
        approved_date=entry.approved_date,
        version=entry.version,
        risks=[
            LinkedRiskOut(
                risk_ref=risk.risk_ref,
                title=risk.title,
                category_label=CATEGORY_LABELS[risk.category],
                treatment_decision=risk.treatment_decision,
                residual_score=risk.residual_score,
                residual_band=risk.residual_band,
                exceeds_appetite=risk.exceeds(thresholds.get(risk.category)),
            )
            for risk in entry.linked_risks
        ],
        controls=[
            LinkedInternalControlOut(
                control_id=control.control_id,
                title=control.title,
                owner_role=control.owner_role,
                control_family=control.control_family,
            )
            for control in entry.linked_controls
        ],
        tests=tests,
        evidence=[
            EvidenceOut(
                evidence_ref=item.evidence_ref,
                title=item.title,
                description=item.description,
                evidence_type=item.evidence_type,
                source_system=item.source_system,
                collected_by=item.collected_by,
                collected_date=item.collected_date,
                valid_from=item.valid_from,
                valid_until=item.valid_until,
                file_reference=item.file_reference,
                control_id=item.control.control_id if item.control else None,
                expired=item.is_expired(as_of),
            )
            for item in entry.linked_evidence
        ],
        remediation=[
            RemediationOut(
                remediation_ref=item.remediation_ref,
                title=item.title,
                description=item.description,
                owner=item.owner,
                due_date=item.due_date,
                status=item.status,
                priority=item.priority,
                completed_date=item.completed_date,
                overdue=item.is_overdue(as_of),
            )
            for item in entry.linked_remediation
        ],
        validation_errors=[f"{e.field}: {e.message}" for e in entry_errors(entry)],
    )


def _thresholds(db: Session) -> dict:
    return {row.category: row for row in db.scalars(select(RiskAppetiteThreshold)).all()}


@router.get("/report.pdf")
def soa_gap_report(db: Session = Depends(get_db)) -> Response:
    """The SoA + Gap Analysis Report, one of the three reports GRCShield produces."""
    entries = sorted(db.scalars(_entry_query()).unique().all(), key=_sort_key)
    if not entries:
        raise HTTPException(status_code=503, detail="Statement of Applicability is not seeded")
    pdf = render_soa_gap_report(entries, overview(db), as_of=_today())
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'inline; filename="finflow-soa-gap-analysis.pdf"',
        },
    )


@router.get("/{control_ref}", response_model=SoADetailOut)
def get_entry(control_ref: str, db: Session = Depends(get_db)) -> SoADetailOut:
    entry = _get_or_404(db, control_ref)
    return _detail(entry, _thresholds(db), _today(), _tests_for(db, entry))


@router.patch("/{control_ref}", response_model=SoADetailOut)
def update_entry(
    control_ref: str, payload: SoAUpdateIn, db: Session = Depends(get_db)
) -> SoADetailOut:
    """Update an SoA entry, enforcing Clause 6.1.3 d).

    Three rules, all returned as 422 with the field named:

    1. Applicable requires an inclusion justification that cites a driver -- a linked
       risk, or a legal, regulatory or contractual obligation. "Required by ISO 27001"
       is circular and is rejected explicitly.
    2. Excluded requires an exclusion justification and forces NOT_IMPLEMENTED.
    3. Applicable and not fully implemented is a gap, and a gap requires at least one
       live remediation item with an owner and a due date.

    The whole entry is revalidated after the change, not only the fields supplied, so
    an edit cannot leave the entry internally inconsistent.
    """
    entry = _get_or_404(db, control_ref)
    updates = payload.model_dump(exclude_unset=True)

    applicable = updates.get("applicable", entry.applicable)
    status = updates.get("implementation_status", entry.implementation_status)
    # Excluding a control forces NOT_IMPLEMENTED. Applying it here rather than
    # rejecting the combination keeps the rule from being a trap when a caller flips
    # applicability without also restating the status.
    if applicable is False and "implementation_status" not in updates:
        status = ImplementationStatus.NOT_IMPLEMENTED

    proposed = {
        "applicable": applicable,
        "justification_inclusion": updates.get(
            "justification_inclusion", entry.justification_inclusion
        ),
        "justification_exclusion": updates.get(
            "justification_exclusion", entry.justification_exclusion
        ),
        "implementation_status": status,
        "implementation_description": updates.get(
            "implementation_description", entry.implementation_description
        ),
        "owner": updates.get("owner", entry.owner),
    }

    original = {field: getattr(entry, field) for field in proposed}
    for field, value in proposed.items():
        setattr(entry, field, value)

    errors = entry_errors(entry)
    if errors:
        for field, value in original.items():
            setattr(entry, field, value)
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=[{"field": e.field, "message": e.message} for e in errors],
        )

    db.commit()
    db.refresh(entry)
    return _detail(entry, _thresholds(db), _today(), _tests_for(db, entry))
