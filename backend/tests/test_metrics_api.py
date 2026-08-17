"""KRI dashboard and the executive view."""

CONTROL_ID_MARKERS = ("A.5.", "A.6.", "A.7.", "A.8.", "AC-0", "DP-0", "OP-0", "CM-0", "TP-0")


def test_seven_indicators_each_with_a_reproducible_formula(client):
    kris = client.get("/kris").json()
    assert len(kris) == 7
    assert [k["kri_ref"] for k in kris] == [f"KRI-{n:03d}" for n in range(1, 8)]
    for kri in kris:
        assert len(kri["formula_description"].split()) >= 20, kri["kri_ref"]
        assert kri["data_source"]
        assert kri["owner_role"]
        assert kri["rationale"]


def test_each_indicator_carries_a_six_point_trend_ending_today(client):
    for kri in client.get("/kris").json():
        assert len(kri["trend"]) == 6, kri["kri_ref"]
        assert kri["trend"][-1]["is_current"] is True
        assert sum(1 for p in kri["trend"] if p["is_current"]) == 1


def test_the_current_point_is_computed_not_stored(client):
    """The live figure must reflect the registers, not the seeded history."""
    kris = {k["kri_ref"]: k for k in client.get("/kris").json()}

    # SoA implementation, computed from the SoA itself.
    overview = client.get("/soa/overview").json()
    assert kris["KRI-003"]["current_value"] == overview["percent_implemented"]

    # Risks above appetite, computed from the register.
    summary = client.get("/risks/summary").json()
    assert kris["KRI-005"]["current_value"] == float(summary["exceeding_appetite"])

    # Expired acceptances, computed from the acceptance register.
    exceptions = client.get("/risk-exceptions/summary").json()
    assert kris["KRI-007"]["current_value"] == float(exceptions["expired"])


def test_the_mfa_indicator_reads_sixty_percent_from_the_workpaper(client):
    kri = next(k for k in client.get("/kris").json() if k["kri_ref"] == "KRI-001")
    assert kri["current_value"] == 60.0
    assert kri["current_band"] == "RED"
    assert "TEST-003" in kri["current_detail"]


def test_mean_time_to_remediate_is_actually_measurable(client):
    """Regression: raised_date was added to the model but not written by the seed
    loader, which made this indicator silently report NO_DATA."""
    kri = next(k for k in client.get("/kris").json() if k["kri_ref"] == "KRI-002")
    assert kri["current_value"] is not None, kri["current_detail"]
    assert kri["current_value"] == 105.0
    assert kri["current_band"] == "RED"
    assert "REM-018" in kri["current_detail"]


def test_every_indicator_that_should_have_data_has_it(client):
    for kri in client.get("/kris").json():
        assert kri["current_value"] is not None, f"{kri['kri_ref']}: {kri['current_detail']}"


def test_bands_respect_direction(client):
    kris = {k["kri_ref"]: k for k in client.get("/kris").json()}
    # Higher is better: 65.5% against a green floor of 95 and amber floor of 80.
    assert kris["KRI-003"]["direction"] == "HIGHER_IS_BETTER"
    assert kris["KRI-003"]["current_band"] == "RED"
    # Lower is better: 1 expired acceptance against a green ceiling of 0, amber of 1.
    assert kris["KRI-007"]["direction"] == "LOWER_IS_BETTER"
    assert kris["KRI-007"]["current_value"] == 1.0
    assert kris["KRI-007"]["current_band"] == "AMBER"


def test_soa_implementation_went_backwards_after_testing(client):
    """The trend records a real regression: TEST-008 downgraded A.8.11."""
    kri = next(k for k in client.get("/kris").json() if k["kri_ref"] == "KRI-003")
    july = next(p for p in kri["trend"] if p["period_end"] == "2026-07-31")
    assert kri["current_value"] < july["value"]
    assert kri["movement"] == "IMPROVING"  # over six periods it is still up overall


def test_movement_accounts_for_direction(client):
    """A falling mean-time-to-remediate is an improvement; a falling percentage is not."""
    kris = {k["kri_ref"]: k for k in client.get("/kris").json()}
    assert kris["KRI-004"]["movement"] == "IMPROVING"   # test coverage rising
    assert kris["KRI-006"]["movement"] == "DETERIORATING"  # evidence freshness falling
    assert kris["KRI-007"]["movement"] == "DETERIORATING"  # expired acceptances rising


def test_no_data_is_distinct_from_zero(client):
    """A metric with an empty population is not performing perfectly."""
    from app.models.kri import KriDefinition

    definition = KriDefinition(
        kri_ref="X", name="x", formula_description="x", data_source="x", rationale="x",
        unit="PERCENT", direction="HIGHER_IS_BETTER", green_threshold=90.0,
        amber_threshold=70.0, owner_role="x", measurement_frequency="MONTHLY",
    )
    assert definition.band_for(None).value == "NO_DATA"
    assert definition.band_for(0.0).value == "RED"


def test_unknown_indicator_returns_404(client):
    assert client.get("/kris/KRI-999").status_code == 404


# --- Executive view ------------------------------------------------------------


def test_the_executive_summary_is_written_for_a_non_technical_reader(client):
    summary = client.get("/executive-summary").json()
    prose = " ".join(
        [summary["posture_statement"], summary["third_party"]["summary"]]
        + [p["headline"] + " " + p["why"] for p in summary["priorities"]]
        + [r["plain_title"] + " " + r["what_could_happen"] for r in summary["top_risks"]]
    )
    for marker in CONTROL_ID_MARKERS:
        assert marker not in prose, f"control identifier '{marker}' leaked into board prose"
    for jargon in ("Annex A", "residual", "SoA", "inherent", "KRI"):
        assert jargon not in prose, f"jargon '{jargon}' leaked into board prose"


def test_the_summary_reports_the_same_numbers_as_the_registers(client):
    summary = client.get("/executive-summary").json()
    soa = client.get("/soa/overview").json()
    risks = client.get("/risks/summary").json()

    assert summary["safeguards_required"] == soa["applicable"]
    assert summary["safeguards_in_place"] == soa["implemented"]
    assert summary["safeguards_percent"] == soa["percent_implemented"]
    assert summary["risks_beyond_agreed_limit"] == risks["exceeding_appetite"]
    assert summary["risks_total"] == risks["total"]


def test_exactly_five_top_risks_and_three_priorities(client):
    summary = client.get("/executive-summary").json()
    assert len(summary["top_risks"]) == 5
    assert len(summary["priorities"]) == 3
    for priority in summary["priorities"]:
        assert priority["owner"]
        assert priority["by_when"]
        assert len(priority["why"].split()) >= 25


def test_top_risks_are_ordered_by_residual_and_flag_breaches(client):
    summary = client.get("/executive-summary").json()
    refs = [r["risk_ref"] for r in summary["top_risks"]]
    scores = [client.get(f"/risks/{ref}").json()["residual"]["score"] for ref in refs]
    assert scores == sorted(scores, reverse=True)
    assert any(r["beyond_agreed_limit"] for r in summary["top_risks"])


def test_risks_carried_without_a_decision_are_surfaced(client):
    summary = client.get("/executive-summary").json()
    exceptions = client.get("/risk-exceptions/summary").json()
    assert summary["risks_carried_without_a_decision"] == len(exceptions["uncovered_breaches"])
    assert summary["risks_carried_without_a_decision"] > 0


def test_posture_reflects_the_state_of_the_register(client):
    summary = client.get("/executive-summary").json()
    assert summary["posture_key"] == "STRAINED"
    assert len(summary["posture_statement"].split()) >= 15


# --- Reports -------------------------------------------------------------------


def test_all_three_reports_are_implemented_and_render(client):
    reports = client.get("/reports").json()
    assert len(reports) == 3
    assert all(r["implemented"] for r in reports)
    for report in reports:
        assert report["endpoint"], report["code"]
        response = client.get(report["endpoint"])
        assert response.status_code == 200, report["code"]
        assert response.content.startswith(b"%PDF-"), report["code"]


def test_the_auditor_can_download_every_report(auditor_client):
    for report in auditor_client.get("/reports").json():
        assert auditor_client.get(report["endpoint"]).status_code == 200
