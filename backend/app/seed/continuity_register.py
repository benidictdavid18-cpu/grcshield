"""Business impact analysis.

Five processes. The numbers are the point: MTPD is what the business can survive, RTO
and RPO are what recovery is planned to achieve, and the relationship between them is
checked. BIA-001 is the interesting one — its two-hour RTO is achievable for the failure
modes FinFlow has engineered for, and is not achievable for the regional loss the
business formally accepted in EXC-002. A BIA earns its keep by making that visible.
"""

from datetime import date
from typing import NamedTuple


class BiaSpec(NamedTuple):
    ref: str
    process_name: str
    process_description: str
    owner_role: str
    rto_hours: float
    rpo_hours: float
    mtpd_hours: float
    impact_1h: float
    impact_24h: float
    impact_1w: float
    impact_note: str
    workaround: str
    recovery_note: str | None
    last_reviewed: date
    assets: tuple[str, ...]
    controls: tuple[str, ...]
    risks: tuple[str, ...]


BIA_PROCESSES: list[BiaSpec] = [
    BiaSpec(
        "BIA-001", "Payment transaction processing",
        "Accepting, authorising and routing merchant transactions. The revenue-generating "
        "process — every minute of downtime is transactions not processed and merchants "
        "unable to trade.",
        "Chief Operating Officer",
        2.0, 0.25, 4.0,
        4200.00, 96000.00, 610000.00,
        "Hourly figure is lost processing fees at current volume. The 24-hour and one-week "
        "figures include estimated merchant churn, which becomes the dominant cost after "
        "roughly six hours: merchants who cannot take payment for a working day begin "
        "moving to alternative providers and largely do not return.",
        "None that FinFlow controls. Merchants can process through an alternative provider "
        "if they already hold one, which most small merchants do not. There is no manual "
        "fallback for card authorisation.",
        "The two-hour RTO is achievable for the failure modes engineered for — single-zone "
        "loss is covered by OP-006 multi-AZ failover, and database corruption by OP-005 "
        "(TEST-012 completed a restore in 47 minutes). It is NOT achievable for the loss "
        "of the whole eu-west-1 region, which is the scenario formally accepted under "
        "EXC-002. That gap is a consequence of an explicit business decision rather than "
        "an oversight, and is recorded here so the decision is visible against the "
        "recovery target it undercuts.",
        date(2026, 7, 15),
        ("AST-001", "AST-002", "AST-006", "AST-010"),
        ("OP-005", "OP-006", "BC-001", "IR-001"),
        ("RISK-007", "RISK-003", "RISK-017"),
    ),
    BiaSpec(
        "BIA-002", "Merchant settlement and payouts",
        "Calculating and instructing payouts of collected funds to merchant bank accounts "
        "on the agreed settlement cycle.",
        "Chief Financial Officer",
        4.0, 0.25, 24.0,
        0.00, 18000.00, 240000.00,
        "No material cost in the first hour — settlement runs on a daily cycle, so a short "
        "outage is absorbed without a merchant noticing. Beyond a missed settlement window "
        "the cost is merchant cash-flow disruption, support load and reputational damage, "
        "which compounds sharply because merchants depend on payouts to pay their own "
        "suppliers.",
        "Settlement instructions can be prepared manually from the ledger and submitted "
        "through the payment service provider's portal. Viable for a single cycle at "
        "current merchant count; not viable for more than two consecutive days.",
        "RPO of 15 minutes is set by the ledger rather than by settlement itself — losing "
        "ledger writes would mean paying out an amount that does not reconcile.",
        date(2026, 7, 15),
        ("AST-001", "AST-010", "AST-006"),
        ("OP-005", "OP-006", "DP-004"),
        ("RISK-003", "RISK-017"),
    ),
    BiaSpec(
        "BIA-003", "Merchant onboarding and identity verification",
        "Verifying and approving new merchant applications, including sanctions and "
        "beneficial ownership screening.",
        "Head of Legal & Compliance",
        24.0, 4.0, 72.0,
        0.00, 2400.00, 34000.00,
        "The cost is deferred revenue and applicant drop-off rather than immediate loss. "
        "Applications queue rather than disappear, but conversion falls measurably once "
        "approval takes more than two working days.",
        "Applications can be received and queued while verification is unavailable. "
        "Screening cannot be performed manually — it depends on the verification provider "
        "— so approval genuinely stops rather than slowing.",
        None,
        date(2026, 7, 15),
        ("AST-003", "AST-001"),
        ("TP-001", "OP-005"),
        ("RISK-003",),
    ),
    BiaSpec(
        "BIA-004", "Customer support",
        "Responding to merchant queries about transactions, settlements and account "
        "configuration.",
        "Chief Operating Officer",
        8.0, 24.0, 48.0,
        0.00, 900.00, 12000.00,
        "Direct cost is low; the real exposure is that support is how merchants discover "
        "and report problems with the other processes. An extended support outage during a "
        "payment incident would compound that incident considerably.",
        "Support can operate from email and a shared inbox without the ticketing platform, "
        "losing history and routing but retaining the ability to respond. This has been "
        "done once, during a vendor outage in 2025.",
        "The 24-hour RPO reflects that losing a day of ticket history is tolerable — the "
        "correspondence exists in email as well.",
        date(2026, 7, 15),
        ("AST-008", "AST-004"),
        ("BC-001", "IR-001"),
        ("RISK-020",),
    ),
    BiaSpec(
        "BIA-005", "Financial reporting and reconciliation",
        "Reconciling processed transactions against provider settlement reports and "
        "producing statutory and management financial reporting.",
        "Chief Financial Officer",
        48.0, 24.0, 120.0,
        0.00, 0.00, 8000.00,
        "No short-term operational cost. The exposure is regulatory and contractual "
        "deadlines — a missed statutory filing carries penalties, and investor reporting "
        "commitments have fixed dates. Both are measured in weeks rather than hours.",
        "Reconciliation can be performed manually from provider settlement reports and "
        "bank statements. Slow and error-prone, but it works and has been used during "
        "month-end incidents.",
        None,
        date(2026, 7, 15),
        ("AST-001", "AST-010", "AST-012"),
        ("OP-005", "DP-004", "OP-001"),
        ("RISK-017",),
    ),
]
