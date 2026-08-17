"""Unit tests for the scoring rules, independent of the database."""

import pytest

from app.services.risk_scoring import (
    ControlEffectivenessBasis as Basis,
)
from app.services.risk_scoring import (
    RiskBand,
    ScoreOutOfRange,
    band_for,
    basis_credits_reduction,
    exceeds_appetite,
    score,
)


@pytest.mark.parametrize(
    "likelihood,impact,expected",
    [(1, 1, 1), (1, 4, 4), (5, 1, 5), (3, 3, 9), (2, 5, 10), (4, 4, 16), (4, 5, 20), (5, 5, 25)],
)
def test_score_is_likelihood_times_impact(likelihood, impact, expected):
    assert score(likelihood, impact) == expected


@pytest.mark.parametrize("bad", [0, 6, -1, 25])
def test_scores_outside_the_matrix_are_rejected(bad):
    with pytest.raises(ScoreOutOfRange):
        score(bad, 3)


@pytest.mark.parametrize(
    "value,band",
    [
        (1, RiskBand.LOW), (4, RiskBand.LOW),
        (5, RiskBand.MEDIUM), (9, RiskBand.MEDIUM),
        (10, RiskBand.HIGH), (16, RiskBand.HIGH),
        (17, RiskBand.CRITICAL), (25, RiskBand.CRITICAL),
    ],
)
def test_band_boundaries_are_inclusive(value, band):
    assert band_for(value) == band


def test_every_achievable_score_lands_in_exactly_one_band():
    for likelihood in range(1, 6):
        for impact in range(1, 6):
            assert band_for(score(likelihood, impact)) in RiskBand


def test_appetite_comparison_is_by_band_not_score():
    # 10 (HIGH) breaches a MEDIUM ceiling; 9 (MEDIUM) does not, despite being close.
    assert exceeds_appetite(band_for(10), RiskBand.MEDIUM) is True
    assert exceeds_appetite(band_for(9), RiskBand.MEDIUM) is False
    assert exceeds_appetite(RiskBand.MEDIUM, RiskBand.MEDIUM) is False
    assert exceeds_appetite(RiskBand.CRITICAL, RiskBand.HIGH) is True
    assert exceeds_appetite(RiskBand.LOW, RiskBand.CRITICAL) is False


@pytest.mark.parametrize(
    "basis,credits",
    [
        (Basis.NOT_TESTED, False),
        (Basis.TESTED_INEFFECTIVE, False),
        (Basis.DESIGN_ONLY, True),
        (Basis.TESTED_EFFECTIVE, True),
        (Basis.TESTED_WITH_EXCEPTIONS, True),
    ],
)
def test_only_assessed_and_working_controls_may_be_credited(basis, credits):
    assert basis_credits_reduction(basis) is credits
