"""Risk acceptance register.

Four exceptions. One has already expired (EXC-003), one expires within thirty days
(EXC-001), one is healthy, and one was refused at management review (EXC-004) — because
a register that only records approvals is a record of agreement, not of decisions.

Every approver is the owner of the linked risk or the Chief Executive Officer. None is
the security function: security advises on risk, the business decides to carry it.
"""

from datetime import date
from typing import NamedTuple


class ExceptionSpec(NamedTuple):
    ref: str
    risk_ref: str
    requested_by: str
    business_justification: str
    compensating_controls: str
    approver_role: str
    approval_date: date | None
    expiry_date: date
    review_trigger: str
    status: str
    decision_note: str | None


RISK_EXCEPTIONS: list[ExceptionSpec] = [
    ExceptionSpec(
        "EXC-001", "RISK-003",
        "Head of Engineering",
        "Integrating a secondary payment service provider is estimated at one engineer for "
        "a full quarter, plus a second commercial negotiation and a second compliance "
        "review. At current transaction volume the expected cost of a PSP outage over "
        "twelve months is materially lower than that build cost, and the engineering "
        "quarter is committed to the certification programme. The business accepts "
        "processing downtime during a provider outage until volumes justify redundancy.",
        "TP-002 obtains and reviews the provider's assurance report annually; the "
        "provider's contract carries availability commitments with service credits. "
        "Merchant-facing status communication is covered by IR-001.",
        "Chief Operating Officer", date(2026, 3, 6), date(2026, 9, 5),
        "Revisit immediately if monthly transaction volume exceeds 250,000, if the "
        "provider reports an availability breach, or if an enterprise contract commits "
        "FinFlow to an uptime figure the single provider cannot support.",
        "APPROVED", None,
    ),
    ExceptionSpec(
        "EXC-002", "RISK-007",
        "Chief Technology Officer",
        "Active-active multi-region operation would roughly double infrastructure spend "
        "and require re-architecting the ledger for cross-region consistency. The board "
        "has judged that a regional AWS failure is rare enough, and FinFlow's recovery "
        "objectives loose enough, that the spend is not warranted at this stage. This is "
        "the decision that sets Business Continuity appetite at High.",
        "OP-005 maintains cross-region backup copies and restore is exercised on schedule "
        "(TEST-012 completed a restore in 47 minutes). OP-006 provides multi-AZ redundancy "
        "against the far more likely single-zone failure.",
        "Chief Executive Officer", date(2026, 6, 24), date(2027, 6, 30),
        "Revisit if an enterprise contract requires a recovery time objective below four "
        "hours, if AWS eu-west-1 suffers a regional outage of any length, or at the next "
        "funding round when infrastructure budget is reset. Note that BIA-001 records a "
        "two-hour RTO for payment processing which this acceptance does not currently "
        "support for a regional loss.",
        "APPROVED", None,
    ),
    ExceptionSpec(
        "EXC-003", "RISK-010",
        "Head of Legal & Compliance",
        "FinFlow cannot test the controls of its critical SaaS vendors directly and has no "
        "commercial leverage to demand more than their standard assurance reporting. The "
        "residual exposure to a vendor-side breach is accepted, with contractual "
        "notification obligations and cyber insurance carrying the financial consequence.",
        "TP-001 gates vendor selection, TP-002 reviews assurance reports annually, TP-003 "
        "places breach notification obligations in contract. Cyber insurance covers "
        "third-party breach costs to the policy limit.",
        "Chief Operating Officer", date(2025, 12, 15), date(2026, 6, 30),
        "Revisit on any vendor security incident, on material change to the vendor set, or "
        "at annual insurance renewal.",
        "EXPIRED",
        "Expired on 30 June 2026 and not renewed. RISK-010 currently sits above the "
        "Third-Party appetite ceiling with no live acceptance covering it, which means the "
        "exposure is being carried without a decision. Raised at MR-2026-H1 for renewal or "
        "treatment.",
    ),
    ExceptionSpec(
        "EXC-004", "RISK-004",
        "Head of Engineering",
        "Requested a time-boxed acceptance of the privileged MFA gap until after the "
        "certification programme, on the grounds that the remaining six accounts are held "
        "by long-tenured engineers and the legacy IAM users are needed by the deployment "
        "pipeline.",
        "OP-002 alerts on anomalous privileged activity; AC-004 reviews entitlements "
        "quarterly. Both are detective rather than preventive.",
        "Chief Technology Officer", None, date(2027, 3, 31),
        "Not applicable — the request was refused.",
        "REJECTED",
        "Refused at MR-2026-H1 on 24 June 2026. The Chief Technology Officer's recorded "
        "reason: accepting a known privileged access gap while seeking ISO 27001 "
        "certification is not defensible to an auditor, and the compensating controls are "
        "detective only, so they shorten the incident rather than prevent it. REM-001 must "
        "close before the Stage 1 audit.",
    ),
]
