"""Rules for risk acceptance, GDPR records and business impact analysis.

Three registers, one theme: each records a judgment somebody made, with the thing that
makes the judgment reviewable attached to it. An acceptance without an expiry is a
permanent decision disguised as a temporary one. A transfer without a safeguard is an
unlawful transfer with paperwork. An RTO longer than the period the business can
tolerate is a recovery plan that has already failed.
"""

import enum
from dataclasses import dataclass
from datetime import date, timedelta

EXPIRY_WARNING_DAYS = 30


# --- Assets -------------------------------------------------------------------


class AssetType(str, enum.Enum):
    SYSTEM = "SYSTEM"
    DATA_STORE = "DATA_STORE"
    SAAS_SERVICE = "SAAS_SERVICE"
    THIRD_PARTY_SERVICE = "THIRD_PARTY_SERVICE"
    DEVICE_FLEET = "DEVICE_FLEET"
    PROCESS = "PROCESS"


class Classification(str, enum.Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


# --- Risk acceptance -----------------------------------------------------------


class ExceptionStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    EXPIRED = "EXPIRED"
    WITHDRAWN = "WITHDRAWN"
    REJECTED = "REJECTED"


# Roles that may approve an acceptance on behalf of a risk owner. Kept deliberately
# short: escalation above the owner is a real thing, but it should be rare and named.
ESCALATION_APPROVERS = frozenset({"Chief Executive Officer"})

# Substrings that identify the security function. Risk acceptance is a business
# decision — security advises on the risk, the business decides to carry it. An
# acceptance signed by the person who raised the risk is not an acceptance.
_SECURITY_ROLE_MARKERS = ("security", "ciso", "infosec", "compliance analyst")


# --- GDPR ----------------------------------------------------------------------


class LawfulBasis(str, enum.Enum):
    """Article 6(1)."""

    CONSENT = "CONSENT"
    CONTRACT = "CONTRACT"
    LEGAL_OBLIGATION = "LEGAL_OBLIGATION"
    VITAL_INTERESTS = "VITAL_INTERESTS"
    PUBLIC_TASK = "PUBLIC_TASK"
    LEGITIMATE_INTERESTS = "LEGITIMATE_INTERESTS"


class TransferSafeguard(str, enum.Enum):
    """Chapter V mechanisms."""

    NOT_APPLICABLE = "NOT_APPLICABLE"
    ADEQUACY_DECISION = "ADEQUACY_DECISION"
    STANDARD_CONTRACTUAL_CLAUSES = "STANDARD_CONTRACTUAL_CLAUSES"
    BINDING_CORPORATE_RULES = "BINDING_CORPORATE_RULES"
    DEROGATION = "DEROGATION"


class DpiaOutcome(str, enum.Enum):
    PROCEED = "PROCEED"
    PROCEED_WITH_MEASURES = "PROCEED_WITH_MEASURES"
    CONSULT_SUPERVISORY_AUTHORITY = "CONSULT_SUPERVISORY_AUTHORITY"
    DO_NOT_PROCEED = "DO_NOT_PROCEED"


class ResidualRiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class RuleViolation:
    field: str
    message: str


def _is_security_role(role: str) -> bool:
    lowered = role.lower()
    return any(marker in lowered for marker in _SECURITY_ROLE_MARKERS)


def validate_exception(
    *,
    approver_role: str,
    risk_owner_role: str,
    expiry_date: date | None,
    approval_date: date | None,
    business_justification: str,
    review_trigger: str,
    status: ExceptionStatus,
) -> list[RuleViolation]:
    """Rules that stop an acceptance becoming a permanent, unowned decision."""
    errors: list[RuleViolation] = []

    if expiry_date is None:
        errors.append(
            RuleViolation(
                "expiry_date",
                "A risk acceptance must expire. An acceptance with no end date is a "
                "permanent decision that nobody will ever revisit, and the conditions that "
                "made it reasonable will change without anyone noticing.",
            )
        )
    elif approval_date is not None and expiry_date <= approval_date:
        errors.append(
            RuleViolation(
                "expiry_date", "The expiry date must fall after the approval date."
            )
        )

    if _is_security_role(approver_role):
        errors.append(
            RuleViolation(
                "approver_role",
                f"'{approver_role}' is part of the security function and cannot approve a "
                "risk acceptance. Security advises on risk; the business decides to carry "
                "it. An acceptance signed by the people who raised the risk is not an "
                "acceptance.",
            )
        )
    elif (
        approver_role.strip() != risk_owner_role.strip()
        and approver_role.strip() not in ESCALATION_APPROVERS
    ):
        errors.append(
            RuleViolation(
                "approver_role",
                f"'{approver_role}' is neither the risk owner ('{risk_owner_role}') nor an "
                "escalation approver. Whoever accepts the risk must be the person who "
                "answers for the consequence.",
            )
        )

    if not business_justification.strip():
        errors.append(
            RuleViolation(
                "business_justification",
                "An acceptance needs a business reason. 'Too expensive to fix' is a reason; "
                "silence is not.",
            )
        )

    if not review_trigger.strip():
        errors.append(
            RuleViolation(
                "review_trigger",
                "Record what would force this acceptance to be revisited before its expiry "
                "— a funding change, a customer commitment, an incident. Time is the "
                "backstop, not the only trigger.",
            )
        )

    if status == ExceptionStatus.APPROVED and approval_date is None:
        errors.append(
            RuleViolation("approval_date", "An approved exception needs an approval date.")
        )

    return errors


def exception_state(expiry_date: date, status: ExceptionStatus, as_of: date) -> str:
    """Derived lifecycle state, so 'APPROVED' cannot quietly mean 'expired last year'."""
    if status in (ExceptionStatus.WITHDRAWN, ExceptionStatus.REJECTED):
        return status.value
    if expiry_date < as_of:
        return "EXPIRED"
    if expiry_date <= as_of + timedelta(days=EXPIRY_WARNING_DAYS):
        return "EXPIRING_SOON"
    return status.value


def validate_ropa(
    *,
    transfers_outside_eea: bool,
    transfer_safeguard: TransferSafeguard,
    transfer_detail: str | None,
    retention_period: str,
    lawful_basis: LawfulBasis,
    legitimate_interests_assessment: str | None,
) -> list[RuleViolation]:
    """Article 30(1) completeness, plus the Chapter V and Article 6(1)(f) dependencies."""
    errors: list[RuleViolation] = []

    if transfers_outside_eea:
        if transfer_safeguard == TransferSafeguard.NOT_APPLICABLE:
            errors.append(
                RuleViolation(
                    "transfer_safeguard",
                    "This activity transfers personal data outside the EEA, so Chapter V "
                    "requires a safeguard. A transfer with no recorded mechanism is an "
                    "unlawful transfer with paperwork attached.",
                )
            )
        if not (transfer_detail or "").strip():
            errors.append(
                RuleViolation(
                    "transfer_detail",
                    "Record which third countries receive the data and under what "
                    "instrument. Article 30(1)(e) asks for the countries by name.",
                )
            )
    elif transfer_safeguard != TransferSafeguard.NOT_APPLICABLE:
        errors.append(
            RuleViolation(
                "transfer_safeguard",
                "A safeguard is recorded but no transfer takes place. Either the transfer "
                "flag is wrong or the safeguard is.",
            )
        )

    if not retention_period.strip():
        errors.append(
            RuleViolation(
                "retention_period",
                "Article 30(1)(f) requires the envisaged time limits for erasure. 'As long "
                "as necessary' is not a time limit.",
            )
        )

    if lawful_basis == LawfulBasis.LEGITIMATE_INTERESTS and not (
        legitimate_interests_assessment or ""
    ).strip():
        errors.append(
            RuleViolation(
                "legitimate_interests_assessment",
                "Article 6(1)(f) requires the interests to be balanced against the data "
                "subject's rights. Relying on legitimate interests without recording that "
                "balancing test leaves the basis unevidenced.",
            )
        )

    return errors


def validate_dpia(
    *,
    outcome: DpiaOutcome,
    residual_risk: ResidualRiskLevel,
    dpo_consulted: bool,
    supervisory_authority_consulted: bool,
    mitigating_measures: str,
    review_date: date | None,
) -> list[RuleViolation]:
    """Article 35 and 36 dependencies."""
    errors: list[RuleViolation] = []

    if not dpo_consulted:
        errors.append(
            RuleViolation(
                "dpo_consulted",
                "Article 35(2) requires the controller to seek the advice of the data "
                "protection officer where one is designated. FinFlow has designated one.",
            )
        )

    # Article 36(1): if the DPIA indicates high residual risk, the supervisory authority
    # must be consulted before processing begins.
    if (
        residual_risk == ResidualRiskLevel.HIGH
        and outcome in (DpiaOutcome.PROCEED, DpiaOutcome.PROCEED_WITH_MEASURES)
        and not supervisory_authority_consulted
    ):
        errors.append(
            RuleViolation(
                "supervisory_authority_consulted",
                "Residual risk remains HIGH after mitigation, so Article 36(1) requires "
                "prior consultation with the supervisory authority before processing. "
                "Proceeding without it is not a decision the controller can take alone.",
            )
        )

    if outcome == DpiaOutcome.PROCEED_WITH_MEASURES and not mitigating_measures.strip():
        errors.append(
            RuleViolation(
                "mitigating_measures",
                "The outcome is 'proceed with measures' but no measures are recorded.",
            )
        )

    if outcome != DpiaOutcome.DO_NOT_PROCEED and review_date is None:
        errors.append(
            RuleViolation(
                "review_date",
                "Article 35(11) requires review where there is a change in the risk. Set a "
                "review date so the assessment cannot silently go stale.",
            )
        )

    return errors


def validate_bia(
    *, rto_hours: float, rpo_hours: float, mtpd_hours: float
) -> list[RuleViolation]:
    """The one arithmetic relationship a BIA must satisfy.

    MTPD is the longest the business can survive without the process. RTO is how long
    recovery is planned to take. If RTO exceeds MTPD, the plan has already failed at the
    moment it is written — recovery completes after the point the business could bear.
    RPO is bounded by the same limit: losing more data than the tolerable window means
    the process cannot resume within it.
    """
    errors: list[RuleViolation] = []

    for label, value in (("rto_hours", rto_hours), ("rpo_hours", rpo_hours), ("mtpd_hours", mtpd_hours)):
        if value < 0:
            errors.append(RuleViolation(label, f"{label} cannot be negative."))

    if rto_hours > mtpd_hours:
        errors.append(
            RuleViolation(
                "rto_hours",
                f"The recovery time objective ({rto_hours}h) exceeds the maximum tolerable "
                f"period of disruption ({mtpd_hours}h). Recovery would complete after the "
                "business could bear the outage, which means the plan fails on the day it "
                "is written. Shorten the RTO or justify a longer MTPD.",
            )
        )
    if rpo_hours > mtpd_hours:
        errors.append(
            RuleViolation(
                "rpo_hours",
                f"The recovery point objective ({rpo_hours}h) exceeds the maximum tolerable "
                f"period of disruption ({mtpd_hours}h).",
            )
        )

    return errors
