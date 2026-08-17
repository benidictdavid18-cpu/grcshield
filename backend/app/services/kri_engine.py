"""Live computation of the KRI set.

Every value here is derived from the registers, not stored and hoped for. The seeded
measurement history is what was recorded in past periods; the current period is computed
on request, so the dashboard cannot drift away from the data behind it.

``None`` means "nothing to measure", and is rendered as NO_DATA rather than zero. A
metric with an empty population is not performing perfectly.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditFinding, ControlTest
from app.models.kri import KriDefinition
from app.models.privacy import RiskException
from app.models.risk import Control, Risk, RiskAppetiteThreshold
from app.models.soa import (
    Evidence,
    ImplementationStatus,
    RemediationItem,
    RemediationPriority,
    RemediationStatus,
    SoAEntry,
)
from app.services.control_testing import FindingSeverity, OperatingEffectiveness
from app.services.privacy_continuity import ExceptionStatus, exception_state

# A control is "current" if it has been tested within this window.
TEST_CURRENCY_DAYS = 365


@dataclass(frozen=True)
class ComputedKri:
    value: float | None
    detail: str


def _pct(numerator: int, denominator: int) -> float | None:
    return round(100 * numerator / denominator, 1) if denominator else None


def privileged_mfa_coverage(db: Session) -> ComputedKri:
    """Percentage of privileged accounts with a phishing-resistant factor enforced.

    Sourced from the most recent workpaper covering AC-002's privileged population,
    because the enrolment report behind it is the only evidence that distinguishes
    'MFA is configured' from 'MFA is enforced on every path'.
    """
    tests = db.scalars(
        select(ControlTest)
        .join(Control)
        .where(Control.control_id == "AC-002")
        .order_by(ControlTest.test_date.desc())
    ).all()
    privileged = [t for t in tests if "privileged" in t.test_objective.lower()]
    if not privileged:
        return ComputedKri(None, "No workpaper covers the privileged account population.")

    latest = privileged[0]
    covered = latest.sample_size - latest.exceptions_count
    return ComputedKri(
        _pct(covered, latest.sample_size),
        f"{covered} of {latest.sample_size} privileged accounts, per {latest.test_ref} "
        f"({latest.test_date}).",
    )


def mean_time_to_remediate(db: Session, as_of: date) -> ComputedKri:
    """Mean days from raised to closed for Critical and High priority remediation.

    Measured over items closed in the trailing 12 months. FinFlow has recorded no
    Critical priority items to date, so High is included to keep the metric measurable —
    the substitution is stated rather than hidden behind an empty chart.
    """
    cutoff = as_of - timedelta(days=365)
    items = db.scalars(
        select(RemediationItem).where(
            RemediationItem.status == RemediationStatus.COMPLETED,
            RemediationItem.priority.in_(
                [RemediationPriority.CRITICAL, RemediationPriority.HIGH]
            ),
        )
    ).all()
    closed = [
        item
        for item in items
        if item.completed_date and item.raised_date and item.completed_date >= cutoff
    ]
    if not closed:
        return ComputedKri(None, "No Critical or High priority items closed in the period.")

    days = [(item.completed_date - item.raised_date).days for item in closed]
    return ComputedKri(
        round(sum(days) / len(days), 1),
        f"{len(closed)} item(s) closed: " + ", ".join(
            f"{item.remediation_ref} {d}d" for item, d in zip(closed, days, strict=True)
        ),
    )


def soa_implementation(db: Session) -> ComputedKri:
    entries = db.scalars(select(SoAEntry)).all()
    applicable = [e for e in entries if e.applicable]
    implemented = [
        e for e in applicable if e.implementation_status == ImplementationStatus.IMPLEMENTED
    ]
    return ComputedKri(
        _pct(len(implemented), len(applicable)),
        f"{len(implemented)} of {len(applicable)} applicable Annex A controls implemented. "
        "Excluded controls are not in the denominator.",
    )


def control_test_currency(db: Session, as_of: date) -> ComputedKri:
    """Percentage of controls tested within their required frequency.

    All controls carry an annual testing requirement, so a control never tested is not
    current. Rating a control from configuration review is legitimate; calling it tested
    is not.
    """
    controls = db.scalars(select(Control)).all()
    if not controls:
        return ComputedKri(None, "No controls in the library.")
    cutoff = as_of - timedelta(days=TEST_CURRENCY_DAYS)
    current = [c for c in controls if c.last_tested and c.last_tested >= cutoff]
    never = sum(
        1 for c in controls if c.operating_effectiveness == OperatingEffectiveness.NOT_TESTED
    )
    return ComputedKri(
        _pct(len(current), len(controls)),
        f"{len(current)} of {len(controls)} controls tested within {TEST_CURRENCY_DAYS} days. "
        f"{never} have never had operating effectiveness tested at all.",
    )


def risks_above_appetite(db: Session) -> ComputedKri:
    thresholds = {t.category: t for t in db.scalars(select(RiskAppetiteThreshold)).all()}
    risks = db.scalars(select(Risk)).all()
    breaching = [r for r in risks if r.exceeds(thresholds.get(r.category))]
    return ComputedKri(
        float(len(breaching)),
        ", ".join(r.risk_ref for r in breaching) or "No risk exceeds its category appetite.",
    )


def evidence_within_validity(db: Session, as_of: date) -> ComputedKri:
    artifacts = db.scalars(select(Evidence)).all()
    if not artifacts:
        return ComputedKri(None, "No evidence recorded.")
    valid = [a for a in artifacts if not a.is_expired(as_of)]
    expired = [a.evidence_ref for a in artifacts if a.is_expired(as_of)]
    return ComputedKri(
        _pct(len(valid), len(artifacts)),
        f"{len(valid)} of {len(artifacts)} artifacts within their validity period."
        + (f" Expired: {', '.join(sorted(expired))}." if expired else ""),
    )


def expired_exceptions(db: Session, as_of: date) -> ComputedKri:
    rows = db.scalars(select(RiskException)).all()
    expired = [
        row
        for row in rows
        if exception_state(row.expiry_date, ExceptionStatus(row.status), as_of) == "EXPIRED"
    ]
    return ComputedKri(
        float(len(expired)),
        ", ".join(f"{row.exception_ref} (expired {row.expiry_date})" for row in expired)
        or "No acceptance is past its expiry date.",
    )


def open_findings_by_severity(db: Session) -> dict[str, int]:
    findings = [f for f in db.scalars(select(AuditFinding)).all() if f.is_open]
    return {s.value: sum(1 for f in findings if f.severity == s) for s in FindingSeverity}


# kri_ref -> callable(db, as_of) -> ComputedKri
COMPUTERS = {
    "KRI-001": lambda db, as_of: privileged_mfa_coverage(db),
    "KRI-002": mean_time_to_remediate,
    "KRI-003": lambda db, as_of: soa_implementation(db),
    "KRI-004": control_test_currency,
    "KRI-005": lambda db, as_of: risks_above_appetite(db),
    "KRI-006": evidence_within_validity,
    "KRI-007": expired_exceptions,
}


def compute(db: Session, definition: KriDefinition, as_of: date) -> ComputedKri:
    computer = COMPUTERS.get(definition.kri_ref)
    if computer is None:
        return ComputedKri(None, "No computation is defined for this indicator.")
    return computer(db, as_of)
