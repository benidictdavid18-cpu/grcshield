"""API tests for the acceptance, GDPR and continuity registers."""

VALID_EXCEPTION = {
    "risk_ref": "RISK-005",
    "requested_by": "Head of Engineering",
    "business_justification": "Patching the remaining medium findings competes with the "
    "certification programme this quarter.",
    "compensating_controls": "OP-003 image scanning blocks critical findings at build.",
    "approver_role": "Chief Technology Officer",
    "approval_date": "2026-08-01",
    "expiry_date": "2026-12-31",
    "review_trigger": "Revisit if a medium finding is exploited or the backlog doubles.",
    "status": "APPROVED",
}


# --- Assets -------------------------------------------------------------------


def test_the_asset_register_backs_the_privacy_records(client):
    assets = client.get("/assets").json()
    assert len(assets) == 12
    refs = {a["asset_ref"] for a in assets}
    # The two stores TEST-008 found holding unmasked customer data.
    assert {"AST-007", "AST-008"} <= refs
    personal = client.get("/assets?holds_personal_data=true").json()
    assert len(personal) == 11


# --- Risk acceptance ------------------------------------------------------------


def test_four_exceptions_with_a_full_range_of_states(client):
    exceptions = {e["exception_ref"]: e for e in client.get("/risk-exceptions").json()}
    assert len(exceptions) == 4
    assert exceptions["EXC-001"]["state"] == "EXPIRING_SOON"
    assert exceptions["EXC-002"]["state"] == "APPROVED"
    assert exceptions["EXC-003"]["state"] == "EXPIRED"
    assert exceptions["EXC-004"]["state"] == "REJECTED"


def test_every_approver_is_a_business_owner(client):
    for exception in client.get("/risk-exceptions").json():
        approver = exception["approver_role"]
        assert "security" not in approver.lower()
        assert approver in (exception["risk_owner_role"], "Chief Executive Officer")


def test_every_exception_has_an_expiry_and_a_review_trigger(client):
    for exception in client.get("/risk-exceptions").json():
        assert exception["expiry_date"]
        assert exception["review_trigger"].strip()


def test_the_rejected_exception_records_why(client):
    """A register that only records approvals is a record of agreement, not decisions."""
    exception = next(
        e for e in client.get("/risk-exceptions").json() if e["exception_ref"] == "EXC-004"
    )
    assert exception["risk_ref"] == "RISK-004"
    assert exception["status"] == "REJECTED"
    assert exception["approval_date"] is None
    assert "not defensible" in exception["decision_note"]


def test_summary_surfaces_breaches_with_no_live_acceptance(client):
    summary = client.get("/risk-exceptions/summary").json()
    assert summary["total"] == 4
    assert summary["expired"] == 1
    assert summary["expiring_soon"] == 1
    assert summary["expiry_warning_days"] == 30
    # Every risk above appetite is currently uncovered: EXC-003 expired and EXC-004 was
    # refused, so nothing live covers RISK-010 or RISK-004.
    assert summary["uncovered_breaches"] == [
        "RISK-002", "RISK-004", "RISK-008", "RISK-009", "RISK-010", "RISK-018",
        "RISK-019",
    ]


def test_an_acceptance_without_an_expiry_is_rejected(client):
    response = client.post(
        "/risk-exceptions", json={**VALID_EXCEPTION, "expiry_date": None}
    )
    assert response.status_code == 422
    assert any(e["field"] == "expiry_date" for e in response.json()["detail"])


def test_the_security_function_cannot_approve(client):
    response = client.post(
        "/risk-exceptions", json={**VALID_EXCEPTION, "approver_role": "Head of Security"}
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any("security function" in e["message"] for e in detail)


def test_a_non_owner_cannot_approve(client):
    response = client.post(
        "/risk-exceptions", json={**VALID_EXCEPTION, "approver_role": "Head of People"}
    )
    assert response.status_code == 422
    assert any(e["field"] == "approver_role" for e in response.json()["detail"])


def test_a_valid_acceptance_is_recorded(client):
    response = client.post("/risk-exceptions", json=VALID_EXCEPTION)
    assert response.status_code == 201
    body = response.json()
    assert body["risk_ref"] == "RISK-005"
    assert body["state"] == "APPROVED"
    assert body["exception_ref"].startswith("EXC-")


def test_unknown_risk_returns_404(client):
    response = client.post("/risk-exceptions", json={**VALID_EXCEPTION, "risk_ref": "RISK-999"})
    assert response.status_code == 404


# --- Article 30 -------------------------------------------------------------------


def test_six_processing_activities(client):
    entries = client.get("/ropa").json()
    assert len(entries) == 6
    assert [e["ropa_ref"] for e in entries] == [f"ROPA-{n:03d}" for n in range(1, 7)]


def test_every_activity_records_the_article_30_fields(client):
    for entry in client.get("/ropa").json():
        assert entry["purpose"]
        assert entry["data_subject_categories"]
        assert entry["personal_data_categories"]
        assert entry["recipients"]
        assert entry["retention_period"]
        assert entry["security_measures_summary"]
        assert entry["controller_role"]


def test_the_only_third_country_transfer_carries_a_safeguard(client):
    entries = client.get("/ropa").json()
    transfers = [e for e in entries if e["transfers_outside_eea"]]
    assert [e["ropa_ref"] for e in transfers] == ["ROPA-003"]
    assert transfers[0]["transfer_safeguard"] == "STANDARD_CONTRACTUAL_CLAUSES"
    assert "India" in transfers[0]["transfer_detail"]
    # Activities with no transfer must carry no safeguard.
    for entry in entries:
        if not entry["transfers_outside_eea"]:
            assert entry["transfer_safeguard"] == "NOT_APPLICABLE"


def test_legitimate_interests_activities_carry_a_balancing_test(client):
    for entry in client.get("/ropa").json():
        if entry["lawful_basis"] == "LEGITIMATE_INTERESTS":
            assert len(entry["legitimate_interests_assessment"].split()) >= 30


def test_a_ropa_entry_flags_a_security_measure_that_is_not_working(client):
    """ROPA-003 lists DP-005, which TEST-008 rated INEFFECTIVE."""
    entry = client.get("/ropa/ROPA-003").json()
    dp005 = next(c for c in entry["controls"] if c["control_id"] == "DP-005")
    assert dp005["operating_effectiveness"] == "INEFFECTIVE"
    assert dp005["credited"] is False


def test_ropa_entries_link_assets_and_risks(client):
    entry = client.get("/ropa/ROPA-003").json()
    assert {a["asset_ref"] for a in entry["assets"]} == {"AST-001", "AST-008"}
    assert {r["risk_ref"] for r in entry["risks"]} == {"RISK-008", "RISK-018"}
    assert entry["dpia_refs"] == ["DPIA-001"]


# --- Articles 35 and 36 -------------------------------------------------------------


def test_two_dpias_both_with_the_dpo_consulted(client):
    dpias = client.get("/dpias").json()
    assert len(dpias) == 2
    assert all(d["dpo_consulted"] for d in dpias)


def test_the_high_residual_dpia_routes_to_the_supervisory_authority(client):
    """Article 36(1): the controller cannot decide alone at high residual risk."""
    dpia = client.get("/dpias/DPIA-001").json()
    assert dpia["residual_risk"] == "HIGH"
    assert dpia["outcome"] == "CONSULT_SUPERVISORY_AUTHORITY"
    assert dpia["supervisory_authority_consulted"] is False
    # The rating was raised because a mitigating control failed its test.
    assert "TEST-008" in dpia["residual_risk_note"]


def test_the_stale_dpia_is_flagged(client):
    dpia = client.get("/dpias/DPIA-001").json()
    assert dpia["review_overdue"] is True
    fresh = client.get("/dpias/DPIA-002").json()
    assert fresh["review_overdue"] is False


def test_privacy_overview(client):
    overview = client.get("/privacy/overview").json()
    assert overview["ropa_entries"] == 6
    assert overview["activities_with_transfers"] == 1
    assert overview["activities_on_legitimate_interests"] == 2
    assert overview["dpias"] == 2
    assert overview["dpias_high_residual"] == 1
    assert overview["dpias_review_overdue"] == 1
    assert overview["dpias_awaiting_supervisory_consultation"] == 1
    assert overview["assets_holding_personal_data"] == 11


# --- Business impact analysis ---------------------------------------------------------


def test_five_processes_with_recovery_targets_inside_tolerance(client):
    processes = client.get("/bia").json()
    assert len(processes) == 5
    for bia in processes:
        assert bia["rto_hours"] <= bia["mtpd_hours"], bia["bia_ref"]
        assert bia["rpo_hours"] <= bia["mtpd_hours"], bia["bia_ref"]
        assert bia["recovery_headroom_hours"] == round(
            bia["mtpd_hours"] - bia["rto_hours"], 2
        )


def test_the_revenue_process_has_the_tightest_objectives(client):
    bia = next(b for b in client.get("/bia").json() if b["bia_ref"] == "BIA-001")
    assert bia["rto_hours"] == 2.0
    assert bia["rpo_hours"] == 0.25
    assert bia["mtpd_hours"] == 4.0
    assert bia["impact_1h"] > 0
    # The BIA earns its keep by naming the scenario its RTO does not cover.
    assert "EXC-002" in bia["recovery_note"]


def test_bia_links_reach_assets_controls_and_continuity_risks(client):
    bia = next(b for b in client.get("/bia").json() if b["bia_ref"] == "BIA-001")
    assert {a["asset_ref"] for a in bia["assets"]} >= {"AST-001", "AST-006"}
    assert {c["control_id"] for c in bia["controls"]} >= {"OP-005", "OP-006"}
    assert {r["risk_ref"] for r in bia["risks"]} >= {"RISK-007", "RISK-017"}


def test_every_process_records_a_workaround_or_says_there_is_none(client):
    for bia in client.get("/bia").json():
        assert len(bia["workaround"].split()) >= 10, bia["bia_ref"]
