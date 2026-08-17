"""Unit tests for the Clause 6.1.3 d) validation rules, independent of the database."""

from datetime import date
from types import SimpleNamespace

import pytest

from app.models.soa import ImplementationStatus
from app.services.soa_validation import validate_entry

IMPLEMENTED = ImplementationStatus.IMPLEMENTED
PARTIAL = ImplementationStatus.PARTIALLY_IMPLEMENTED
NOT_IMPLEMENTED = ImplementationStatus.NOT_IMPLEMENTED


def remediation(ref="REM-001", owner="Head of Engineering", due=date(2026, 12, 1)):
    return SimpleNamespace(remediation_ref=ref, owner=owner, due_date=due)


def fields(errors):
    return {error.field for error in errors}


# --- Applicable controls ----------------------------------------------------


def test_applicable_control_needs_an_inclusion_justification():
    errors = validate_entry(
        applicable=True,
        justification_inclusion="   ",
        justification_exclusion=None,
        implementation_status=IMPLEMENTED,
        linked_risk_refs=["RISK-001"],
        actionable_remediation=[],
    )
    assert fields(errors) == {"justification_inclusion"}


@pytest.mark.parametrize(
    "text",
    [
        "Required by ISO 27001.",
        "ISO 27001 requires this control.",
        "Annex A requires it.",
        "Mandated by the standard.",
        "Best practice",
        "Required for certification",
    ],
)
def test_circular_justifications_are_rejected(text):
    """'We do it because the standard says to' explains nothing about FinFlow."""
    errors = validate_entry(
        applicable=True,
        justification_inclusion=text,
        justification_exclusion=None,
        implementation_status=IMPLEMENTED,
        linked_risk_refs=["RISK-001"],
        actionable_remediation=[],
    )
    assert fields(errors) == {"justification_inclusion"}
    assert "circular" in errors[0].message.lower()


def test_justification_with_no_driver_is_rejected():
    errors = validate_entry(
        applicable=True,
        justification_inclusion="This control is important to the business and we do it.",
        justification_exclusion=None,
        implementation_status=IMPLEMENTED,
        linked_risk_refs=[],
        actionable_remediation=[],
    )
    assert fields(errors) == {"justification_inclusion"}


def test_a_linked_risk_is_an_acceptable_driver():
    errors = validate_entry(
        applicable=True,
        justification_inclusion="Treats the account takeover scenario recorded in the register.",
        justification_exclusion=None,
        implementation_status=IMPLEMENTED,
        linked_risk_refs=["RISK-001"],
        actionable_remediation=[],
    )
    assert errors == []


def test_a_legal_obligation_is_an_acceptable_driver_without_a_risk():
    errors = validate_entry(
        applicable=True,
        justification_inclusion="GDPR Article 32 imposes a direct statutory duty on FinFlow.",
        justification_exclusion=None,
        implementation_status=IMPLEMENTED,
        linked_risk_refs=[],
        actionable_remediation=[],
    )
    assert errors == []


def test_author_placeholder_is_accepted_without_triggering_driver_checks():
    """The TODO marker is a known gap, flagged in the UI rather than blocked."""
    errors = validate_entry(
        applicable=True,
        justification_inclusion="TODO AUTHOR:BENNY — decide the driver and write this.",
        justification_exclusion=None,
        implementation_status=IMPLEMENTED,
        linked_risk_refs=[],
        actionable_remediation=[],
    )
    assert errors == []


# --- Gaps -------------------------------------------------------------------


@pytest.mark.parametrize("status", [PARTIAL, NOT_IMPLEMENTED])
def test_a_gap_requires_a_remediation_item(status):
    errors = validate_entry(
        applicable=True,
        justification_inclusion="Treats RISK-004.",
        justification_exclusion=None,
        implementation_status=status,
        linked_risk_refs=["RISK-004"],
        actionable_remediation=[],
    )
    assert fields(errors) == {"linked_remediation_ids"}


def test_a_gap_with_remediation_passes():
    errors = validate_entry(
        applicable=True,
        justification_inclusion="Treats RISK-004.",
        justification_exclusion=None,
        implementation_status=PARTIAL,
        linked_risk_refs=["RISK-004"],
        actionable_remediation=[remediation()],
    )
    assert errors == []


def test_remediation_without_an_owner_or_date_does_not_satisfy_the_rule():
    errors = validate_entry(
        applicable=True,
        justification_inclusion="Treats RISK-004.",
        justification_exclusion=None,
        implementation_status=PARTIAL,
        linked_risk_refs=["RISK-004"],
        actionable_remediation=[remediation(owner="  ", due=None)],
    )
    assert fields(errors) == {"linked_remediation_ids"}
    assert len(errors) == 2


def test_implemented_control_needs_no_remediation():
    errors = validate_entry(
        applicable=True,
        justification_inclusion="Treats RISK-001.",
        justification_exclusion=None,
        implementation_status=IMPLEMENTED,
        linked_risk_refs=["RISK-001"],
        actionable_remediation=[],
    )
    assert errors == []


# --- Excluded controls ------------------------------------------------------


def test_excluded_control_needs_an_exclusion_justification():
    errors = validate_entry(
        applicable=False,
        justification_inclusion=None,
        justification_exclusion=None,
        implementation_status=NOT_IMPLEMENTED,
        linked_risk_refs=[],
        actionable_remediation=[],
    )
    assert fields(errors) == {"justification_exclusion"}


@pytest.mark.parametrize("status", [IMPLEMENTED, PARTIAL])
def test_excluded_control_cannot_claim_implementation(status):
    errors = validate_entry(
        applicable=False,
        justification_inclusion=None,
        justification_exclusion="Transferred to AWS under the shared responsibility model.",
        implementation_status=status,
        linked_risk_refs=[],
        actionable_remediation=[],
    )
    assert fields(errors) == {"implementation_status"}


def test_a_valid_exclusion_passes():
    errors = validate_entry(
        applicable=False,
        justification_inclusion=None,
        justification_exclusion="No premises exist; risk transferred to AWS and assured "
        "through their SOC 2 Type II report under TP-002.",
        implementation_status=NOT_IMPLEMENTED,
        linked_risk_refs=[],
        actionable_remediation=[],
    )
    assert errors == []
