"""Control testing rules: design vs operating effectiveness, sampling, conclusions.

Why effectiveness is two fields, not one
----------------------------------------
An auditor asks two separate questions about every control, in order:

  1. **Design** — if this control operated exactly as written, would it achieve the
     objective? A control can fail here while operating flawlessly. DP-005 masks the
     primary application database and nothing else; it runs perfectly every night and
     still leaves analytics environments holding real customer data. That is a *design*
     deficiency, and no amount of reliable operation fixes it.

  2. **Operating** — did it actually run, over a period, as designed? A control can be
     perfectly designed and simply not happen.

Collapsing the two into one "effectiveness" rating loses the distinction that decides
what to do next. A design deficiency needs the control redesigned; an operating
deficiency needs it enforced. They are different pieces of work with different owners.

The rule
--------
Operating effectiveness may not be EFFECTIVE while design effectiveness is DEFICIENT.
If the design does not achieve the objective, then operating exactly as designed still
does not achieve the objective — the best available operating rating is
EFFECTIVE_WITH_EXCEPTIONS. This is enforced server-side, not merely surfaced.

Sampling
--------
An auditor's first question about any test is "how did you choose the sample?" A
population size without a sample size is not a test, and a judgmental sample without a
rationale is an opinion. Both are enforced.
"""

import enum
from dataclasses import dataclass
from datetime import date  # noqa: F401  -- referenced in a string annotation

from app.services.risk_scoring import ControlEffectivenessBasis


class DesignEffectiveness(str, enum.Enum):
    NOT_ASSESSED = "NOT_ASSESSED"
    EFFECTIVE = "EFFECTIVE"
    DEFICIENT = "DEFICIENT"


class OperatingEffectiveness(str, enum.Enum):
    NOT_TESTED = "NOT_TESTED"
    EFFECTIVE = "EFFECTIVE"
    EFFECTIVE_WITH_EXCEPTIONS = "EFFECTIVE_WITH_EXCEPTIONS"
    INEFFECTIVE = "INEFFECTIVE"


class SampleSelectionMethod(str, enum.Enum):
    RANDOM = "RANDOM"
    HAPHAZARD = "HAPHAZARD"
    JUDGMENTAL = "JUDGMENTAL"
    FULL_POPULATION = "FULL_POPULATION"


class TestConclusion(str, enum.Enum):
    PASS = "PASS"
    PASS_WITH_EXCEPTIONS = "PASS_WITH_EXCEPTIONS"
    FAIL = "FAIL"


class FindingSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FindingStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    REMEDIATED = "REMEDIATED"
    CLOSED = "CLOSED"


class FindingSource(str, enum.Enum):
    CONTROL_TEST = "CONTROL_TEST"
    INTERNAL_AUDIT = "INTERNAL_AUDIT"
    MANAGEMENT_REVIEW = "MANAGEMENT_REVIEW"
    INCIDENT = "INCIDENT"


class AuditStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DEFERRED = "DEFERRED"


class NonconformityStatus(str, enum.Enum):
    OPEN = "OPEN"
    CORRECTION_APPLIED = "CORRECTION_APPLIED"
    CORRECTIVE_ACTION_IN_PROGRESS = "CORRECTIVE_ACTION_IN_PROGRESS"
    AWAITING_EFFECTIVENESS_CHECK = "AWAITING_EFFECTIVENESS_CHECK"
    CLOSED = "CLOSED"


# A test conclusion determines what the control's operating effectiveness may say.
# Recording a PASS and then rating the control INEFFECTIVE (or vice versa) means one of
# the two is wrong, and the workpaper is the record that survives.
CONCLUSION_TO_OPERATING: dict[TestConclusion, OperatingEffectiveness] = {
    TestConclusion.PASS: OperatingEffectiveness.EFFECTIVE,
    TestConclusion.PASS_WITH_EXCEPTIONS: OperatingEffectiveness.EFFECTIVE_WITH_EXCEPTIONS,
    TestConclusion.FAIL: OperatingEffectiveness.INEFFECTIVE,
}

# Which risk-link bases the control library actually supports. Claiming a *tested*
# basis for a control nobody has tested is the failure this catches.
_TESTED_BASES = {
    ControlEffectivenessBasis.TESTED_EFFECTIVE,
    ControlEffectivenessBasis.TESTED_WITH_EXCEPTIONS,
    ControlEffectivenessBasis.TESTED_INEFFECTIVE,
}

# The strongest basis each operating rating supports. A risk link may record something
# weaker (that is conservative and always allowed); recording something stronger is an
# optimism flag, surfaced rather than blocked, because the analyst may be scoping to a
# population the exceptions did not touch.
_ROLLUP_BASIS: dict[OperatingEffectiveness, ControlEffectivenessBasis] = {
    OperatingEffectiveness.EFFECTIVE: ControlEffectivenessBasis.TESTED_EFFECTIVE,
    OperatingEffectiveness.EFFECTIVE_WITH_EXCEPTIONS: (
        ControlEffectivenessBasis.TESTED_WITH_EXCEPTIONS
    ),
    OperatingEffectiveness.INEFFECTIVE: ControlEffectivenessBasis.TESTED_INEFFECTIVE,
    OperatingEffectiveness.NOT_TESTED: ControlEffectivenessBasis.NOT_TESTED,
}

_BASIS_STRENGTH = {
    ControlEffectivenessBasis.NOT_TESTED: 0,
    ControlEffectivenessBasis.TESTED_INEFFECTIVE: 0,
    ControlEffectivenessBasis.DESIGN_ONLY: 1,
    ControlEffectivenessBasis.TESTED_WITH_EXCEPTIONS: 2,
    ControlEffectivenessBasis.TESTED_EFFECTIVE: 3,
}


@dataclass(frozen=True)
class RuleViolation:
    field: str
    message: str


def validate_effectiveness(
    design: DesignEffectiveness, operating: OperatingEffectiveness
) -> list[RuleViolation]:
    """A deficient design caps operating effectiveness below EFFECTIVE."""
    if design == DesignEffectiveness.DEFICIENT and operating == OperatingEffectiveness.EFFECTIVE:
        return [
            RuleViolation(
                "operating_effectiveness",
                "Operating effectiveness cannot be EFFECTIVE while the design is DEFICIENT. "
                "If the control as designed does not achieve its objective, then operating "
                "exactly as designed does not achieve it either — the ceiling is "
                "EFFECTIVE_WITH_EXCEPTIONS. Fix the design, or lower the rating.",
            )
        ]
    return []


def validate_test(
    *,
    population_size: int,
    sample_size: int,
    sample_selection_method: SampleSelectionMethod,
    sampling_rationale: str | None,
    exceptions_count: int,
    conclusion: TestConclusion,
    exception_details: str | None,
    tester: str,
    reviewed_by: str | None,
    period_covered_start: "date | None" = None,
    period_covered_end: "date | None" = None,
) -> list[RuleViolation]:
    """Rules a workpaper must satisfy to be worth the paper it is written on."""
    errors: list[RuleViolation] = []

    if (
        period_covered_start is not None
        and period_covered_end is not None
        and period_covered_end < period_covered_start
    ):
        errors.append(
            RuleViolation(
                "period_covered_end",
                "The period covered ends before it starts. Operating effectiveness is a "
                "claim about a span of time, so the span has to be real.",
            )
        )

    if population_size < 1:
        errors.append(
            RuleViolation("population_size", "Population size must be at least 1.")
        )
    if sample_size < 1:
        errors.append(RuleViolation("sample_size", "Sample size must be at least 1."))
    if sample_size > population_size:
        errors.append(
            RuleViolation(
                "sample_size",
                f"Sample size {sample_size} exceeds the population of {population_size}. "
                "A sample cannot be larger than what it is drawn from.",
            )
        )
    if (
        sample_selection_method == SampleSelectionMethod.FULL_POPULATION
        and sample_size != population_size
    ):
        errors.append(
            RuleViolation(
                "sample_size",
                "FULL_POPULATION means every item was examined, so sample size must equal "
                f"population size ({population_size}).",
            )
        )
    if not (sampling_rationale or "").strip():
        errors.append(
            RuleViolation(
                "sampling_rationale",
                "Every test needs a sampling rationale. 'How did you choose the sample?' is "
                "the first question an auditor asks, and a sample without an answer is an "
                "opinion rather than evidence.",
            )
        )

    if exceptions_count < 0:
        errors.append(
            RuleViolation("exceptions_count", "Exception count cannot be negative.")
        )
    if exceptions_count > sample_size:
        errors.append(
            RuleViolation(
                "exceptions_count",
                f"{exceptions_count} exceptions found in a sample of {sample_size}.",
            )
        )
    if exceptions_count > 0 and conclusion == TestConclusion.PASS:
        errors.append(
            RuleViolation(
                "conclusion",
                f"{exceptions_count} exception(s) were found, so the conclusion cannot be a "
                "clean PASS. Use PASS_WITH_EXCEPTIONS, or FAIL if the control did not "
                "achieve its objective.",
            )
        )
    if exceptions_count == 0 and conclusion == TestConclusion.PASS_WITH_EXCEPTIONS:
        errors.append(
            RuleViolation(
                "conclusion",
                "PASS_WITH_EXCEPTIONS records zero exceptions. Either the exceptions were "
                "not counted or the conclusion should be PASS.",
            )
        )
    if exceptions_count > 0 and not (exception_details or "").strip():
        errors.append(
            RuleViolation(
                "exception_details",
                "Exceptions were found but not described. A count with no detail cannot be "
                "remediated or re-tested.",
            )
        )

    # Preparer/reviewer segregation. A workpaper reviewed by its own author has not been
    # reviewed, and this is one of the few segregation controls a 40-person company can
    # still operate.
    if reviewed_by and reviewed_by.strip().lower() == tester.strip().lower():
        errors.append(
            RuleViolation(
                "reviewed_by",
                "The reviewer cannot be the tester. A workpaper reviewed by its own author "
                "has not been independently reviewed.",
            )
        )

    return errors


# Priority for an auto-created remediation item, keyed by the finding's severity.
RemediationPriorityForSeverity: dict[FindingSeverity, str] = {
    FindingSeverity.LOW: "LOW",
    FindingSeverity.MEDIUM: "MEDIUM",
    FindingSeverity.HIGH: "HIGH",
    FindingSeverity.CRITICAL: "CRITICAL",
}


def requires_finding(conclusion: TestConclusion) -> bool:
    """FAIL and PASS_WITH_EXCEPTIONS must produce a finding and remediation."""
    return conclusion in (TestConclusion.FAIL, TestConclusion.PASS_WITH_EXCEPTIONS)


def severity_for(conclusion: TestConclusion, exceptions_count: int, sample_size: int) -> FindingSeverity:
    """Default severity for an auto-created finding.

    A starting point for a human to adjust, not a verdict — the finding is created as
    DRAFT precisely so someone confirms it.
    """
    if conclusion == TestConclusion.FAIL:
        return FindingSeverity.HIGH
    rate = exceptions_count / sample_size if sample_size else 0
    return FindingSeverity.MEDIUM if rate >= 0.2 else FindingSeverity.LOW


def basis_supported_by_control(
    basis: ControlEffectivenessBasis, operating: OperatingEffectiveness
) -> bool:
    """False when a risk link claims a tested basis for a never-tested control."""
    if operating == OperatingEffectiveness.NOT_TESTED and basis in _TESTED_BASES:
        return False
    return True


def strongest_supported_basis(
    design: DesignEffectiveness, operating: OperatingEffectiveness
) -> ControlEffectivenessBasis:
    """The most a risk link may claim, given what is known about the control.

    An untested control still supports DESIGN_ONLY when its design has been assessed and
    found effective — that is precisely what DESIGN_ONLY means. It supports nothing when
    the design was never assessed, or was assessed and found deficient.
    """
    if operating != OperatingEffectiveness.NOT_TESTED:
        return _ROLLUP_BASIS[operating]
    if design == DesignEffectiveness.EFFECTIVE:
        return ControlEffectivenessBasis.DESIGN_ONLY
    return ControlEffectivenessBasis.NOT_TESTED


def basis_is_optimistic(
    basis: ControlEffectivenessBasis,
    operating: OperatingEffectiveness,
    design: DesignEffectiveness = DesignEffectiveness.NOT_ASSESSED,
) -> bool:
    """True when a risk link records more assurance than the control library supports.

    Surfaced, not blocked. The analyst may legitimately be scoping to a population the
    exceptions did not touch — AC-002 passed for the workforce and failed for privileged
    accounts — but the discrepancy should be visible rather than silent.
    """
    supported = strongest_supported_basis(design, operating)
    return _BASIS_STRENGTH[basis] > _BASIS_STRENGTH[supported]
