"""Load the framework registry, control library and ISO -> SOC 2 mappings.

Idempotent: re-running updates titles and scope notes in place rather than
duplicating rows, so `docker compose up` against an existing volume is safe.

Run with:  python -m app.seed.run_seed
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.framework import (
    ControlMapping,
    Framework,
    FrameworkControl,
    MappingRelationship,
    ScopeStatus,
)
from app.models.risk import (
    Control,
    ControlAnnexALink,
    Risk,
    RiskAppetiteThreshold,
    RiskControl,
)
from app.models.soa import (
    Evidence,
    EvidenceType,
    ImplementationStatus,
    RemediationItem,
    RemediationPriority,
    RemediationSource,
    RemediationStatus,
    SoAControlLink,
    SoAEntry,
    SoAEvidenceLink,
    SoARemediationLink,
    SoARiskLink,
)
from app.models.audit import (
    AuditFinding,
    ControlTest,
    ControlTestEvidenceLink,
    FindingRemediationLink,
    InternalAudit,
    ManagementReview,
    Nonconformity,
)
from app.services.control_testing import (
    CONCLUSION_TO_OPERATING,
    AuditStatus,
    DesignEffectiveness,
    FindingSeverity,
    FindingSource,
    FindingStatus,
    NonconformityStatus,
    OperatingEffectiveness,
    SampleSelectionMethod,
    TestConclusion,
    basis_supported_by_control,
    requires_finding,
    validate_effectiveness,
    validate_test,
)
from app.models.privacy import (
    Asset,
    BiaAssetLink,
    BiaControlLink,
    BiaRiskLink,
    BusinessImpactAnalysis,
    Dpia,
    DpiaAssetLink,
    DpiaRiskLink,
    RiskException,
    RopaAssetLink,
    RopaControlLink,
    RopaEntry,
    RopaRiskLink,
)
from app.core.config import get_settings
from app.core.security import hash_password
from app.models.kri import (
    KriDefinition,
    KriDirection,
    KriMeasurement,
    KriUnit,
    MeasurementFrequency,
)
from app.models.user import Role, User
from app.seed.asset_register import ASSETS
from app.seed.kri_register import KRI_DEFINITIONS
from app.seed.users import DEMO_USERS
from app.seed.continuity_register import BIA_PROCESSES
from app.seed.exception_register import RISK_EXCEPTIONS
from app.seed.privacy_register import DPIAS, ROPA_ENTRIES
from app.services.privacy_continuity import (
    AssetType,
    Classification,
    DpiaOutcome,
    ExceptionStatus,
    LawfulBasis,
    ResidualRiskLevel,
    TransferSafeguard,
    validate_bia,
    validate_dpia,
    validate_exception,
    validate_ropa,
)
from app.services.soa_validation import entry_errors
from app.seed.annex_a_2022 import (
    ANNEX_A_CONTROLS,
    PROVISIONAL_EXCLUSIONS,
    THEME_TITLES,
)
from app.seed.control_tests import (
    AUDIT_FINDINGS,
    CONTROL_TESTS,
    INTERNAL_AUDITS,
    MANAGEMENT_REVIEWS,
    NONCONFORMITIES,
)
from app.seed.evidence_register import EVIDENCE
from app.seed.internal_controls import EFFECTIVENESS, INTERNAL_CONTROLS
from app.seed.iso_soc2_mappings import ISO_TO_SOC2
from app.seed.remediation_register import REMEDIATION_ITEMS
from app.seed.risk_register import APPETITE_THRESHOLDS, RISKS
from app.seed.soa_register import (
    SOA_APPROVED_BY,
    SOA_APPROVED_DATE,
    SOA_ENTRIES,
    SOA_LAST_REVIEWED,
    SOA_NEXT_REVIEW,
    SOA_VERSION,
)
from app.seed.soc2_tsc import ELECTED_CATEGORIES, TSC_CRITERIA

ISO_CODE = "ISO27001_2022"
SOC2_CODE = "SOC2_TSC"
NIST_CODE = "NIST_CSF_2_0"
GDPR_CODE = "GDPR"

FRAMEWORKS = [
    dict(
        code=ISO_CODE,
        name="ISO/IEC 27001:2022 — Information security management systems",
        version="2022",
        publisher="ISO/IEC",
        scope_status=ScopeStatus.PRIMARY,
        sort_order=10,
        scope_note=(
            "FinFlow's primary framework. All 93 Annex A controls are catalogued and "
            "each one receives an applicability decision in the Statement of "
            "Applicability (Clause 6.1.3 d). Risk assessment follows ISO/IEC 27005."
        ),
    ),
    dict(
        code=SOC2_CODE,
        name="AICPA SOC 2 Trust Services Criteria",
        version="2017 (2022 points of focus)",
        publisher="AICPA",
        scope_status=ScopeStatus.SECONDARY,
        sort_order=20,
        scope_note=(
            "Assessed by mapping from ISO/IEC 27001:2022, not independently. FinFlow "
            "elects Security (Common Criteria), Availability and Confidentiality. "
            "Processing Integrity and Privacy are not elected — privacy obligations are "
            "handled under GDPR Articles 30 and 35 instead. Criteria descriptions here "
            "are plain-English summaries, not the AICPA's copyrighted wording."
        ),
    ),
    dict(
        code=NIST_CODE,
        name="NIST Cybersecurity Framework 2.0",
        version="2.0",
        publisher="NIST",
        scope_status=ScopeStatus.ROADMAP,
        sort_order=30,
        scope_note=(
            "Not yet assessed. NIST CSF 2.0 is a profile-and-outcome framework that "
            "would largely restate the ISO control set for a company this size, so "
            "assessing both at once would produce breadth without adding assurance. "
            "Revisit once the ISO ISMS has completed one full internal audit cycle."
        ),
    ),
    dict(
        code=GDPR_CODE,
        name="EU General Data Protection Regulation",
        version="Regulation (EU) 2016/679",
        publisher="European Union",
        scope_status=ScopeStatus.ROADMAP,
        sort_order=40,
        scope_note=(
            "Not assessed article-by-article. GDPR is a legal obligation rather than a "
            "control framework, and a control-by-control scorecard against it invites "
            "false precision about legal compliance. Two operational artefacts are built "
            "as real modules instead: the Record of Processing Activities (Article 30) "
            "and Data Protection Impact Assessments (Article 35). Compliance obligations "
            "are carried into the ISMS through A.5.31 and A.5.34."
        ),
    ),
]


def _upsert_framework(db: Session, spec: dict) -> Framework:
    framework = db.scalar(select(Framework).where(Framework.code == spec["code"]))
    if framework is None:
        framework = Framework(**spec)
        db.add(framework)
    else:
        for key, value in spec.items():
            setattr(framework, key, value)
    db.flush()
    return framework


def _upsert_control(db: Session, framework: Framework, **spec) -> FrameworkControl:
    control = db.scalar(
        select(FrameworkControl).where(
            FrameworkControl.framework_id == framework.id,
            FrameworkControl.control_ref == spec["control_ref"],
        )
    )
    if control is None:
        control = FrameworkControl(framework_id=framework.id, **spec)
        db.add(control)
    else:
        for key, value in spec.items():
            setattr(control, key, value)
    db.flush()
    return control


def seed_iso(db: Session) -> dict[str, FrameworkControl]:
    framework = _upsert_framework(db, next(f for f in FRAMEWORKS if f["code"] == ISO_CODE))
    controls: dict[str, FrameworkControl] = {}
    for order, entry in enumerate(ANNEX_A_CONTROLS, start=1):
        exclusion_note = PROVISIONAL_EXCLUSIONS.get(entry.ref)
        controls[entry.ref] = _upsert_control(
            db,
            framework,
            control_ref=entry.ref,
            title=entry.title,
            group_ref=entry.theme,
            group_title=THEME_TITLES[entry.theme],
            sort_order=order,
            in_scope=exclusion_note is None,
            scope_note=exclusion_note,
        )
    return controls


def seed_soc2(db: Session) -> dict[str, FrameworkControl]:
    framework = _upsert_framework(db, next(f for f in FRAMEWORKS if f["code"] == SOC2_CODE))
    controls: dict[str, FrameworkControl] = {}
    for order, criterion in enumerate(TSC_CRITERIA, start=1):
        # CC1..CC9 all sit under the mandatory Common Criteria election; the optional
        # categories are elected individually.
        elected = criterion.category.startswith("CC") or ELECTED_CATEGORIES.get(
            criterion.category, False
        )
        controls[criterion.ref] = _upsert_control(
            db,
            framework,
            control_ref=criterion.ref,
            title=criterion.title,
            group_ref=criterion.category,
            group_title=criterion.category_title,
            sort_order=order,
            in_scope=elected,
            scope_note=None if elected else "Trust Services category not elected for FinFlow's SOC 2 scope.",
        )
    return controls


def seed_roadmap_frameworks(db: Session) -> None:
    """NIST CSF 2.0 and GDPR are registered but carry no control rows.

    Populating a catalogue we have not assessed would let the UI render progress
    bars against controls nobody has looked at. The scope_note carries the
    explanation instead.
    """
    for code in (NIST_CODE, GDPR_CODE):
        _upsert_framework(db, next(f for f in FRAMEWORKS if f["code"] == code))


def seed_mappings(
    db: Session, iso: dict[str, FrameworkControl], soc2: dict[str, FrameworkControl]
) -> int:
    created = 0
    for iso_ref, tsc_ref, relationship in ISO_TO_SOC2:
        source = iso.get(iso_ref)
        target = soc2.get(tsc_ref)
        if source is None:
            raise ValueError(f"Mapping references unknown ISO control '{iso_ref}'")
        if target is None:
            raise ValueError(f"Mapping references unknown TSC criterion '{tsc_ref}'")
        if not source.in_scope:
            raise ValueError(
                f"Mapping '{iso_ref}' -> '{tsc_ref}' targets an out-of-scope ISO control. "
                "An excluded control produces no evidence and cannot satisfy a criterion."
            )
        if not target.in_scope:
            raise ValueError(
                f"Mapping '{iso_ref}' -> '{tsc_ref}' targets a Trust Services category "
                "FinFlow has not elected."
            )

        existing = db.scalar(
            select(ControlMapping).where(
                ControlMapping.source_control_id == source.id,
                ControlMapping.target_control_id == target.id,
            )
        )
        if existing is None:
            db.add(
                ControlMapping(
                    source_control_id=source.id,
                    target_control_id=target.id,
                    relationship_type=MappingRelationship(relationship),
                )
            )
            created += 1
        else:
            existing.relationship_type = MappingRelationship(relationship)
    db.flush()
    return created


def seed_internal_controls(
    db: Session, iso: dict[str, FrameworkControl]
) -> dict[str, Control]:
    controls: dict[str, Control] = {}
    for order, spec in enumerate(INTERNAL_CONTROLS, start=1):
        control = db.scalar(select(Control).where(Control.control_id == spec.control_id))
        if control is None:
            control = Control(control_id=spec.control_id)
            db.add(control)
        control.title = spec.title
        control.description = spec.description
        control.control_family = spec.family
        control.owner_role = spec.owner_role
        control.sort_order = order
        design, operating, note = EFFECTIVENESS[spec.control_id]
        control.design_effectiveness = DesignEffectiveness(design)
        control.operating_effectiveness = OperatingEffectiveness(operating)
        control.effectiveness_note = note
        violations = validate_effectiveness(
            control.design_effectiveness, control.operating_effectiveness
        )
        if violations:
            raise ValueError(f"{spec.control_id}: {violations[0].message}")
        db.flush()

        wanted = set(spec.annex_a_refs)
        unknown = wanted - set(iso)
        if unknown:
            raise ValueError(f"{spec.control_id} references unknown Annex A refs: {sorted(unknown)}")

        existing = {link.framework_control.control_ref: link for link in control.annex_a_links}
        for ref in wanted - set(existing):
            db.add(ControlAnnexALink(control_id=control.id, framework_control_id=iso[ref].id))
        for ref in set(existing) - wanted:
            db.delete(existing[ref])
        db.flush()
        controls[spec.control_id] = control
    return controls


def seed_appetite(db: Session) -> int:
    for spec in APPETITE_THRESHOLDS:
        threshold = db.scalar(
            select(RiskAppetiteThreshold).where(RiskAppetiteThreshold.category == spec.category)
        )
        if threshold is None:
            threshold = RiskAppetiteThreshold(category=spec.category)
            db.add(threshold)
        threshold.max_acceptable_band = spec.max_acceptable_band
        threshold.approver_role = spec.approver_role
        threshold.rationale = spec.rationale
        threshold.last_reviewed = date(2026, 4, 30)
    db.flush()
    return len(APPETITE_THRESHOLDS)


def seed_risks(db: Session, controls: dict[str, Control]) -> int:
    for spec in RISKS:
        risk = db.scalar(select(Risk).where(Risk.risk_ref == spec.risk_ref))
        if risk is None:
            risk = Risk(risk_ref=spec.risk_ref)
            db.add(risk)
        for field in (
            "title", "description", "category", "owner_role", "status", "asset", "threat",
            "vulnerability", "inherent_likelihood", "inherent_impact", "residual_likelihood",
            "residual_impact", "residual_justification", "treatment_decision",
            "treatment_summary", "date_identified", "last_reviewed", "next_review",
        ):
            setattr(risk, field, getattr(spec, field))
        db.flush()

        wanted = {ref: basis for ref, basis in spec.controls}
        unknown = set(wanted) - set(controls)
        if unknown:
            raise ValueError(f"{spec.risk_ref} references unknown controls: {sorted(unknown)}")

        existing = {link.control.control_id: link for link in risk.control_links}
        for ref, basis in wanted.items():
            if ref in existing:
                existing[ref].effectiveness_basis = basis
            else:
                db.add(
                    RiskControl(
                        risk_id=risk.id, control_id=controls[ref].id, effectiveness_basis=basis
                    )
                )
        for ref in set(existing) - set(wanted):
            db.delete(existing[ref])
        db.flush()

        # The methodology rule is enforced at the API layer for user input; seed data
        # must satisfy it too, or the register ships already contradicting itself.
        db.refresh(risk)
        if risk.claims_reduction and not risk.crediting_control_links:
            raise ValueError(
                f"{spec.risk_ref} claims a residual reduction "
                f"({risk.inherent_score} -> {risk.residual_score}) but every linked control "
                "is untested or tested ineffective, so none may be credited."
            )
    db.flush()
    return len(RISKS)


def seed_evidence(db: Session, controls: dict[str, Control]) -> dict[str, Evidence]:
    loaded: dict[str, Evidence] = {}
    for spec in EVIDENCE:
        artifact = db.scalar(select(Evidence).where(Evidence.evidence_ref == spec.ref))
        if artifact is None:
            artifact = Evidence(evidence_ref=spec.ref)
            db.add(artifact)
        artifact.title = spec.title
        artifact.description = spec.description
        artifact.evidence_type = EvidenceType(spec.evidence_type)
        artifact.source_system = spec.source_system
        artifact.collected_by = spec.collected_by
        artifact.collected_date = spec.collected_date
        artifact.valid_from = spec.valid_from
        artifact.valid_until = spec.valid_until
        artifact.file_reference = spec.file_reference
        if spec.control_ref is not None:
            if spec.control_ref not in controls:
                raise ValueError(f"{spec.ref} references unknown control '{spec.control_ref}'")
            artifact.control_id = controls[spec.control_ref].id
        if spec.valid_until < spec.valid_from:
            raise ValueError(f"{spec.ref} expires before it becomes valid")
        db.flush()
        loaded[spec.ref] = artifact
    return loaded


def seed_remediation(db: Session) -> dict[str, RemediationItem]:
    loaded: dict[str, RemediationItem] = {}
    for spec in REMEDIATION_ITEMS:
        item = db.scalar(
            select(RemediationItem).where(RemediationItem.remediation_ref == spec.ref)
        )
        if item is None:
            item = RemediationItem(remediation_ref=spec.ref)
            db.add(item)
        item.title = spec.title
        item.description = spec.description
        item.owner = spec.owner
        item.due_date = spec.due_date
        item.status = RemediationStatus(spec.status)
        item.priority = RemediationPriority(spec.priority)
        item.source = RemediationSource(spec.source)
        item.completed_date = spec.completed_date
        item.raised_date = spec.raised_date
        if (
            spec.raised_date
            and spec.completed_date
            and spec.completed_date < spec.raised_date
        ):
            raise ValueError(f"{spec.ref}: completed before it was raised")
        if (item.status == RemediationStatus.COMPLETED) != (item.completed_date is not None):
            raise ValueError(
                f"{spec.ref}: completed status and completion date must agree"
            )
        db.flush()
        loaded[spec.ref] = item
    return loaded


def seed_soa(
    db: Session,
    iso: dict[str, FrameworkControl],
    controls: dict[str, Control],
    risks: dict[str, Risk],
    evidence: dict[str, Evidence],
    remediation: dict[str, RemediationItem],
) -> dict[str, SoAEntry]:
    """Load the Statement of Applicability and refuse to ship an invalid one.

    Every entry is run through the same validator the API uses. Seed data that would
    be rejected on a write must not be loadable, or the SoA ships already breaking its
    own rules.
    """
    seen = {spec.ref for spec in SOA_ENTRIES}
    missing = set(iso) - seen
    if missing:
        raise ValueError(f"SoA is missing {len(missing)} Annex A control(s): {sorted(missing)}")
    unknown = seen - set(iso)
    if unknown:
        raise ValueError(f"SoA references non-existent controls: {sorted(unknown)}")

    loaded: dict[str, SoAEntry] = {}
    for spec in SOA_ENTRIES:
        catalogue = iso[spec.ref]
        entry = db.scalar(select(SoAEntry).where(SoAEntry.control_ref == spec.ref))
        if entry is None:
            entry = SoAEntry(control_ref=spec.ref)
            db.add(entry)
        entry.framework_control_id = catalogue.id
        # Snapshot fields must agree with the catalogue at load time; see SoAEntry.
        entry.control_title = catalogue.title
        entry.theme = catalogue.group_ref
        entry.applicable = spec.applicable
        entry.justification_inclusion = spec.inclusion
        entry.justification_exclusion = spec.exclusion
        entry.implementation_status = ImplementationStatus(spec.status)
        entry.implementation_description = spec.implementation
        entry.owner = spec.owner
        entry.version = SOA_VERSION
        entry.approved_by = SOA_APPROVED_BY
        entry.approved_date = SOA_APPROVED_DATE
        entry.last_reviewed = SOA_LAST_REVIEWED
        entry.next_review = SOA_NEXT_REVIEW
        db.flush()

        # (label, wanted refs, ref -> object lookup, link model, FK column, ref attribute)
        link_specs = (
            ("control", set(spec.controls), controls, SoAControlLink, "control_id", "control_id"),
            ("risk", set(spec.risks), risks, SoARiskLink, "risk_id", "risk_ref"),
            ("evidence", set(spec.evidence), evidence, SoAEvidenceLink, "evidence_id",
             "evidence_ref"),
            ("remediation", set(spec.remediation), remediation, SoARemediationLink,
             "remediation_id", "remediation_ref"),
        )
        for label, wanted_refs, lookup, link_model, fk_column, ref_attr in link_specs:
            unknown_refs = wanted_refs - set(lookup)
            if unknown_refs:
                raise ValueError(f"{spec.ref} links unknown {label}(s): {sorted(unknown_refs)}")

            current = db.scalars(
                select(link_model).where(link_model.soa_entry_id == entry.id)
            ).all()
            by_ref = {getattr(getattr(link, label), ref_attr): link for link in current}

            for ref in wanted_refs - set(by_ref):
                db.add(link_model(soa_entry_id=entry.id, **{fk_column: lookup[ref].id}))
            for ref in set(by_ref) - wanted_refs:
                db.delete(by_ref[ref])
            db.flush()

        db.refresh(entry)
        errors = entry_errors(entry)
        if errors:
            detail = "; ".join(f"{e.field}: {e.message}" for e in errors)
            raise ValueError(f"SoA entry {spec.ref} fails validation -- {detail}")
        loaded[spec.ref] = entry

    return loaded


def seed_findings(
    db: Session, controls: dict[str, Control], remediation: dict[str, RemediationItem]
) -> dict[str, AuditFinding]:
    loaded: dict[str, AuditFinding] = {}
    for spec in AUDIT_FINDINGS:
        finding = db.scalar(select(AuditFinding).where(AuditFinding.finding_ref == spec.ref))
        if finding is None:
            finding = AuditFinding(finding_ref=spec.ref)
            db.add(finding)
        finding.title = spec.title
        finding.description = spec.description
        finding.severity = FindingSeverity(spec.severity)
        finding.status = FindingStatus(spec.status)
        finding.source = FindingSource(spec.source)
        finding.identified_date = spec.identified_date
        finding.identified_by = spec.identified_by
        finding.owner = spec.owner
        finding.closed_date = spec.closed_date
        if spec.control_ref is not None:
            if spec.control_ref not in controls:
                raise ValueError(f"{spec.ref} references unknown control '{spec.control_ref}'")
            finding.control_id = controls[spec.control_ref].id
        db.flush()

        wanted = set(spec.remediation)
        unknown = wanted - set(remediation)
        if unknown:
            raise ValueError(f"{spec.ref} links unknown remediation: {sorted(unknown)}")
        if not wanted:
            raise ValueError(f"{spec.ref} has no remediation; a finding without a plan is noise")

        current = db.scalars(
            select(FindingRemediationLink).where(FindingRemediationLink.finding_id == finding.id)
        ).all()
        by_ref = {link.remediation.remediation_ref: link for link in current}
        for ref in wanted - set(by_ref):
            db.add(
                FindingRemediationLink(
                    finding_id=finding.id, remediation_id=remediation[ref].id
                )
            )
        for ref in set(by_ref) - wanted:
            db.delete(by_ref[ref])
        db.flush()
        loaded[spec.ref] = finding
    return loaded


def seed_control_tests(
    db: Session,
    controls: dict[str, Control],
    evidence: dict[str, Evidence],
    findings: dict[str, AuditFinding],
) -> dict[str, ControlTest]:
    """Load workpapers, enforcing the same rules the API applies on write."""
    loaded: dict[str, ControlTest] = {}
    for spec in CONTROL_TESTS:
        if spec.control_ref not in controls:
            raise ValueError(f"{spec.ref} references unknown control '{spec.control_ref}'")

        errors = validate_test(
            population_size=spec.population_size,
            sample_size=spec.sample_size,
            sample_selection_method=SampleSelectionMethod(spec.method),
            sampling_rationale=spec.sampling_rationale,
            exceptions_count=spec.exceptions_count,
            conclusion=TestConclusion(spec.conclusion),
            exception_details=spec.exception_details,
            tester=spec.tester,
            reviewed_by=spec.reviewed_by,
        )
        if errors:
            raise ValueError(f"{spec.ref} fails workpaper validation -- {errors[0].message}")

        conclusion = TestConclusion(spec.conclusion)
        if requires_finding(conclusion) and spec.finding_ref is None:
            raise ValueError(
                f"{spec.ref} concluded {conclusion.value} but raises no finding. A test that "
                "found something and reported nothing is worse than no test."
            )
        if not requires_finding(conclusion) and spec.finding_ref is not None:
            raise ValueError(f"{spec.ref} concluded PASS but links a finding")

        test = db.scalar(select(ControlTest).where(ControlTest.test_ref == spec.ref))
        if test is None:
            test = ControlTest(test_ref=spec.ref)
            db.add(test)
        test.control_id = controls[spec.control_ref].id
        test.tester = spec.tester
        test.test_date = spec.test_date
        test.period_covered_start = spec.period_start
        test.period_covered_end = spec.period_end
        test.test_objective = spec.objective
        test.test_procedure = spec.procedure
        test.population_description = spec.population_description
        test.population_size = spec.population_size
        test.sample_size = spec.sample_size
        test.sample_selection_method = SampleSelectionMethod(spec.method)
        test.sampling_rationale = spec.sampling_rationale
        test.results_summary = spec.results_summary
        test.exceptions_count = spec.exceptions_count
        test.exception_details = spec.exception_details
        test.conclusion = conclusion
        test.reviewed_by = spec.reviewed_by
        test.review_date = spec.review_date
        test.linked_finding_id = (
            findings[spec.finding_ref].id if spec.finding_ref else None
        )
        db.flush()

        wanted = set(spec.evidence)
        unknown = wanted - set(evidence)
        if unknown:
            raise ValueError(f"{spec.ref} links unknown evidence: {sorted(unknown)}")
        current = db.scalars(
            select(ControlTestEvidenceLink).where(
                ControlTestEvidenceLink.control_test_id == test.id
            )
        ).all()
        by_ref = {link.evidence.evidence_ref: link for link in current}
        for ref in wanted - set(by_ref):
            db.add(
                ControlTestEvidenceLink(control_test_id=test.id, evidence_id=evidence[ref].id)
            )
        for ref in set(by_ref) - wanted:
            db.delete(by_ref[ref])
        db.flush()
        loaded[spec.ref] = test

    # The control library's operating rating must agree with its most recent workpaper.
    # A control rated EFFECTIVE whose last test FAILED means one of the two is wrong,
    # and the workpaper is the record that survives an audit.
    by_control: dict[str, list] = {}
    for spec in CONTROL_TESTS:
        by_control.setdefault(spec.control_ref, []).append(spec)
    for control_ref, specs in by_control.items():
        latest = max(specs, key=lambda s: s.test_date)
        worst = min(
            specs,
            key=lambda s: ["FAIL", "PASS_WITH_EXCEPTIONS", "PASS"].index(s.conclusion),
        )
        control = controls[control_ref]
        control.last_tested = latest.test_date
        # Rate the control at its worst outstanding result, not its most recent one:
        # a later clean test on a different population does not undo an open exception.
        expected = CONCLUSION_TO_OPERATING[TestConclusion(worst.conclusion)]
        if control.operating_effectiveness != expected:
            raise ValueError(
                f"{control_ref} is rated {control.operating_effectiveness.value} but its "
                f"worst outstanding test ({worst.ref}) concluded {worst.conclusion}, which "
                f"implies {expected.value}."
            )
    db.flush()
    return loaded


def check_risk_bases_against_control_library(db: Session) -> list[str]:
    """A risk link may not claim a tested basis for a control nobody has tested.

    Returns the refs of links whose basis is *optimistic* -- stronger than the control
    library supports. Those are surfaced rather than blocked, because an analyst may be
    scoping to a population the exceptions did not touch.
    """
    optimistic: list[str] = []
    links = db.scalars(select(RiskControl)).all()
    for link in links:
        operating = link.control.operating_effectiveness
        if not basis_supported_by_control(link.effectiveness_basis, operating):
            raise ValueError(
                f"{link.risk.risk_ref} claims basis {link.effectiveness_basis.value} for "
                f"{link.control.control_id}, but the control library records that control as "
                "never tested."
            )
        if link.basis_is_optimistic:
            optimistic.append(f"{link.risk.risk_ref}/{link.control.control_id}")
    return sorted(optimistic)


def seed_isms_records(db: Session, findings: dict[str, AuditFinding]) -> tuple[int, int, int]:
    for spec in INTERNAL_AUDITS:
        audit = db.scalar(select(InternalAudit).where(InternalAudit.audit_ref == spec.ref))
        if audit is None:
            audit = InternalAudit(audit_ref=spec.ref)
            db.add(audit)
        audit.title = spec.title
        audit.scope = spec.scope
        audit.objectives = spec.objectives
        audit.criteria = spec.criteria
        audit.auditor = spec.auditor
        audit.independence_note = spec.independence_note
        audit.planned_start = spec.planned_start
        audit.planned_end = spec.planned_end
        audit.actual_start = spec.actual_start
        audit.actual_end = spec.actual_end
        audit.status = AuditStatus(spec.status)
        audit.outcome_summary = spec.outcome_summary

    for spec in MANAGEMENT_REVIEWS:
        review = db.scalar(
            select(ManagementReview).where(ManagementReview.review_ref == spec.ref)
        )
        if review is None:
            review = ManagementReview(review_ref=spec.ref)
            db.add(review)
        review.review_date = spec.review_date
        review.chair = spec.chair
        review.attendees = spec.attendees
        review.inputs_considered = spec.inputs_considered
        review.decisions = spec.decisions
        review.actions = spec.actions
        review.next_review_date = spec.next_review_date

    for spec in NONCONFORMITIES:
        nc = db.scalar(select(Nonconformity).where(Nonconformity.nc_ref == spec.ref))
        if nc is None:
            nc = Nonconformity(nc_ref=spec.ref)
            db.add(nc)
        nc.description = spec.description
        nc.source = FindingSource(spec.source)
        nc.identified_date = spec.identified_date
        nc.identified_by = spec.identified_by
        nc.owner = spec.owner
        nc.immediate_correction = spec.immediate_correction
        nc.root_cause_analysis = spec.root_cause_analysis
        nc.corrective_action = spec.corrective_action
        nc.target_date = spec.target_date
        nc.effectiveness_check_date = spec.effectiveness_check_date
        nc.effectiveness_check_result = spec.effectiveness_check_result
        nc.status = NonconformityStatus(spec.status)
        nc.closure_date = spec.closure_date
        nc.finding_id = findings[spec.finding_ref].id if spec.finding_ref else None
        # Clause 10.2 d): a nonconformity cannot be closed without evidence that the
        # corrective action actually worked.
        if nc.status == NonconformityStatus.CLOSED and not nc.effectiveness_check_result:
            raise ValueError(
                f"{spec.ref} is closed with no effectiveness check result. Clause 10.2 "
                "requires a review of whether the corrective action worked."
            )

    db.flush()
    return len(INTERNAL_AUDITS), len(MANAGEMENT_REVIEWS), len(NONCONFORMITIES)


def _sync(db: Session, link_model, parent_column, parent_id, ref_attr, lookup, fk, wanted):
    """Reconcile a set of link rows against the refs the seed asks for."""
    unknown = set(wanted) - set(lookup)
    if unknown:
        raise ValueError(f"links reference unknown records: {sorted(unknown)}")
    current = db.scalars(select(link_model).where(parent_column == parent_id)).all()
    by_ref = {getattr(getattr(link, ref_attr[0]), ref_attr[1]): link for link in current}
    for ref in set(wanted) - set(by_ref):
        db.add(link_model(**{parent_column.key: parent_id, fk: lookup[ref].id}))
    for ref in set(by_ref) - set(wanted):
        db.delete(by_ref[ref])
    db.flush()


def seed_assets(db: Session) -> dict[str, Asset]:
    loaded: dict[str, Asset] = {}
    for order, spec in enumerate(ASSETS, start=1):
        asset = db.scalar(select(Asset).where(Asset.asset_ref == spec.ref))
        if asset is None:
            asset = Asset(asset_ref=spec.ref)
            db.add(asset)
        asset.name = spec.name
        asset.description = spec.description
        asset.asset_type = AssetType(spec.asset_type)
        asset.classification = Classification(spec.classification)
        asset.owner_role = spec.owner_role
        asset.hosting_location = spec.hosting_location
        asset.holds_personal_data = spec.holds_personal_data
        asset.sort_order = order
        db.flush()
        loaded[spec.ref] = asset
    return loaded


def seed_risk_exceptions(db: Session, risks: dict[str, Risk]) -> dict[str, RiskException]:
    loaded: dict[str, RiskException] = {}
    for spec in RISK_EXCEPTIONS:
        if spec.risk_ref not in risks:
            raise ValueError(f"{spec.ref} references unknown risk '{spec.risk_ref}'")
        risk = risks[spec.risk_ref]

        errors = validate_exception(
            approver_role=spec.approver_role,
            risk_owner_role=risk.owner_role,
            expiry_date=spec.expiry_date,
            approval_date=spec.approval_date,
            business_justification=spec.business_justification,
            review_trigger=spec.review_trigger,
            status=ExceptionStatus(spec.status),
        )
        if errors:
            raise ValueError(f"{spec.ref} fails validation -- {errors[0].message}")

        exception = db.scalar(
            select(RiskException).where(RiskException.exception_ref == spec.ref)
        )
        if exception is None:
            exception = RiskException(exception_ref=spec.ref)
            db.add(exception)
        exception.risk_id = risk.id
        exception.requested_by = spec.requested_by
        exception.business_justification = spec.business_justification
        exception.compensating_controls = spec.compensating_controls
        exception.approver_role = spec.approver_role
        exception.approval_date = spec.approval_date
        exception.expiry_date = spec.expiry_date
        exception.review_trigger = spec.review_trigger
        exception.status = ExceptionStatus(spec.status)
        exception.decision_note = spec.decision_note
        db.flush()
        loaded[spec.ref] = exception
    return loaded


def seed_ropa(
    db: Session,
    assets: dict[str, Asset],
    risks: dict[str, Risk],
    controls: dict[str, Control],
) -> dict[str, RopaEntry]:
    loaded: dict[str, RopaEntry] = {}
    for spec in ROPA_ENTRIES:
        errors = validate_ropa(
            transfers_outside_eea=spec.transfers_outside_eea,
            transfer_safeguard=TransferSafeguard(spec.transfer_safeguard),
            transfer_detail=spec.transfer_detail,
            retention_period=spec.retention_period,
            lawful_basis=LawfulBasis(spec.lawful_basis),
            legitimate_interests_assessment=spec.legitimate_interests_assessment,
        )
        if errors:
            raise ValueError(f"{spec.ref} fails Article 30 validation -- {errors[0].message}")

        entry = db.scalar(select(RopaEntry).where(RopaEntry.ropa_ref == spec.ref))
        if entry is None:
            entry = RopaEntry(ropa_ref=spec.ref)
            db.add(entry)
        entry.processing_activity = spec.processing_activity
        entry.purpose = spec.purpose
        entry.lawful_basis = LawfulBasis(spec.lawful_basis)
        entry.legitimate_interests_assessment = spec.legitimate_interests_assessment
        entry.data_subject_categories = spec.data_subject_categories
        entry.personal_data_categories = spec.personal_data_categories
        entry.special_category_data = spec.special_category_data
        entry.recipients = spec.recipients
        entry.transfers_outside_eea = spec.transfers_outside_eea
        entry.transfer_detail = spec.transfer_detail
        entry.transfer_safeguard = TransferSafeguard(spec.transfer_safeguard)
        entry.retention_period = spec.retention_period
        entry.security_measures_summary = spec.security_measures_summary
        entry.controller_role = spec.controller_role
        entry.owner_role = spec.owner_role
        entry.last_reviewed = spec.last_reviewed
        db.flush()

        _sync(db, RopaAssetLink, RopaAssetLink.ropa_id, entry.id, ("asset", "asset_ref"),
              assets, "asset_id", set(spec.assets))
        _sync(db, RopaRiskLink, RopaRiskLink.ropa_id, entry.id, ("risk", "risk_ref"),
              risks, "risk_id", set(spec.risks))
        _sync(db, RopaControlLink, RopaControlLink.ropa_id, entry.id, ("control", "control_id"),
              controls, "control_id", set(spec.controls))
        loaded[spec.ref] = entry
    return loaded


def seed_dpias(
    db: Session, assets: dict[str, Asset], risks: dict[str, Risk], ropa: dict[str, RopaEntry]
) -> dict[str, Dpia]:
    loaded: dict[str, Dpia] = {}
    for spec in DPIAS:
        errors = validate_dpia(
            outcome=DpiaOutcome(spec.outcome),
            residual_risk=ResidualRiskLevel(spec.residual_risk),
            dpo_consulted=spec.dpo_consulted,
            supervisory_authority_consulted=spec.supervisory_authority_consulted,
            mitigating_measures=spec.mitigating_measures,
            review_date=spec.review_date,
        )
        if errors:
            raise ValueError(f"{spec.ref} fails Article 35/36 validation -- {errors[0].message}")

        dpia = db.scalar(select(Dpia).where(Dpia.dpia_ref == spec.ref))
        if dpia is None:
            dpia = Dpia(dpia_ref=spec.ref)
            db.add(dpia)
        dpia.title = spec.title
        dpia.ropa_id = ropa[spec.ropa_ref].id if spec.ropa_ref else None
        dpia.trigger_reason = spec.trigger_reason
        dpia.processing_description = spec.processing_description
        dpia.necessity_and_proportionality = spec.necessity_and_proportionality
        dpia.risks_to_data_subjects = spec.risks_to_data_subjects
        dpia.mitigating_measures = spec.mitigating_measures
        dpia.residual_risk = ResidualRiskLevel(spec.residual_risk)
        dpia.residual_risk_note = spec.residual_risk_note
        dpia.dpo_consulted = spec.dpo_consulted
        dpia.dpo_advice = spec.dpo_advice
        dpia.supervisory_authority_consulted = spec.supervisory_authority_consulted
        dpia.data_subjects_consulted = spec.data_subjects_consulted
        dpia.outcome = DpiaOutcome(spec.outcome)
        dpia.assessed_by = spec.assessed_by
        dpia.assessment_date = spec.assessment_date
        dpia.review_date = spec.review_date
        db.flush()

        _sync(db, DpiaAssetLink, DpiaAssetLink.dpia_id, dpia.id, ("asset", "asset_ref"),
              assets, "asset_id", set(spec.assets))
        _sync(db, DpiaRiskLink, DpiaRiskLink.dpia_id, dpia.id, ("risk", "risk_ref"),
              risks, "risk_id", set(spec.risks))
        loaded[spec.ref] = dpia
    return loaded


def seed_bia(
    db: Session,
    assets: dict[str, Asset],
    controls: dict[str, Control],
    risks: dict[str, Risk],
) -> dict[str, BusinessImpactAnalysis]:
    loaded: dict[str, BusinessImpactAnalysis] = {}
    for spec in BIA_PROCESSES:
        errors = validate_bia(
            rto_hours=spec.rto_hours, rpo_hours=spec.rpo_hours, mtpd_hours=spec.mtpd_hours
        )
        if errors:
            raise ValueError(f"{spec.ref} fails BIA validation -- {errors[0].message}")

        bia = db.scalar(
            select(BusinessImpactAnalysis).where(BusinessImpactAnalysis.bia_ref == spec.ref)
        )
        if bia is None:
            bia = BusinessImpactAnalysis(bia_ref=spec.ref)
            db.add(bia)
        bia.process_name = spec.process_name
        bia.process_description = spec.process_description
        bia.owner_role = spec.owner_role
        bia.rto_hours = spec.rto_hours
        bia.rpo_hours = spec.rpo_hours
        bia.mtpd_hours = spec.mtpd_hours
        bia.currency = "GBP"
        bia.impact_1h = spec.impact_1h
        bia.impact_24h = spec.impact_24h
        bia.impact_1w = spec.impact_1w
        bia.impact_note = spec.impact_note
        bia.workaround = spec.workaround
        bia.recovery_note = spec.recovery_note
        bia.last_reviewed = spec.last_reviewed
        db.flush()

        _sync(db, BiaAssetLink, BiaAssetLink.bia_id, bia.id, ("asset", "asset_ref"),
              assets, "asset_id", set(spec.assets))
        _sync(db, BiaControlLink, BiaControlLink.bia_id, bia.id, ("control", "control_id"),
              controls, "control_id", set(spec.controls))
        _sync(db, BiaRiskLink, BiaRiskLink.bia_id, bia.id, ("risk", "risk_ref"),
              risks, "risk_id", set(spec.risks))
        loaded[spec.ref] = bia
    return loaded


def seed_users(db: Session) -> int:
    """Create the demo accounts.

    Passwords are re-hashed on every run rather than left alone, so a deployment that
    changes the demo password in settings actually takes effect.
    """
    settings = get_settings()
    for spec in DEMO_USERS:
        user = db.scalar(select(User).where(User.username == spec.username))
        if user is None:
            user = User(username=spec.username)
            db.add(user)
        user.full_name = spec.full_name
        user.email = spec.email
        user.role = Role(spec.role)
        user.is_active = True
        user.hashed_password = hash_password(getattr(settings, spec.password_setting))
    db.flush()
    return len(DEMO_USERS)


def seed_kris(db: Session) -> int:
    for order, spec in enumerate(KRI_DEFINITIONS, start=1):
        definition = db.scalar(
            select(KriDefinition).where(KriDefinition.kri_ref == spec.ref)
        )
        if definition is None:
            definition = KriDefinition(kri_ref=spec.ref)
            db.add(definition)
        definition.name = spec.name
        definition.formula_description = spec.formula_description
        definition.data_source = spec.data_source
        definition.rationale = spec.rationale
        definition.unit = KriUnit(spec.unit)
        definition.direction = KriDirection(spec.direction)
        definition.green_threshold = spec.green_threshold
        definition.amber_threshold = spec.amber_threshold
        definition.owner_role = spec.owner_role
        definition.measurement_frequency = MeasurementFrequency(spec.frequency)
        definition.sort_order = order

        # A HIGHER_IS_BETTER indicator whose amber floor sits above its green floor would
        # classify nothing as amber; the reverse for LOWER_IS_BETTER.
        if definition.direction == KriDirection.HIGHER_IS_BETTER:
            if definition.amber_threshold > definition.green_threshold:
                raise ValueError(f"{spec.ref}: amber threshold must be below green")
        elif definition.amber_threshold < definition.green_threshold:
            raise ValueError(f"{spec.ref}: amber threshold must be above green")
        db.flush()

        for period_end, value in spec.history:
            measurement = db.scalar(
                select(KriMeasurement).where(
                    KriMeasurement.kri_id == definition.id,
                    KriMeasurement.period_end == period_end,
                )
            )
            if measurement is None:
                measurement = KriMeasurement(kri_id=definition.id, period_end=period_end)
                db.add(measurement)
            measurement.value = value
        db.flush()
    return len(KRI_DEFINITIONS)


def main() -> None:
    with SessionLocal() as db:
        iso = seed_iso(db)
        soc2 = seed_soc2(db)
        seed_roadmap_frameworks(db)
        created = seed_mappings(db, iso, soc2)
        controls = seed_internal_controls(db, iso)
        thresholds = seed_appetite(db)
        risks = seed_risks(db, controls)
        risk_map = {r.risk_ref: r for r in db.scalars(select(Risk)).all()}
        evidence = seed_evidence(db, controls)
        remediation = seed_remediation(db)
        soa = seed_soa(db, iso, controls, risk_map, evidence, remediation)
        findings = seed_findings(db, controls, remediation)
        tests = seed_control_tests(db, controls, evidence, findings)
        optimistic = check_risk_bases_against_control_library(db)
        audits, reviews, ncs = seed_isms_records(db, findings)
        assets = seed_assets(db)
        exceptions = seed_risk_exceptions(db, risk_map)
        ropa = seed_ropa(db, assets, risk_map, controls)
        dpias = seed_dpias(db, assets, risk_map, ropa)
        bia = seed_bia(db, assets, controls, risk_map)
        users = seed_users(db)
        kris = seed_kris(db)
        db.commit()

    excluded = sum(1 for c in iso.values() if not c.in_scope)
    print(f"  frameworks         : {len(FRAMEWORKS)}")
    print(f"  ISO Annex A        : {len(iso)} controls ({excluded} provisionally out of scope)")
    print(f"  SOC 2 criteria     : {len(soc2)}")
    print(f"  ISO -> SOC 2 links : {len(ISO_TO_SOC2)} ({created} new)")
    print(f"  internal controls  : {len(controls)}")
    print(f"  appetite thresholds: {thresholds}")
    print(f"  risks              : {risks}")
    print(f"  evidence artifacts : {len(evidence)}")
    print(f"  remediation items  : {len(remediation)}")
    print(f"  SoA entries        : {len(soa)}")
    print(f"  control tests      : {len(tests)}")
    print(f"  audit findings     : {len(findings)}")
    print(f"  internal audits    : {audits}")
    print(f"  management reviews : {reviews}")
    print(f"  nonconformities    : {ncs}")
    print(f"  assets             : {len(assets)}")
    print(f"  risk exceptions    : {len(exceptions)}")
    print(f"  RoPA entries       : {len(ropa)}")
    print(f"  DPIAs              : {len(dpias)}")
    print(f"  BIA processes      : {len(bia)}")
    print(f"  demo users         : {users}")
    print(f"  KRI definitions    : {kris}")
    if optimistic:
        print(f"  optimistic bases   : {len(optimistic)} {optimistic}")


if __name__ == "__main__":
    main()
