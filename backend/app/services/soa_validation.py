"""Statement of Applicability validation rules.

These encode ISO/IEC 27001:2022 Clause 6.1.3 d): the SoA must state, for every Annex A
control, whether it is applicable and *why*. The rules exist because the three ways an
SoA goes wrong are all silent:

  - a control marked applicable with no reason recorded;
  - a control excluded with no reason recorded, or excluded while still claiming to be
    partly implemented;
  - a control marked applicable and not implemented, with nobody assigned to fix it.

Each is caught here and returned as a 422 rather than discovered by an auditor.
"""

import re
from dataclasses import dataclass

from app.models.soa import ImplementationStatus, RemediationStatus

# A justification that points back at the standard is circular. "We do it because the
# standard says to" explains nothing about FinFlow and is the single most common filler
# in a weak SoA. Clause 6.1.3 d) asks for the reason the control is *necessary*, which
# means a risk, a law, or a contract.
_CIRCULAR_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"^\W*required by iso",
        r"^\W*iso ?/?\s*(iec)? ?27001 requires",
        r"^\W*annex a requires",
        r"^\W*mandated by (the )?standard",
        r"^\W*(it is )?(a )?(standard|iso) requirement\W*$",
        r"^\W*best practice\W*$",
        r"^\W*required for certification\W*$",
    )
]

# Words that signal a legal, regulatory or contractual driver. A linked risk is the
# other accepted driver and is checked separately.
_OBLIGATION_TERMS = (
    "gdpr", "article", "regulation", "regulatory", "statutory", "legal", "law",
    "contract", "contractual", "customer commitment", "sla", "pci", "dss",
    "supervisory authority", "data protection act", "obligation", "dpa",
)

AUTHOR_TODO_MARKER = "TODO AUTHOR:BENNY"


@dataclass(frozen=True)
class ValidationError:
    field: str
    message: str


def _is_blank(value: str | None) -> bool:
    return value is None or not value.strip()


def _looks_circular(justification: str) -> bool:
    stripped = justification.strip()
    return any(pattern.search(stripped) for pattern in _CIRCULAR_PATTERNS)


def _names_an_obligation(justification: str) -> bool:
    lowered = justification.lower()
    return any(term in lowered for term in _OBLIGATION_TERMS)


def validate_entry(
    *,
    applicable: bool,
    justification_inclusion: str | None,
    justification_exclusion: str | None,
    implementation_status: ImplementationStatus,
    linked_risk_refs: list[str],
    actionable_remediation: list,
) -> list[ValidationError]:
    """Return every rule violation for a proposed SoA entry state.

    ``actionable_remediation`` holds remediation items that are not cancelled; each is
    expected to expose ``owner``, ``due_date`` and ``remediation_ref``.
    """
    errors: list[ValidationError] = []

    if applicable:
        if _is_blank(justification_inclusion):
            errors.append(
                ValidationError(
                    "justification_inclusion",
                    "An applicable control requires an inclusion justification stating why "
                    "the control is necessary — cite a risk, a legal or regulatory "
                    "obligation, or a contractual commitment.",
                )
            )
        else:
            text = justification_inclusion or ""
            is_placeholder = AUTHOR_TODO_MARKER in text
            if not is_placeholder and _looks_circular(text):
                errors.append(
                    ValidationError(
                        "justification_inclusion",
                        "'Required by ISO 27001' is circular and explains nothing about "
                        "FinFlow. Clause 6.1.3 d) asks why the control is necessary: name "
                        "the risk it treats, or the law or contract that demands it.",
                    )
                )
            elif not is_placeholder and not linked_risk_refs and not _names_an_obligation(text):
                errors.append(
                    ValidationError(
                        "justification_inclusion",
                        "The inclusion justification names no driver. Link at least one "
                        "risk, or reference the legal, regulatory or contractual "
                        "obligation the control satisfies.",
                    )
                )

        if implementation_status != ImplementationStatus.IMPLEMENTED:
            if not actionable_remediation:
                errors.append(
                    ValidationError(
                        "linked_remediation_ids",
                        f"This control is applicable and {implementation_status.value}, so it "
                        "is a gap. A gap requires at least one remediation item with an "
                        "owner and a due date.",
                    )
                )
            else:
                for item in actionable_remediation:
                    if _is_blank(getattr(item, "owner", None)):
                        errors.append(
                            ValidationError(
                                "linked_remediation_ids",
                                f"Remediation {item.remediation_ref} has no owner.",
                            )
                        )
                    if getattr(item, "due_date", None) is None:
                        errors.append(
                            ValidationError(
                                "linked_remediation_ids",
                                f"Remediation {item.remediation_ref} has no due date.",
                            )
                        )
    else:
        if _is_blank(justification_exclusion):
            errors.append(
                ValidationError(
                    "justification_exclusion",
                    "An excluded control requires an exclusion justification. State where "
                    "the risk went — transferred, addressed by another control, or genuinely "
                    "absent — not merely that the control does not apply.",
                )
            )
        if implementation_status != ImplementationStatus.NOT_IMPLEMENTED:
            errors.append(
                ValidationError(
                    "implementation_status",
                    "An excluded control cannot carry an implementation status other than "
                    "NOT_IMPLEMENTED. A control FinFlow has declared out of scope cannot "
                    "simultaneously be implemented.",
                )
            )

    return errors


def entry_errors(entry) -> list[ValidationError]:
    """Validate a persisted ``SoAEntry`` in its current state."""
    return validate_entry(
        applicable=entry.applicable,
        justification_inclusion=entry.justification_inclusion,
        justification_exclusion=entry.justification_exclusion,
        implementation_status=entry.implementation_status,
        linked_risk_refs=[risk.risk_ref for risk in entry.linked_risks],
        actionable_remediation=[
            item
            for item in entry.linked_remediation
            if item.status != RemediationStatus.CANCELLED
        ],
    )
