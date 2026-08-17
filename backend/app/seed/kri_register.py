"""KRI definitions and their recorded measurement history.

Seven indicators. Each has a formula precise enough that two people would compute the
same number, a named owner, and thresholds with a direction — "green above 95" and
"green below 14" are both normal and one comparison cannot serve both.

The five monthly measurements seeded here are **recorded history**: what was observed at
each period end. The current period is computed live from the registers on every
request, so the dashboard cannot drift from the data behind it. Where the two disagree
about a trend — KRI-003 falls in August after rising for five months — that is real: a
control test downgraded A.8.11 and the implementation percentage went backwards.
"""

from datetime import date
from typing import NamedTuple

ENG = "Head of Engineering"
LEGAL = "Head of Legal & Compliance"
COO = "Chief Operating Officer"
DPO = "Data Protection Officer"


class KriSpec(NamedTuple):
    ref: str
    name: str
    formula_description: str
    data_source: str
    rationale: str
    unit: str
    direction: str
    green_threshold: float
    amber_threshold: float
    owner_role: str
    frequency: str
    history: tuple[tuple[date, float | None], ...]


KRI_DEFINITIONS: list[KriSpec] = [
    KriSpec(
        "KRI-001",
        "Privileged accounts with MFA enforced",
        "Accounts holding a privileged role in the AWS production account that have a "
        "phishing-resistant factor enrolled AND the Okta sign-on policy applied, divided "
        "by all accounts holding a privileged role, expressed as a percentage. An account "
        "reachable through any path that bypasses the sign-on policy counts as not "
        "covered, however it is configured elsewhere.",
        "Most recent control test covering AC-002's privileged population (currently "
        "TEST-003), which is backed by the Okta enrolment report EV-002.",
        "This is the single control standing between a stolen password and the whole "
        "production estate. RISK-004 sits above appetite entirely because of it.",
        "PERCENT", "HIGHER_IS_BETTER", 100.0, 90.0, ENG, "MONTHLY",
        (
            (date(2026, 3, 31), 40.0),
            (date(2026, 4, 30), 46.7),
            (date(2026, 5, 31), 53.3),
            (date(2026, 6, 30), 53.3),
            (date(2026, 7, 31), 60.0),
        ),
    ),
    KriSpec(
        "KRI-002",
        "Mean time to remediate Critical and High priority findings",
        "Mean days from the date remediation was raised to the date it was closed, over "
        "items of Critical or High priority closed in the trailing twelve months. FinFlow "
        "has recorded no Critical priority items to date, so High is included to keep the "
        "indicator measurable — the substitution is stated rather than left to produce an "
        "empty chart.",
        "Remediation register, filtered to closed items with a recorded raised date.",
        "Detection without timely closure is theatre. This measures whether serious "
        "findings actually get fixed, as distinct from whether they get logged.",
        "DAYS", "LOWER_IS_BETTER", 30.0, 60.0, ENG, "MONTHLY",
        (
            (date(2026, 3, 31), 105.0),
            (date(2026, 4, 30), 105.0),
            (date(2026, 5, 31), 105.0),
            (date(2026, 6, 30), 105.0),
            (date(2026, 7, 31), 105.0),
        ),
    ),
    KriSpec(
        "KRI-003",
        "Applicable Annex A controls implemented",
        "SoA entries marked applicable with an implementation status of IMPLEMENTED, "
        "divided by all applicable SoA entries, as a percentage. Excluded controls are "
        "not in the denominator: counting them as unimplemented understates readiness and "
        "counting them as implemented overstates it.",
        "Statement of Applicability.",
        "The headline certification-readiness figure, and the one an auditor will "
        "recompute themselves.",
        "PERCENT", "HIGHER_IS_BETTER", 95.0, 80.0, LEGAL, "MONTHLY",
        (
            (date(2026, 3, 31), 48.8),
            (date(2026, 4, 30), 54.8),
            (date(2026, 5, 31), 58.3),
            (date(2026, 6, 30), 61.9),
            (date(2026, 7, 31), 66.7),
        ),
    ),
    KriSpec(
        "KRI-004",
        "Controls tested within their required frequency",
        "Internal controls with a recorded test date inside the last 365 days, divided by "
        "all controls in the library, as a percentage. Every control carries an annual "
        "testing requirement, so a control never tested is not current. A control rated "
        "from configuration review is legitimately rated but is not tested.",
        "Internal control library and the control test workpapers.",
        "Distinguishes an ISMS that is assessed from one that is asserted. A high SoA "
        "implementation percentage means little if nothing behind it has been tested.",
        "PERCENT", "HIGHER_IS_BETTER", 80.0, 50.0, LEGAL, "QUARTERLY",
        (
            (date(2026, 3, 31), 8.6),
            (date(2026, 4, 30), 14.3),
            (date(2026, 5, 31), 20.0),
            (date(2026, 6, 30), 25.7),
            (date(2026, 7, 31), 31.4),
        ),
    ),
    KriSpec(
        "KRI-005",
        "Risks with residual band above category appetite",
        "Count of risks whose residual band exceeds the maximum acceptable band recorded "
        "for their category. Comparison is by band, not score, because bands are the unit "
        "the business agreed to.",
        "Risk register and the per-category appetite thresholds.",
        "Each of these is either an unremediated gap or an undocumented acceptance. Both "
        "need a decision from a named person.",
        "COUNT", "LOWER_IS_BETTER", 0.0, 3.0, COO, "MONTHLY",
        (
            (date(2026, 3, 31), 4.0),
            (date(2026, 4, 30), 4.0),
            (date(2026, 5, 31), 5.0),
            (date(2026, 6, 30), 5.0),
            (date(2026, 7, 31), 5.0),
        ),
    ),
    KriSpec(
        "KRI-006",
        "Evidence artifacts within their validity period",
        "Evidence artifacts whose recorded validity end date is on or after the "
        "measurement date, divided by all artifacts in the register, as a percentage. "
        "Validity is a property of the artifact rather than of the control it supports: a "
        "control can be operating perfectly while the document proving it has gone stale.",
        "Evidence register.",
        "An expired artifact is not evidence that a control operates; it is evidence that "
        "it operated once. Eight of the nine Annex A exclusions currently rest on an "
        "expired provider report.",
        "PERCENT", "HIGHER_IS_BETTER", 95.0, 85.0, LEGAL, "MONTHLY",
        (
            (date(2026, 3, 31), 100.0),
            (date(2026, 4, 30), 96.8),
            (date(2026, 5, 31), 93.5),
            (date(2026, 6, 30), 93.5),
            (date(2026, 7, 31), 90.3),
        ),
    ),
    KriSpec(
        "KRI-007",
        "Risk acceptances past their expiry date",
        "Count of entries in the acceptance register whose expiry date has passed and "
        "which have not been withdrawn or rejected.",
        "Risk acceptance register.",
        "An expired acceptance means an exposure is being carried with nobody currently "
        "answering for it — worse than a documented acceptance, because no one has agreed "
        "to it.",
        "COUNT", "LOWER_IS_BETTER", 0.0, 1.0, DPO, "MONTHLY",
        (
            (date(2026, 3, 31), 0.0),
            (date(2026, 4, 30), 0.0),
            (date(2026, 5, 31), 0.0),
            (date(2026, 6, 30), 0.0),
            (date(2026, 7, 31), 1.0),
        ),
    ),
]
