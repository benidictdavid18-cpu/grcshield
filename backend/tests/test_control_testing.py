"""Unit tests for control testing rules, independent of the database."""

from datetime import date

import pytest

from app.services.control_testing import (
    DesignEffectiveness as Design,
)
from app.services.control_testing import (
    OperatingEffectiveness as Operating,
)
from app.services.control_testing import (
    SampleSelectionMethod as Method,
)
from app.services.control_testing import (
    TestConclusion as Conclusion,
)
from app.services.control_testing import (
    FindingSeverity,
    basis_is_optimistic,
    basis_supported_by_control,
    requires_finding,
    severity_for,
    strongest_supported_basis,
    validate_effectiveness,
    validate_test,
)
from app.services.risk_scoring import ControlEffectivenessBasis as Basis


def fields(errors):
    return {e.field for e in errors}


def a_test(**overrides):
    payload = dict(
        population_size=100,
        sample_size=25,
        sample_selection_method=Method.RANDOM,
        sampling_rationale="Random selection removes bias across the period.",
        exceptions_count=0,
        conclusion=Conclusion.PASS,
        exception_details=None,
        tester="Priya Raghavan",
        reviewed_by="Head of Legal & Compliance",
    )
    payload.update(overrides)
    return validate_test(**payload)


# --- Design vs operating -----------------------------------------------------


def test_deficient_design_cannot_operate_effectively():
    errors = validate_effectiveness(Design.DEFICIENT, Operating.EFFECTIVE)
    assert fields(errors) == {"operating_effectiveness"}


@pytest.mark.parametrize(
    "operating",
    [Operating.EFFECTIVE_WITH_EXCEPTIONS, Operating.INEFFECTIVE, Operating.NOT_TESTED],
)
def test_deficient_design_permits_lower_operating_ratings(operating):
    """The ceiling is EFFECTIVE_WITH_EXCEPTIONS, not a blanket ban."""
    assert validate_effectiveness(Design.DEFICIENT, operating) == []


@pytest.mark.parametrize("design", [Design.EFFECTIVE, Design.NOT_ASSESSED])
def test_a_sound_design_places_no_cap(design):
    assert validate_effectiveness(design, Operating.EFFECTIVE) == []


# --- Sampling ---------------------------------------------------------------


def test_sample_cannot_exceed_population():
    assert fields(a_test(population_size=10, sample_size=25)) == {"sample_size"}


def test_full_population_must_actually_be_full():
    errors = a_test(sample_selection_method=Method.FULL_POPULATION, sample_size=25,
                    population_size=100)
    assert fields(errors) == {"sample_size"}


def test_full_population_passes_when_sample_equals_population():
    assert a_test(
        sample_selection_method=Method.FULL_POPULATION, sample_size=100, population_size=100
    ) == []


def test_sampling_rationale_is_mandatory():
    assert fields(a_test(sampling_rationale="   ")) == {"sampling_rationale"}


def test_period_must_be_a_real_span():
    errors = a_test(
        period_covered_start=date(2026, 6, 30), period_covered_end=date(2026, 1, 1)
    )
    assert fields(errors) == {"period_covered_end"}


# --- Exceptions and conclusions ----------------------------------------------


def test_exceptions_cannot_yield_a_clean_pass():
    errors = a_test(exceptions_count=3, conclusion=Conclusion.PASS, exception_details="x")
    assert "conclusion" in fields(errors)


def test_pass_with_exceptions_requires_exceptions():
    assert fields(a_test(exceptions_count=0, conclusion=Conclusion.PASS_WITH_EXCEPTIONS)) == {
        "conclusion"
    }


def test_exceptions_must_be_described():
    errors = a_test(
        exceptions_count=3, conclusion=Conclusion.PASS_WITH_EXCEPTIONS, exception_details=" "
    )
    assert "exception_details" in fields(errors)


def test_exceptions_cannot_exceed_the_sample():
    errors = a_test(
        exceptions_count=99, conclusion=Conclusion.FAIL, exception_details="everything"
    )
    assert "exceptions_count" in fields(errors)


def test_reviewer_cannot_be_the_tester():
    assert fields(a_test(tester="Priya Raghavan", reviewed_by="priya raghavan")) == {
        "reviewed_by"
    }


def test_a_clean_workpaper_passes():
    assert a_test() == []


# --- Cascade ----------------------------------------------------------------


@pytest.mark.parametrize(
    "conclusion,expected",
    [
        (Conclusion.PASS, False),
        (Conclusion.PASS_WITH_EXCEPTIONS, True),
        (Conclusion.FAIL, True),
    ],
)
def test_non_clean_conclusions_require_a_finding(conclusion, expected):
    assert requires_finding(conclusion) is expected


def test_default_severity_scales_with_the_exception_rate():
    assert severity_for(Conclusion.FAIL, 2, 11) == FindingSeverity.HIGH
    assert severity_for(Conclusion.PASS_WITH_EXCEPTIONS, 6, 15) == FindingSeverity.MEDIUM
    assert severity_for(Conclusion.PASS_WITH_EXCEPTIONS, 3, 45) == FindingSeverity.LOW


# --- Basis support (the Phase 2 tie-in) --------------------------------------


@pytest.mark.parametrize(
    "basis", [Basis.TESTED_EFFECTIVE, Basis.TESTED_WITH_EXCEPTIONS, Basis.TESTED_INEFFECTIVE]
)
def test_a_tested_basis_is_not_supported_by_an_untested_control(basis):
    assert basis_supported_by_control(basis, Operating.NOT_TESTED) is False


@pytest.mark.parametrize("basis", [Basis.NOT_TESTED, Basis.DESIGN_ONLY])
def test_untested_and_design_only_are_always_supported(basis):
    assert basis_supported_by_control(basis, Operating.NOT_TESTED) is True


def test_design_only_is_supported_when_the_design_was_assessed():
    assert strongest_supported_basis(Design.EFFECTIVE, Operating.NOT_TESTED) == Basis.DESIGN_ONLY
    assert basis_is_optimistic(Basis.DESIGN_ONLY, Operating.NOT_TESTED, Design.EFFECTIVE) is False


def test_design_only_is_optimistic_when_the_design_was_never_assessed():
    assert basis_is_optimistic(Basis.DESIGN_ONLY, Operating.NOT_TESTED, Design.NOT_ASSESSED)


def test_claiming_full_effectiveness_on_a_control_with_exceptions_is_optimistic():
    assert basis_is_optimistic(
        Basis.TESTED_EFFECTIVE, Operating.EFFECTIVE_WITH_EXCEPTIONS, Design.EFFECTIVE
    )
    # Claiming less than the control supports is conservative and always fine.
    assert not basis_is_optimistic(
        Basis.TESTED_WITH_EXCEPTIONS, Operating.EFFECTIVE, Design.EFFECTIVE
    )
