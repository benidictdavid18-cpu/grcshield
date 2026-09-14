"""The executive view.

Written for someone who does not know what Annex A is and should not have to. Rules for
everything in here:

  - No control identifiers in the prose. "A.8.5" means nothing to a board member.
  - No band names as nouns. "High" is jargon; "one of the five most serious" is not.
  - Every recommendation names what to do, who does it, and what it buys.

The numbers are the same numbers the rest of the application uses. This is a different
audience, not a different set of facts.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditFinding
from app.models.privacy import RiskException
from app.models.risk import Risk, RiskAppetiteThreshold
from app.models.soa import (
    ImplementationStatus,
    RemediationItem,
    SoAEntry,
)
from app.services.control_testing import FindingSeverity
from app.services.privacy_continuity import ExceptionStatus, exception_state
from app.services.risk_scoring import CATEGORY_LABELS, RiskBand

_POSTURE = {
    "STRAINED": (
        "Security posture is strained. Several significant exposures are open at once, "
        "and more of them are being carried without a decision than are being actively "
        "fixed."
    ),
    "MIXED": (
        "Security posture is mixed. The foundations are in place and most controls work, "
        "but a small number of significant exposures remain open and are holding back "
        "certification."
    ),
    "SOUND": (
        "Security posture is sound. Controls are largely implemented and tested, and no "
        "exposure currently sits outside what the business has agreed to carry."
    ),
}


@dataclass(frozen=True)
class TopRisk:
    risk_ref: str
    plain_title: str
    what_could_happen: str
    who_owns_it: str
    beyond_agreed_limit: bool


@dataclass(frozen=True)
class Priority:
    headline: str
    why: str
    owner: str
    by_when: str


def _band_words(band: RiskBand) -> str:
    return {
        RiskBand.CRITICAL: "the most serious level we record",
        RiskBand.HIGH: "serious",
        RiskBand.MEDIUM: "moderate",
        RiskBand.LOW: "minor",
    }[band]


def build(db: Session, as_of: date) -> dict:
    thresholds = {t.category: t for t in db.scalars(select(RiskAppetiteThreshold)).all()}
    risks = db.scalars(select(Risk)).all()
    entries = db.scalars(select(SoAEntry)).all()
    findings = [f for f in db.scalars(select(AuditFinding)).all() if f.is_open]
    remediation = db.scalars(select(RemediationItem)).all()
    exceptions = db.scalars(select(RiskException)).all()

    breaching = [r for r in risks if r.exceeds(thresholds.get(r.category))]
    applicable = [e for e in entries if e.applicable]
    implemented = [
        e for e in applicable if e.implementation_status == ImplementationStatus.IMPLEMENTED
    ]
    open_remediation = [r for r in remediation if r.is_open]
    overdue = [r for r in open_remediation if r.is_overdue(as_of)]

    live_acceptance = {
        e.risk_id
        for e in exceptions
        if exception_state(e.expiry_date, ExceptionStatus(e.status), as_of)
        in ("APPROVED", "PENDING", "EXPIRING_SOON")
    }
    uncovered = [r for r in breaching if r.id not in live_acceptance]

    posture_key = "SOUND"
    if breaching:
        posture_key = "STRAINED" if len(uncovered) >= 5 else "MIXED"

    top_risks = [
        TopRisk(
            risk_ref=risk.risk_ref,
            plain_title=risk.title,
            what_could_happen=(
                f"If this happened it would be {_band_words(risk.residual_band)}, even "
                "after the protections already in place."
            ),
            who_owns_it=risk.owner_role,
            beyond_agreed_limit=bool(risk.exceeds(thresholds.get(risk.category))),
        )
        for risk in sorted(risks, key=lambda r: r.residual_score, reverse=True)[:5]
    ]

    # Gaps ranked by how much is riding on them: a control that several risks depend on
    # matters more than one that nothing points at.
    gap_entries = [e for e in applicable if e.is_gap]
    top_gaps = sorted(
        gap_entries,
        key=lambda e: (len(e.linked_risks), e.implementation_status.value),
        reverse=True,
    )[:5]

    third_party_risks = [r for r in risks if r.category.value == "THIRD_PARTY"]
    third_party_breaching = [r for r in third_party_risks if r in breaching]

    priorities: list[Priority] = []
    mfa_risk = next((r for r in risks if r.risk_ref == "RISK-004"), None)
    if mfa_risk and mfa_risk.exceeds(thresholds.get(mfa_risk.category)):
        priorities.append(
            Priority(
                headline="Finish locking down administrator access to the live system",
                why=(
                    "Four in ten administrator accounts can still be used with only a "
                    "password. Anyone who obtains one of those passwords reaches "
                    "everything, including customer data. Leadership has already declined "
                    "to accept this, and it is the single largest obstacle to "
                    "certification."
                ),
                owner=mfa_risk.owner_role,
                by_when="Before the certification audit",
            )
        )
    if uncovered:
        priorities.append(
            Priority(
                headline="Decide what to do about exposures nobody has signed off",
                why=(
                    f"{len(uncovered)} exposures currently sit beyond the limits the "
                    "business set, with no one having formally agreed to carry them. Each "
                    "needs either funded work to reduce it or a dated, signed decision to "
                    "live with it. Carrying a risk without deciding to is the worst of "
                    "both options."
                ),
                owner="Chief Operating Officer",
                by_when="Next management review",
            )
        )
    if overdue or len(implemented) < len(applicable):
        outstanding = len(applicable) - len(implemented)
        priorities.append(
            Priority(
                headline="Close the remaining certification gaps and clear overdue work",
                why=(
                    f"{outstanding} of the {len(applicable)} required safeguards are not "
                    f"yet fully in place, and {len(overdue)} pieces of remediation are past "
                    "their due date. Certification is a funded commercial objective and "
                    "enterprise customers are waiting on it."
                ),
                owner="Head of Legal & Compliance",
                by_when="This quarter",
            )
        )

    return {
        "as_of": as_of,
        "posture_statement": _POSTURE[posture_key],
        "posture_key": posture_key,
        "risks_total": len(risks),
        "risks_beyond_agreed_limit": len(breaching),
        "risks_carried_without_a_decision": len(uncovered),
        "safeguards_required": len(applicable),
        "safeguards_in_place": len(implemented),
        "safeguards_percent": (
            round(100 * len(implemented) / len(applicable), 1) if applicable else 0.0
        ),
        "top_risks": top_risks,
        "top_gaps": [
            {
                "what_is_missing": e.control_title,
                "detail": e.implementation_description or "",
                "risks_depending_on_it": len(e.linked_risks),
                "owner": e.owner,
            }
            for e in top_gaps
        ],
        "open_findings_by_severity": {
            s.value: sum(1 for f in findings if f.severity == s) for s in FindingSeverity
        },
        "open_findings_total": len(findings),
        "remediation_open": len(open_remediation),
        "remediation_overdue": len(overdue),
        "third_party": {
            "risks_tracked": len(third_party_risks),
            "beyond_agreed_limit": len(third_party_breaching),
            "summary": (
                "FinFlow runs on other companies' software, and cannot inspect their "
                "security directly. It relies on choosing carefully, reading the "
                "independent reports those suppliers publish, and putting obligations in "
                "the contract. One supplier report has expired and needs replacing; until "
                "it does, part of the assurance we rely on is out of date."
            ),
        },
        "categories": {
            CATEGORY_LABELS[c]: sum(1 for r in risks if r.category == c)
            for c in {r.category for r in risks}
        },
        "priorities": priorities[:3],
    }
