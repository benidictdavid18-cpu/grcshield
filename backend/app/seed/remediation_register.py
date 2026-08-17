"""Remediation register.

Every SoA gap — applicable but not fully implemented — must point at one of these.
Items may cover several controls, because real remediation work usually closes a
cluster of related gaps rather than exactly one.

Two items are deliberately overdue as of the assessment date (2026-08-15): REM-006 and
REM-017. Two are completed (REM-018, REM-019) and remain linked to the controls they
closed, so the SoA carries its own history rather than only its current state.
"""

from datetime import date
from typing import NamedTuple


class RemediationSpec(NamedTuple):
    ref: str
    title: str
    description: str
    owner: str
    due_date: date
    status: str
    priority: str
    source: str
    completed_date: date | None
    # Only recorded on closed items, because that is where it is needed: mean time to
    # remediate is measured over completed work. Backfilling a raised date onto open
    # items would be inventing history.
    raised_date: date | None = None


REMEDIATION_ITEMS: list[RemediationSpec] = [
    RemediationSpec(
        "REM-001",
        "Enforce MFA on all privileged accounts and remove legacy bypass paths",
        "Six of fifteen privileged accounts still authenticate without a "
        "phishing-resistant factor, and several legacy access paths bypass the Okta "
        "sign-on policy entirely. Close both before certification.",
        "Head of Engineering", date(2026, 10, 31),
        "IN_PROGRESS", "HIGH", "RISK_TREATMENT", None,
    ),
    RemediationSpec(
        "REM-002",
        "Rebuild the Record of Processing Activities with a change trigger",
        "The RoPA was compiled once and has no mechanism to capture new processing. "
        "Rebuild it and tie an update trigger to the product launch checklist.",
        "Head of Legal & Compliance", date(2026, 11, 28),
        "IN_PROGRESS", "HIGH", "RISK_TREATMENT", None,
    ),
    RemediationSpec(
        "REM-003",
        "Finalise and exercise the business continuity plan",
        "The plan is at draft v0.9 and has never been exercised, so continuity controls "
        "cannot be assessed beyond design. Approve it and run a tabletop covering loss "
        "of region and loss of the identity provider.",
        "Chief Operating Officer", date(2026, 12, 19),
        "OPEN", "MEDIUM", "SOA_GAP", None,
    ),
    RemediationSpec(
        "REM-004",
        "Stand up the internal audit programme and management review cycle",
        "No independent review of the ISMS has been performed. Define the audit "
        "programme, schedule the first cycle, and record the independence basis for "
        "the auditor.",
        "Head of Legal & Compliance", date(2027, 1, 30),
        "OPEN", "HIGH", "SOA_GAP", None,
    ),
    RemediationSpec(
        "REM-005",
        "Deploy data loss prevention controls on egress paths",
        "No DLP capability exists on email, endpoints or the support tooling. Scope and "
        "deploy detection on the paths that carry customer personal data.",
        "Head of Engineering", date(2027, 2, 27),
        "OPEN", "MEDIUM", "SOA_GAP", None,
    ),
    RemediationSpec(
        "REM-006",
        "Implement information labelling in line with the classification policy",
        "Classification tiers are defined but nothing is labelled, so handling rules "
        "cannot be applied consistently. Apply labels to document stores and data "
        "stores. OVERDUE.",
        "Head of Legal & Compliance", date(2026, 7, 31),
        "IN_PROGRESS", "LOW", "SOA_GAP", None,
    ),
    RemediationSpec(
        "REM-007",
        "Establish an authority and special-interest-group contact register",
        "There is no recorded contact point for the supervisory authority, law "
        "enforcement or sector groups, which would slow any regulatory notification.",
        "Head of Legal & Compliance", date(2026, 10, 16),
        "OPEN", "LOW", "SOA_GAP", None,
    ),
    RemediationSpec(
        "REM-008",
        "Formalise a threat intelligence intake process",
        "Threat information is consumed ad hoc by individual engineers. Define sources, "
        "a review cadence and how intelligence feeds the risk assessment.",
        "Head of Engineering", date(2026, 12, 11),
        "OPEN", "MEDIUM", "SOA_GAP", None,
    ),
    RemediationSpec(
        "REM-009",
        "Complete the asset inventory and link it to data classification",
        "The inventory covers infrastructure but not information assets or the "
        "supplier-provided components in the ICT supply chain.",
        "Head of Engineering", date(2026, 11, 6),
        "IN_PROGRESS", "MEDIUM", "SOA_GAP", None,
    ),
    RemediationSpec(
        "REM-010",
        "Document segregation of duties and compensating controls",
        "At forty people, full segregation is not achievable in every process. Document "
        "where duties conflict and what compensating controls apply, rather than "
        "claiming a separation that does not exist.",
        "Chief Operating Officer", date(2026, 10, 23),
        "OPEN", "MEDIUM", "SOA_GAP", None,
    ),
    RemediationSpec(
        "REM-011",
        "Add security requirements to project intake and acceptance testing",
        "Security is considered informally during design. Add explicit security "
        "requirements to the project intake checklist and an acceptance gate before "
        "production release.",
        "Head of Engineering", date(2026, 12, 4),
        "OPEN", "LOW", "SOA_GAP", None,
    ),
    RemediationSpec(
        "REM-012",
        "Define a forensic evidence collection procedure",
        "Incident logs are retained but there is no documented procedure for preserving "
        "evidence in a form that would survive legal scrutiny.",
        "Head of Engineering", date(2027, 1, 15),
        "OPEN", "LOW", "SOA_GAP", None,
    ),
    RemediationSpec(
        "REM-013",
        "Complete automated deletion coverage across all data categories and media",
        "Deletion jobs cover the primary database but not object storage exports, "
        "support attachments or removable media handling.",
        "Head of Engineering", date(2026, 11, 20),
        "IN_PROGRESS", "MEDIUM", "SOA_GAP", None,
    ),
    RemediationSpec(
        "REM-014",
        "Implement capacity monitoring against defined thresholds",
        "Capacity is observed reactively through incident response. Define thresholds "
        "per service and alert before they are reached.",
        "Head of Engineering", date(2026, 12, 18),
        "OPEN", "LOW", "SOA_GAP", None,
    ),
    RemediationSpec(
        "REM-015",
        "Enforce software installation and web filtering controls on the fleet",
        "Engineers hold local administrator rights and no web filtering is applied, so "
        "unapproved software installation is unrestricted.",
        "Head of Engineering", date(2026, 11, 27),
        "BLOCKED", "MEDIUM", "SOA_GAP", None,
    ),
    RemediationSpec(
        "REM-016",
        "Establish a laptop maintenance and repair handling procedure",
        "Devices sent for repair have no documented data handling requirement, so an "
        "encrypted drive could leave the company's control undocumented.",
        "Head of People", date(2026, 12, 31),
        "OPEN", "LOW", "SOA_GAP", None,
    ),
    RemediationSpec(
        "REM-017",
        "Extend test data masking to all non-production datasets",
        "Masking covers the main application database. Analytics and support "
        "environments still receive partially unmasked extracts. OVERDUE.",
        "Head of Engineering", date(2026, 8, 1),
        "IN_PROGRESS", "MEDIUM", "SOA_GAP", None,
    ),
    RemediationSpec(
        "REM-020",
        "Close medium-severity patch SLA breaches and add an exception approval path",
        "TEST-011 found three medium-severity findings remediated beyond the 90-day SLA "
        "with no documented exception approval, indicating roughly a 12% breach rate. "
        "Clear the backlog and add a route for approving a deliberate exception, so that a "
        "breach is a decision rather than an oversight.",
        "Head of Engineering", date(2026, 11, 14),
        "OPEN", "MEDIUM", "CONTROL_TEST", None,
    ),
    RemediationSpec(
        "REM-018",
        "Deploy endpoint detection and response across the macOS fleet",
        "EDR agent rolled out to all issued laptops with alerting into the on-call "
        "rotation. Closed and verified through the MDM compliance report.",
        "Head of Engineering", date(2026, 3, 31),
        "COMPLETED", "HIGH", "SOA_GAP", date(2026, 3, 24), date(2025, 12, 1),
    ),
    RemediationSpec(
        "REM-019",
        "Migrate production infrastructure changes to code",
        "All production infrastructure moved under Terraform with review required; "
        "console changes now treated as incidents. Closed.",
        "Head of Engineering", date(2026, 2, 28),
        "COMPLETED", "HIGH", "RISK_TREATMENT", date(2026, 2, 20), date(2025, 11, 15),
    ),
]
