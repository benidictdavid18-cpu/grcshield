from collections import Counter
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.audit import (
    AuditFinding,
    ControlTest,
    ControlTestEvidenceLink,
    FindingRemediationLink,
)
from app.models.risk import Control, ControlAnnexALink, RiskControl
from app.models.soa import (
    Evidence,
    RemediationItem,
    RemediationPriority,
    RemediationSource,
    RemediationStatus,
)
from app.schemas.audit import (
    ControlTestCreateIn,
    ControlTestDetailOut,
    ControlTestSummaryOut,
    EffectivenessUpdateIn,
    FindingOut,
    InternalControlOut,
    LinkedRemediationOut,
    TestEvidenceOut,
    TestingOverviewOut,
)
from app.services.control_testing import (
    CONCLUSION_TO_OPERATING,
    DesignEffectiveness,
    FindingSeverity,
    FindingSource,
    FindingStatus,
    OperatingEffectiveness,
    RemediationPriorityForSeverity,
    TestConclusion,
    requires_finding,
    severity_for,
    strongest_supported_basis,
    validate_effectiveness,
    validate_test,
)
from app.services.soa_validation import AUTHOR_TODO_MARKER

router = APIRouter(tags=["control testing"])


def _today() -> date:
    return date.today()


def _control_query():
    return select(Control).options(
        selectinload(Control.annex_a_links).selectinload(ControlAnnexALink.framework_control)
    )


def _test_query():
    return select(ControlTest).options(
        selectinload(ControlTest.control),
        selectinload(ControlTest.linked_finding),
        selectinload(ControlTest.evidence_links).selectinload(ControlTestEvidenceLink.evidence),
    )


def _finding_query():
    return select(AuditFinding).options(
        selectinload(AuditFinding.control),
        selectinload(AuditFinding.remediation_links).selectinload(
            FindingRemediationLink.remediation
        ),
    )


def _test_counts(db: Session) -> dict[int, int]:
    rows = db.execute(
        select(ControlTest.control_id, func.count(ControlTest.id)).group_by(ControlTest.control_id)
    ).all()
    return dict(rows)


# --- Internal control library ------------------------------------------------


@router.get("/internal-controls", response_model=list[InternalControlOut])
def list_internal_controls(
    family: str | None = Query(default=None),
    design_effectiveness: DesignEffectiveness | None = Query(default=None),
    operating_effectiveness: OperatingEffectiveness | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[InternalControlOut]:
    stmt = _control_query()
    if family:
        stmt = stmt.where(Control.control_family == family)
    if design_effectiveness is not None:
        stmt = stmt.where(Control.design_effectiveness == design_effectiveness)
    if operating_effectiveness is not None:
        stmt = stmt.where(Control.operating_effectiveness == operating_effectiveness)

    counts = _test_counts(db)
    controls = db.scalars(stmt.order_by(Control.sort_order)).unique().all()
    return [
        InternalControlOut(
            control_id=c.control_id,
            title=c.title,
            description=c.description,
            control_family=c.control_family,
            owner_role=c.owner_role,
            annex_a_refs=c.annex_a_refs,
            design_effectiveness=c.design_effectiveness,
            operating_effectiveness=c.operating_effectiveness,
            effectiveness_note=c.effectiveness_note,
            last_tested=c.last_tested,
            test_count=counts.get(c.id, 0),
            strongest_supported_basis=strongest_supported_basis(
                c.design_effectiveness, c.operating_effectiveness
            ),
        )
        for c in controls
    ]


@router.patch("/internal-controls/{control_id}/effectiveness", response_model=InternalControlOut)
def update_effectiveness(
    control_id: str, payload: EffectivenessUpdateIn, db: Session = Depends(get_db)
) -> InternalControlOut:
    """Re-rate a control's design and operating effectiveness.

    Enforces the rule that operating effectiveness cannot be EFFECTIVE while the design
    is DEFICIENT: if the control as designed does not achieve its objective, operating
    exactly as designed does not achieve it either.
    """
    control = db.scalar(_control_query().where(Control.control_id == control_id.upper()))
    if control is None:
        raise HTTPException(status_code=404, detail=f"Unknown control '{control_id}'")

    updates = payload.model_dump(exclude_unset=True)
    design = updates.get("design_effectiveness", control.design_effectiveness)
    operating = updates.get("operating_effectiveness", control.operating_effectiveness)

    violations = validate_effectiveness(design, operating)
    if violations:
        raise HTTPException(
            status_code=422,
            detail=[{"field": v.field, "message": v.message} for v in violations],
        )

    control.design_effectiveness = design
    control.operating_effectiveness = operating
    if "effectiveness_note" in updates:
        control.effectiveness_note = updates["effectiveness_note"]
    db.commit()
    db.refresh(control)

    counts = _test_counts(db)
    return InternalControlOut(
        control_id=control.control_id,
        title=control.title,
        description=control.description,
        control_family=control.control_family,
        owner_role=control.owner_role,
        annex_a_refs=control.annex_a_refs,
        design_effectiveness=control.design_effectiveness,
        operating_effectiveness=control.operating_effectiveness,
        effectiveness_note=control.effectiveness_note,
        last_tested=control.last_tested,
        test_count=counts.get(control.id, 0),
        strongest_supported_basis=strongest_supported_basis(
            control.design_effectiveness, control.operating_effectiveness
        ),
    )


# --- Workpapers ---------------------------------------------------------------


def _test_summary(test: ControlTest) -> ControlTestSummaryOut:
    return ControlTestSummaryOut(
        test_ref=test.test_ref,
        control_id=test.control.control_id,
        control_title=test.control.title,
        tester=test.tester,
        test_date=test.test_date,
        period_covered_start=test.period_covered_start,
        period_covered_end=test.period_covered_end,
        population_size=test.population_size,
        sample_size=test.sample_size,
        sample_selection_method=test.sample_selection_method,
        exceptions_count=test.exceptions_count,
        exception_rate=test.exception_rate,
        conclusion=test.conclusion,
        reviewed_by=test.reviewed_by,
        is_reviewed=test.is_reviewed,
        rationale_outstanding=AUTHOR_TODO_MARKER in test.sampling_rationale,
        linked_finding_ref=test.linked_finding.finding_ref if test.linked_finding else None,
    )


@router.get("/control-tests", response_model=list[ControlTestSummaryOut])
def list_control_tests(
    control_id: str | None = Query(default=None),
    conclusion: TestConclusion | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ControlTestSummaryOut]:
    stmt = _test_query()
    if conclusion is not None:
        stmt = stmt.where(ControlTest.conclusion == conclusion)
    tests = db.scalars(stmt.order_by(ControlTest.test_ref)).unique().all()
    if control_id:
        tests = [t for t in tests if t.control.control_id == control_id.upper()]
    return [_test_summary(t) for t in tests]


@router.get("/control-tests/overview", response_model=TestingOverviewOut)
def testing_overview(db: Session = Depends(get_db)) -> TestingOverviewOut:
    as_of = _today()
    tests = db.scalars(_test_query()).unique().all()
    controls = db.scalars(select(Control)).all()
    findings = db.scalars(_finding_query()).unique().all()
    links = db.scalars(
        select(RiskControl).options(
            selectinload(RiskControl.control), selectinload(RiskControl.risk)
        )
    ).all()

    conclusions = Counter(t.conclusion.value for t in tests)
    open_findings = [f for f in findings if f.is_open]
    return TestingOverviewOut(
        total_tests=len(tests),
        by_conclusion={c.value: conclusions.get(c.value, 0) for c in TestConclusion},
        controls_tested=len({t.control_id for t in tests}),
        controls_total=len(controls),
        percent_controls_tested=(
            round(100 * len({t.control_id for t in tests}) / len(controls), 1) if controls else 0.0
        ),
        tests_unreviewed=sum(1 for t in tests if not t.is_reviewed),
        rationales_outstanding=sum(
            1 for t in tests if AUTHOR_TODO_MARKER in t.sampling_rationale
        ),
        open_findings=len(open_findings),
        findings_by_severity={
            s.value: sum(1 for f in open_findings if f.severity == s) for s in FindingSeverity
        },
        controls_design_deficient=sum(
            1 for c in controls if c.design_effectiveness == DesignEffectiveness.DEFICIENT
        ),
        controls_never_tested=sum(
            1 for c in controls if c.operating_effectiveness == OperatingEffectiveness.NOT_TESTED
        ),
        optimistic_risk_links=sorted(
            f"{link.risk.risk_ref}/{link.control.control_id}"
            for link in links
            if link.basis_is_optimistic
        ),
    )
    _ = as_of


def _test_detail(test: ControlTest, as_of: date) -> ControlTestDetailOut:
    base = _test_summary(test)
    return ControlTestDetailOut(
        **base.model_dump(),
        test_objective=test.test_objective,
        test_procedure=test.test_procedure,
        population_description=test.population_description,
        sampling_rationale=test.sampling_rationale,
        results_summary=test.results_summary,
        exception_details=test.exception_details,
        review_date=test.review_date,
        evidence=[
            TestEvidenceOut(
                evidence_ref=item.evidence_ref, title=item.title, expired=item.is_expired(as_of)
            )
            for item in test.linked_evidence
        ],
    )


@router.get("/control-tests/{test_ref}", response_model=ControlTestDetailOut)
def get_control_test(test_ref: str, db: Session = Depends(get_db)) -> ControlTestDetailOut:
    test = db.scalar(_test_query().where(ControlTest.test_ref == test_ref.upper()))
    if test is None:
        raise HTTPException(status_code=404, detail=f"Unknown test '{test_ref}'")
    return _test_detail(test, _today())


def _next_ref(db: Session, model, column, prefix: str) -> str:
    existing = db.scalars(select(column)).all()
    numbers = [int(ref.split("-")[-1]) for ref in existing if ref.rsplit("-", 1)[-1].isdigit()]
    return f"{prefix}-{max(numbers, default=0) + 1:03d}"


@router.post("/control-tests", response_model=ControlTestDetailOut, status_code=201)
def create_control_test(
    payload: ControlTestCreateIn, db: Session = Depends(get_db)
) -> ControlTestDetailOut:
    """Record a workpaper.

    A conclusion of FAIL or PASS_WITH_EXCEPTIONS **auto-creates** a draft audit finding
    and a remediation item linked back to the test. A test that found something and
    reported nothing is worse than no test at all, so there is no way to record an
    exception without also recording what will be done about it.

    The finding is created as DRAFT deliberately: the system observed a fact, but whether
    it is a finding worth raising, and at what severity, is a human judgment.
    """
    control = db.scalar(select(Control).where(Control.control_id == payload.control_id.upper()))
    if control is None:
        raise HTTPException(status_code=404, detail=f"Unknown control '{payload.control_id}'")

    errors = validate_test(
        population_size=payload.population_size,
        sample_size=payload.sample_size,
        sample_selection_method=payload.sample_selection_method,
        sampling_rationale=payload.sampling_rationale,
        exceptions_count=payload.exceptions_count,
        conclusion=payload.conclusion,
        exception_details=payload.exception_details,
        tester=payload.tester,
        reviewed_by=payload.reviewed_by,
        period_covered_start=payload.period_covered_start,
        period_covered_end=payload.period_covered_end,
    )
    if errors:
        raise HTTPException(
            status_code=422,
            detail=[{"field": e.field, "message": e.message} for e in errors],
        )

    evidence_map = {}
    if payload.evidence_refs:
        found = db.scalars(
            select(Evidence).where(Evidence.evidence_ref.in_(payload.evidence_refs))
        ).all()
        evidence_map = {e.evidence_ref: e for e in found}
        missing = set(payload.evidence_refs) - set(evidence_map)
        if missing:
            raise HTTPException(status_code=422, detail=f"Unknown evidence: {sorted(missing)}")

    test = ControlTest(
        test_ref=_next_ref(db, ControlTest, ControlTest.test_ref, "TEST"),
        control_id=control.id,
        tester=payload.tester,
        test_date=payload.test_date,
        period_covered_start=payload.period_covered_start,
        period_covered_end=payload.period_covered_end,
        test_objective=payload.test_objective,
        test_procedure=payload.test_procedure,
        population_description=payload.population_description,
        population_size=payload.population_size,
        sample_size=payload.sample_size,
        sample_selection_method=payload.sample_selection_method,
        sampling_rationale=payload.sampling_rationale,
        results_summary=payload.results_summary,
        exceptions_count=payload.exceptions_count,
        exception_details=payload.exception_details,
        conclusion=payload.conclusion,
        reviewed_by=payload.reviewed_by,
        review_date=payload.review_date,
    )
    db.add(test)
    db.flush()

    for ref in payload.evidence_refs:
        db.add(ControlTestEvidenceLink(control_test_id=test.id, evidence_id=evidence_map[ref].id))

    if requires_finding(payload.conclusion):
        severity = severity_for(
            payload.conclusion, payload.exceptions_count, payload.sample_size
        )
        finding = AuditFinding(
            finding_ref=_next_ref(db, AuditFinding, AuditFinding.finding_ref, "FIND"),
            title=f"{control.control_id}: {payload.conclusion.value.replace('_', ' ').lower()} "
            f"in {test.test_ref}",
            description=(
                f"{test.test_ref} concluded {payload.conclusion.value} against "
                f"{control.control_id} ({control.title}). "
                f"{payload.exceptions_count} exception(s) in a sample of "
                f"{payload.sample_size}. {payload.exception_details or ''}"
            ).strip(),
            severity=severity,
            status=FindingStatus.DRAFT,
            source=FindingSource.CONTROL_TEST,
            identified_date=payload.test_date,
            identified_by=payload.tester,
            owner=payload.remediation_owner or control.owner_role,
            control_id=control.id,
        )
        db.add(finding)
        db.flush()

        remediation = RemediationItem(
            remediation_ref=_next_ref(
                db, RemediationItem, RemediationItem.remediation_ref, "REM"
            ),
            title=f"Remediate {finding.finding_ref}: {control.control_id}",
            description=(
                f"Raised automatically from {test.test_ref}. {payload.exception_details or ''}"
            ).strip(),
            owner=payload.remediation_owner or control.owner_role,
            # Default 90 days out. A date the owner has not agreed is a placeholder, but
            # a placeholder that exists can be challenged; a missing one cannot.
            due_date=payload.remediation_due_date or date.fromordinal(
                payload.test_date.toordinal() + 90
            ),
            status=RemediationStatus.OPEN,
            priority=RemediationPriority(RemediationPriorityForSeverity[severity]),
            source=RemediationSource.CONTROL_TEST,
        )
        db.add(remediation)
        db.flush()
        db.add(
            FindingRemediationLink(finding_id=finding.id, remediation_id=remediation.id)
        )
        test.linked_finding_id = finding.id

    # Keep the control library honest: a test result that contradicts the recorded
    # operating rating means one of the two is wrong.
    implied = CONCLUSION_TO_OPERATING[payload.conclusion]
    if validate_effectiveness(control.design_effectiveness, implied):
        # A deficient design cannot support an EFFECTIVE rating even after a clean test.
        implied = OperatingEffectiveness.EFFECTIVE_WITH_EXCEPTIONS
    control.operating_effectiveness = implied
    control.last_tested = payload.test_date

    db.commit()
    db.refresh(test)
    return _test_detail(test, _today())


# --- Findings ------------------------------------------------------------------


def _finding_out(finding: AuditFinding, as_of: date, source_test: str | None) -> FindingOut:
    return FindingOut(
        finding_ref=finding.finding_ref,
        title=finding.title,
        description=finding.description,
        severity=finding.severity,
        status=finding.status,
        source=finding.source,
        identified_date=finding.identified_date,
        identified_by=finding.identified_by,
        owner=finding.owner,
        closed_date=finding.closed_date,
        control_id=finding.control.control_id if finding.control else None,
        source_test_ref=source_test,
        remediation=[
            LinkedRemediationOut(
                remediation_ref=item.remediation_ref,
                title=item.title,
                owner=item.owner,
                due_date=item.due_date,
                status=item.status.value,
                overdue=item.is_overdue(as_of),
            )
            for item in finding.linked_remediation
        ],
    )


@router.get("/findings", response_model=list[FindingOut])
def list_findings(
    status: FindingStatus | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[FindingOut]:
    stmt = _finding_query()
    if status is not None:
        stmt = stmt.where(AuditFinding.status == status)
    findings = db.scalars(stmt.order_by(AuditFinding.finding_ref)).unique().all()

    source_tests = {
        t.linked_finding_id: t.test_ref
        for t in db.scalars(select(ControlTest).where(ControlTest.linked_finding_id.is_not(None)))
    }
    as_of = _today()
    return [_finding_out(f, as_of, source_tests.get(f.id)) for f in findings]


@router.get("/findings/{finding_ref}", response_model=FindingOut)
def get_finding(finding_ref: str, db: Session = Depends(get_db)) -> FindingOut:
    finding = db.scalar(_finding_query().where(AuditFinding.finding_ref == finding_ref.upper()))
    if finding is None:
        raise HTTPException(status_code=404, detail=f"Unknown finding '{finding_ref}'")
    source = db.scalar(
        select(ControlTest.test_ref).where(ControlTest.linked_finding_id == finding.id)
    )
    return _finding_out(finding, _today(), source)
