"""Unit tests for acceptance, GDPR and BIA rules, independent of the database."""

from datetime import date

import pytest

from app.services.privacy_continuity import (
    DpiaOutcome,
    ExceptionStatus,
    LawfulBasis,
    ResidualRiskLevel,
    TransferSafeguard,
    exception_state,
    validate_bia,
    validate_dpia,
    validate_exception,
    validate_ropa,
)

TODAY = date(2026, 8, 15)


def fields(errors):
    return {e.field for e in errors}


def an_exception(**overrides):
    payload = dict(
        approver_role="Chief Operating Officer",
        risk_owner_role="Chief Operating Officer",
        expiry_date=date(2027, 1, 1),
        approval_date=date(2026, 6, 1),
        business_justification="Building redundancy costs more than the expected loss.",
        review_trigger="Revisit if transaction volume doubles.",
        status=ExceptionStatus.APPROVED,
    )
    payload.update(overrides)
    return validate_exception(**payload)


# --- Risk acceptance ----------------------------------------------------------


def test_an_acceptance_must_expire():
    assert fields(an_exception(expiry_date=None)) == {"expiry_date"}


def test_expiry_must_follow_approval():
    assert fields(
        an_exception(approval_date=date(2026, 6, 1), expiry_date=date(2026, 5, 1))
    ) == {"expiry_date"}


@pytest.mark.parametrize(
    "approver",
    ["Head of Security", "CISO", "Security Engineer", "Marcus Whitfield, Compliance Analyst"],
)
def test_the_security_function_cannot_approve_an_acceptance(approver):
    errors = an_exception(approver_role=approver)
    assert fields(errors) == {"approver_role"}
    assert "security function" in errors[0].message


def test_the_approver_must_be_the_risk_owner():
    errors = an_exception(
        approver_role="Head of People", risk_owner_role="Chief Operating Officer"
    )
    assert fields(errors) == {"approver_role"}


def test_the_chief_executive_may_approve_on_behalf_of_an_owner():
    assert an_exception(
        approver_role="Chief Executive Officer", risk_owner_role="Chief Technology Officer"
    ) == []


def test_a_justification_and_a_review_trigger_are_both_required():
    assert fields(an_exception(business_justification="  ")) == {"business_justification"}
    assert fields(an_exception(review_trigger="")) == {"review_trigger"}


def test_an_approved_exception_needs_an_approval_date():
    assert fields(an_exception(approval_date=None)) == {"approval_date"}


@pytest.mark.parametrize(
    "expiry,status,expected",
    [
        (date(2026, 6, 30), ExceptionStatus.APPROVED, "EXPIRED"),
        (date(2026, 9, 5), ExceptionStatus.APPROVED, "EXPIRING_SOON"),
        (date(2026, 9, 14), ExceptionStatus.APPROVED, "EXPIRING_SOON"),
        (date(2026, 9, 16), ExceptionStatus.APPROVED, "APPROVED"),
        (date(2027, 1, 1), ExceptionStatus.REJECTED, "REJECTED"),
        (date(2025, 1, 1), ExceptionStatus.WITHDRAWN, "WITHDRAWN"),
    ],
)
def test_derived_state_cannot_hide_an_expiry(expiry, status, expected):
    """'APPROVED' must not quietly mean 'expired last year'."""
    assert exception_state(expiry, status, TODAY) == expected


# --- Article 30 ---------------------------------------------------------------


def a_ropa(**overrides):
    payload = dict(
        transfers_outside_eea=False,
        transfer_safeguard=TransferSafeguard.NOT_APPLICABLE,
        transfer_detail=None,
        retention_period="Seven years from transaction date.",
        lawful_basis=LawfulBasis.CONTRACT,
        legitimate_interests_assessment=None,
    )
    payload.update(overrides)
    return validate_ropa(**payload)


def test_a_transfer_outside_the_eea_needs_a_safeguard():
    errors = a_ropa(transfers_outside_eea=True, transfer_detail="India support staff.")
    assert fields(errors) == {"transfer_safeguard"}


def test_a_transfer_must_name_the_countries():
    errors = a_ropa(
        transfers_outside_eea=True,
        transfer_safeguard=TransferSafeguard.STANDARD_CONTRACTUAL_CLAUSES,
        transfer_detail="   ",
    )
    assert fields(errors) == {"transfer_detail"}


def test_a_safeguard_without_a_transfer_is_a_contradiction():
    errors = a_ropa(transfer_safeguard=TransferSafeguard.ADEQUACY_DECISION)
    assert fields(errors) == {"transfer_safeguard"}


def test_retention_period_is_required():
    assert fields(a_ropa(retention_period="  ")) == {"retention_period"}


def test_legitimate_interests_requires_a_balancing_test():
    errors = a_ropa(lawful_basis=LawfulBasis.LEGITIMATE_INTERESTS)
    assert fields(errors) == {"legitimate_interests_assessment"}
    assert a_ropa(
        lawful_basis=LawfulBasis.LEGITIMATE_INTERESTS,
        legitimate_interests_assessment="Balanced against merchant expectations.",
    ) == []


def test_a_valid_transfer_record_passes():
    assert a_ropa(
        transfers_outside_eea=True,
        transfer_safeguard=TransferSafeguard.STANDARD_CONTRACTUAL_CLAUSES,
        transfer_detail="Support staff in India, covered by SCCs.",
    ) == []


# --- Articles 35 and 36 --------------------------------------------------------


def a_dpia(**overrides):
    payload = dict(
        outcome=DpiaOutcome.PROCEED_WITH_MEASURES,
        residual_risk=ResidualRiskLevel.MEDIUM,
        dpo_consulted=True,
        supervisory_authority_consulted=False,
        mitigating_measures="Masking, access restriction, logging.",
        review_date=date(2027, 4, 9),
    )
    payload.update(overrides)
    return validate_dpia(**payload)


def test_the_dpo_must_be_consulted():
    assert fields(a_dpia(dpo_consulted=False)) == {"dpo_consulted"}


def test_high_residual_risk_cannot_simply_proceed():
    """Article 36(1): the controller cannot decide alone at this residual level."""
    for outcome in (DpiaOutcome.PROCEED, DpiaOutcome.PROCEED_WITH_MEASURES):
        errors = a_dpia(outcome=outcome, residual_risk=ResidualRiskLevel.HIGH)
        assert fields(errors) == {"supervisory_authority_consulted"}


def test_high_residual_risk_is_acceptable_once_the_authority_is_consulted():
    assert a_dpia(
        residual_risk=ResidualRiskLevel.HIGH, supervisory_authority_consulted=True
    ) == []


def test_choosing_to_consult_is_itself_a_valid_outcome():
    assert a_dpia(
        outcome=DpiaOutcome.CONSULT_SUPERVISORY_AUTHORITY,
        residual_risk=ResidualRiskLevel.HIGH,
    ) == []


def test_proceed_with_measures_requires_measures():
    assert fields(a_dpia(mitigating_measures="   ")) == {"mitigating_measures"}


def test_a_live_assessment_needs_a_review_date():
    assert fields(a_dpia(review_date=None)) == {"review_date"}
    # An assessment that concluded "do not proceed" has nothing left to review.
    assert a_dpia(outcome=DpiaOutcome.DO_NOT_PROCEED, review_date=None) == []


# --- Business impact analysis ---------------------------------------------------


def test_recovery_target_cannot_exceed_what_the_business_tolerates():
    errors = validate_bia(rto_hours=8.0, rpo_hours=1.0, mtpd_hours=4.0)
    assert fields(errors) == {"rto_hours"}
    assert "fails on the day it is written" in errors[0].message


def test_recovery_point_cannot_exceed_the_tolerable_period():
    assert fields(validate_bia(rto_hours=2.0, rpo_hours=48.0, mtpd_hours=4.0)) == {"rpo_hours"}


def test_negative_objectives_are_rejected():
    assert "rto_hours" in fields(validate_bia(rto_hours=-1.0, rpo_hours=1.0, mtpd_hours=4.0))


def test_rto_equal_to_mtpd_is_permitted_but_has_no_headroom():
    assert validate_bia(rto_hours=4.0, rpo_hours=0.25, mtpd_hours=4.0) == []
