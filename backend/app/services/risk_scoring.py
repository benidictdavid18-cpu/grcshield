"""Risk scoring rules.

Methodology basis
-----------------
ISO/IEC 27005          risk identification, analysis and evaluation for an ISMS
NIST SP 800-30 Rev. 1  likelihood x impact analysis and the risk determination step
ISO 31000              governance framing: appetite, ownership, treatment decisions
ISO/IEC 27001:2022     Clause 6.1.2 (risk assessment) and 6.1.3 (risk treatment)

Why residual is scored independently
------------------------------------
A common shortcut computes:

    residual = inherent x (1 - control_effectiveness)

That is arithmetic wearing the costume of a methodology, and it is wrong for three
reasons.

1.  It collapses two dimensions into one. Controls do not reduce "risk"; they reduce
    *likelihood* or *impact*, and usually only one of them. MFA makes credential
    compromise less likely and does nothing to the blast radius once an attacker is
    in. A backup does nothing to likelihood and everything to impact. Multiplying a
    single score by a single percentage cannot express that, so it silently misstates
    which dimension was treated.

2.  A single "effectiveness percentage" is not a measurable quantity. Nobody can
    defend the difference between a control that is 70% effective and one that is
    75% effective, yet that invented number drives the output the board sees.

3.  It makes residual risk non-falsifiable. If residual is derived, an analyst can
    never disagree with it, and an auditor can never challenge it. Scoring residual
    directly forces a human to commit to a position and write down why.

So: the analyst sets residual_likelihood and residual_impact directly, and must supply
a written justification naming which control reduced which dimension. The system
computes bands and compares against appetite; it does not compute the judgment.

Untested controls earn no credit
--------------------------------
A control that has never been tested provides no assurance, only intent. Crediting it
with a residual reduction converts an assumption into a number and then reports that
number as fact. The rule is enforced server-side, not merely surfaced as a warning.
"""

import enum


class RiskBand(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ControlEffectivenessBasis(str, enum.Enum):
    """How much is actually known about a control linked to a risk.

    This is evidence provenance, not a quality score. It answers "on what basis do you
    claim this control works?" -- which is the question an auditor asks first.
    """

    NOT_TESTED = "NOT_TESTED"
    DESIGN_ONLY = "DESIGN_ONLY"
    TESTED_EFFECTIVE = "TESTED_EFFECTIVE"
    TESTED_WITH_EXCEPTIONS = "TESTED_WITH_EXCEPTIONS"
    TESTED_INEFFECTIVE = "TESTED_INEFFECTIVE"


class TreatmentDecision(str, enum.Enum):
    MITIGATE = "MITIGATE"
    ACCEPT = "ACCEPT"
    TRANSFER = "TRANSFER"
    AVOID = "AVOID"


class RiskStatus(str, enum.Enum):
    OPEN = "OPEN"
    TREATMENT_IN_PROGRESS = "TREATMENT_IN_PROGRESS"
    MONITORING = "MONITORING"
    CLOSED = "CLOSED"


class RiskCategory(str, enum.Enum):
    CYBERSECURITY = "CYBERSECURITY"
    DATA_PRIVACY = "DATA_PRIVACY"
    THIRD_PARTY = "THIRD_PARTY"
    OPERATIONAL = "OPERATIONAL"
    FINANCIAL = "FINANCIAL"
    LEGAL = "LEGAL"
    COMPLIANCE = "COMPLIANCE"
    BUSINESS_CONTINUITY = "BUSINESS_CONTINUITY"
    TECHNOLOGY = "TECHNOLOGY"


CATEGORY_LABELS: dict[RiskCategory, str] = {
    RiskCategory.CYBERSECURITY: "Cybersecurity",
    RiskCategory.DATA_PRIVACY: "Data Privacy",
    RiskCategory.THIRD_PARTY: "Third-Party",
    RiskCategory.OPERATIONAL: "Operational",
    RiskCategory.FINANCIAL: "Financial",
    RiskCategory.LEGAL: "Legal",
    RiskCategory.COMPLIANCE: "Compliance",
    RiskCategory.BUSINESS_CONTINUITY: "Business Continuity",
    RiskCategory.TECHNOLOGY: "Technology",
}

SCALE_MIN = 1
SCALE_MAX = 5

# Inclusive score bands over a 5x5 matrix. Every achievable product of two values in
# 1..5 falls in exactly one band.
_BANDS: list[tuple[int, int, RiskBand]] = [
    (1, 4, RiskBand.LOW),
    (5, 9, RiskBand.MEDIUM),
    (10, 16, RiskBand.HIGH),
    (17, 25, RiskBand.CRITICAL),
]

_BAND_SEVERITY: dict[RiskBand, int] = {
    RiskBand.LOW: 0,
    RiskBand.MEDIUM: 1,
    RiskBand.HIGH: 2,
    RiskBand.CRITICAL: 3,
}

# Bases that may not be credited with any residual reduction.
#
# NOT_TESTED is required by the methodology: an untested control is an assumption.
#
# TESTED_INEFFECTIVE is included on the same reasoning taken one step further -- a
# control that was tested and failed provides less assurance than one that was never
# tested, because the failure is now a known fact rather than an open question.
# Crediting it would be indefensible in an audit.
NON_CREDITING_BASES: frozenset[ControlEffectivenessBasis] = frozenset(
    {
        ControlEffectivenessBasis.NOT_TESTED,
        ControlEffectivenessBasis.TESTED_INEFFECTIVE,
    }
)


class ScoreOutOfRange(ValueError):
    pass


def validate_scale(value: int, field: str) -> int:
    if not SCALE_MIN <= value <= SCALE_MAX:
        raise ScoreOutOfRange(f"{field} must be between {SCALE_MIN} and {SCALE_MAX}, got {value}")
    return value


def score(likelihood: int, impact: int) -> int:
    """Likelihood x impact on a 5x5 matrix, yielding 1..25."""
    validate_scale(likelihood, "likelihood")
    validate_scale(impact, "impact")
    return likelihood * impact


def band_for(risk_score: int) -> RiskBand:
    for low, high, band in _BANDS:
        if low <= risk_score <= high:
            return band
    raise ScoreOutOfRange(f"Risk score {risk_score} is outside the 1-25 matrix")


def band_severity(band: RiskBand) -> int:
    return _BAND_SEVERITY[band]


def exceeds_appetite(residual_band: RiskBand, max_acceptable_band: RiskBand) -> bool:
    """True when a residual band sits above what the category tolerates."""
    return band_severity(residual_band) > band_severity(max_acceptable_band)


def basis_credits_reduction(basis: ControlEffectivenessBasis) -> bool:
    return basis not in NON_CREDITING_BASES


def band_boundaries() -> list[dict]:
    """Band definitions, for the UI legend and the methodology report."""
    return [
        {"band": band.value, "min_score": low, "max_score": high}
        for low, high, band in _BANDS
    ]
