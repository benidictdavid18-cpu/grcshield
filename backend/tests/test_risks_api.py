"""API tests for the risk register, appetite comparison and the residual write rules."""

TODO_MARKER = "TODO AUTHOR:BENNY"


def test_register_holds_twenty_risks_across_nine_categories(client):
    risks = client.get("/risks").json()
    assert len(risks) == 20
    assert len({r["category"] for r in risks}) == 9
    assert [r["risk_ref"] for r in risks] == [f"RISK-{n:03d}" for n in range(1, 21)]


def test_appetite_is_per_category_with_a_business_approver(client):
    appetite = {a["category"]: a for a in client.get("/risk-appetite").json()}
    assert len(appetite) == 9
    # Differentiated, not one global number.
    assert appetite["DATA_PRIVACY"]["max_acceptable_band"] == "LOW"
    assert appetite["BUSINESS_CONTINUITY"]["max_acceptable_band"] == "HIGH"
    assert appetite["CYBERSECURITY"]["max_acceptable_band"] == "MEDIUM"
    # Risk acceptance is a business decision -- no approver is the security function.
    approvers = {a["approver_role"] for a in appetite.values()}
    assert not {a for a in approvers if "security" in a.lower()}
    for entry in appetite.values():
        assert len(entry["rationale"].split()) >= 15


def test_inherent_and_residual_are_scored_independently(client):
    """RISK-004 is the walkthrough risk: partial MFA coverage, impact immovable."""
    risk = client.get("/risks/RISK-004").json()
    assert risk["inherent"] == {"likelihood": 4, "impact": 5, "score": 20, "band": "CRITICAL"}
    assert risk["residual"] == {"likelihood": 3, "impact": 5, "score": 15, "band": "HIGH"}
    # Impact is unchanged: no arithmetic model could produce this from one percentage.
    assert risk["inherent"]["impact"] == risk["residual"]["impact"]


def test_risk_004_breaches_its_category_appetite(client):
    risk = client.get("/risks/RISK-004").json()
    assert risk["appetite"]["max_acceptable_band"] == "MEDIUM"
    assert risk["appetite"]["exceeds_appetite"] is True
    assert risk["appetite"]["approver_role"] == "Chief Technology Officer"


def test_risk_004_control_chain_reaches_annex_a_8_5(client):
    risk = client.get("/risks/RISK-004").json()
    controls = {c["control_id"]: c for c in risk["controls"]}
    assert "AC-002" in controls
    assert controls["AC-002"]["effectiveness_basis"] == "TESTED_WITH_EXCEPTIONS"
    assert controls["AC-002"]["credits_reduction"] is True
    assert "A.8.5" in controls["AC-002"]["annex_a_refs"]


def test_untested_controls_are_flagged_and_earn_no_reduction(client):
    """RISK-019: every control untested, so residual must equal inherent."""
    risk = client.get("/risks/RISK-019").json()
    assert risk["inherent"]["score"] == risk["residual"]["score"]
    assert risk["has_uncredited_controls"] is True
    assert all(c["credits_reduction"] is False for c in risk["controls"])
    assert all(c["effectiveness_basis"] == "NOT_TESTED" for c in risk["controls"])


def test_no_residual_justification_is_left_unwritten(client):
    """Every one of the twenty is written.

    This test used to assert the opposite -- that five were deliberately blank. The
    marker mechanism is still in place and still enforced by the API, the reports and
    the UI; there is simply nothing carrying it any more.
    """
    outstanding = [r for r in client.get("/risks").json() if r["justification_outstanding"]]
    assert outstanding == []
    for summary in client.get("/risks").json():
        detail = client.get(f"/risks/{summary['risk_ref']}").json()
        assert TODO_MARKER not in detail["residual_justification"]


def test_every_justification_is_substantive(client):
    for summary in client.get("/risks").json():
        detail = client.get(f"/risks/{summary['risk_ref']}").json()
        assert len(detail["residual_justification"].split()) >= 25


def test_every_justification_names_a_control_actually_linked_to_that_risk(client):
    """The check that makes a justification reviewable rather than merely present.

    Clause-free prose that never names a control cannot be argued with. A justification
    that names AC-003 can be checked against AC-003's test, and disagreed with.

    RISK-019 is the exception the rule needs: none of its controls may be credited, so
    its justification explains why *no* reduction is claimed rather than attributing one.
    A justification that named a control there would be claiming something the register
    refuses to record.
    """
    for summary in client.get("/risks").json():
        detail = client.get(f"/risks/{summary['risk_ref']}").json()
        text = detail["residual_justification"]
        linked = {control["control_id"] for control in detail["controls"]}
        if detail["residual"]["score"] < detail["inherent"]["score"]:
            assert any(control_id in text for control_id in linked), detail["risk_ref"]


def test_register_summary_counts_breaches_and_outstanding_work(client):
    summary = client.get("/risks/summary").json()
    assert summary["total"] == 20
    assert summary["justifications_outstanding"] == 0
    # Seven. Two of them arrived the same way: TEST-008 rated DP-005 ineffective,
    # which withdrew the reduction RISK-008 was carrying, and forced RISK-018 back to
    # its inherent level once its only preventive control was gone.
    assert summary["exceeding_appetite"] == 7
    assert sum(summary["by_residual_band"].values()) == 20
    assert summary["bands"] == [
        {"band": "LOW", "min_score": 1, "max_score": 4},
        {"band": "MEDIUM", "min_score": 5, "max_score": 9},
        {"band": "HIGH", "min_score": 10, "max_score": 16},
        {"band": "CRITICAL", "min_score": 17, "max_score": 25},
    ]


def test_filter_to_risks_exceeding_appetite(client):
    breaching = client.get("/risks?exceeding_appetite=true").json()
    assert {r["risk_ref"] for r in breaching} == {
        "RISK-002", "RISK-004", "RISK-008", "RISK-009", "RISK-010", "RISK-018",
        "RISK-019",
    }
    for risk in breaching:
        assert risk["appetite"]["exceeds_appetite"] is True


# --- Write-path rules -------------------------------------------------------


def test_empty_residual_justification_is_rejected(client):
    response = client.patch(
        "/risks/RISK-001/residual",
        json={"residual_likelihood": 2, "residual_impact": 4, "residual_justification": "   "},
    )
    assert response.status_code == 422


def test_missing_residual_justification_is_rejected(client):
    response = client.patch(
        "/risks/RISK-001/residual",
        json={"residual_likelihood": 2, "residual_impact": 4},
    )
    assert response.status_code == 422


def test_scores_outside_the_matrix_are_rejected(client):
    for payload in (
        {"residual_likelihood": 0, "residual_impact": 4},
        {"residual_likelihood": 6, "residual_impact": 4},
        {"residual_likelihood": 2, "residual_impact": 9},
    ):
        response = client.patch(
            "/risks/RISK-001/residual", json={**payload, "residual_justification": "valid text"}
        )
        assert response.status_code == 422


def test_reduction_is_refused_when_no_control_may_be_credited(client):
    """RISK-019's controls are all NOT_TESTED, so it cannot claim any reduction."""
    response = client.patch(
        "/risks/RISK-019/residual",
        json={
            "residual_likelihood": 1,
            "residual_impact": 3,
            "residual_justification": "Classification work is underway and should help.",
        },
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "NOT_TESTED" in detail or "TESTED_INEFFECTIVE" in detail


def test_scoring_residual_at_inherent_is_always_allowed(client):
    """The rule blocks unearned reductions, not honest ones."""
    response = client.patch(
        "/risks/RISK-019/residual",
        json={
            "residual_likelihood": 3,
            "residual_impact": 3,
            "residual_justification": "No reduction claimed; both controls remain untested.",
        },
    )
    assert response.status_code == 200
    assert response.json()["residual"]["score"] == 9


def test_a_valid_reduction_is_accepted_and_recomputes_the_band(client):
    response = client.patch(
        "/risks/RISK-001/residual",
        json={
            "residual_likelihood": 1,
            "residual_impact": 4,
            "residual_justification": "AC-002 tested effective; likelihood reduced to 1.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["residual"] == {"likelihood": 1, "impact": 4, "score": 4, "band": "LOW"}
    assert body["appetite"]["exceeds_appetite"] is False
    assert body["justification_outstanding"] is False


def test_unknown_risk_returns_404(client):
    assert client.get("/risks/RISK-999").status_code == 404
