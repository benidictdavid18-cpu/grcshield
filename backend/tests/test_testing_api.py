"""API tests for control testing workpapers, findings and the ISMS clause records."""

BASE_TEST = {
    "control_id": "AC-006",
    "tester": "Priya Raghavan, Security Engineer",
    "test_date": "2026-08-10",
    "period_covered_start": "2026-01-01",
    "period_covered_end": "2026-06-30",
    "test_objective": "Verify repository permissions are assigned by team.",
    "test_procedure": "Sampled repositories and inspected collaborator lists.",
    "population_description": "All 62 repositories in the organisation.",
    "population_size": 62,
    "sample_size": 20,
    "sample_selection_method": "RANDOM",
    "sampling_rationale": "Random selection across all repositories avoids bias toward "
    "actively developed ones.",
    "results_summary": "Twenty repositories inspected.",
    "exceptions_count": 0,
    "conclusion": "PASS",
    "reviewed_by": "Head of Legal & Compliance",
    "review_date": "2026-08-14",
}


def test_twelve_workpapers_with_a_mix_of_conclusions(client):
    tests = client.get("/control-tests").json()
    assert len(tests) == 12
    conclusions = {}
    for entry in tests:
        conclusions[entry["conclusion"]] = conclusions.get(entry["conclusion"], 0) + 1
    assert conclusions == {"PASS": 8, "PASS_WITH_EXCEPTIONS": 3, "FAIL": 1}


def test_every_non_clean_test_raises_a_finding(client):
    for entry in client.get("/control-tests").json():
        if entry["conclusion"] == "PASS":
            assert entry["linked_finding_ref"] is None, entry["test_ref"]
        else:
            assert entry["linked_finding_ref"], entry["test_ref"]


def test_every_finding_carries_remediation_with_an_owner_and_a_date(client):
    findings = client.get("/findings").json()
    assert len(findings) == 4
    for finding in findings:
        assert finding["remediation"], finding["finding_ref"]
        for item in finding["remediation"]:
            assert item["owner"].strip()
            assert item["due_date"]


def test_four_sampling_rationales_are_left_for_the_author(client):
    outstanding = [t for t in client.get("/control-tests").json() if t["rationale_outstanding"]]
    assert {t["test_ref"] for t in outstanding} == {
        "TEST-003", "TEST-005", "TEST-008", "TEST-011",
    }


def test_every_written_rationale_is_substantive(client):
    for summary in client.get("/control-tests").json():
        if summary["rationale_outstanding"]:
            continue
        detail = client.get(f"/control-tests/{summary['test_ref']}").json()
        assert len(detail["sampling_rationale"].split()) >= 20, summary["test_ref"]


def test_no_workpaper_is_reviewed_by_its_own_tester(client):
    for summary in client.get("/control-tests").json():
        detail = client.get(f"/control-tests/{summary['test_ref']}").json()
        if detail["reviewed_by"]:
            assert detail["reviewed_by"].lower() != detail["tester"].lower()


def test_the_risk_004_workpaper_shows_sixty_percent_coverage(client):
    detail = client.get("/control-tests/TEST-003").json()
    assert detail["control_id"] == "AC-002"
    assert detail["population_size"] == 15
    assert detail["sample_size"] == 15
    assert detail["sample_selection_method"] == "FULL_POPULATION"
    assert detail["exceptions_count"] == 6
    assert detail["exception_rate"] == 0.4
    assert detail["conclusion"] == "PASS_WITH_EXCEPTIONS"
    assert detail["linked_finding_ref"] == "FIND-001"
    assert "EV-002" in [e["evidence_ref"] for e in detail["evidence"]]


def test_the_design_deficiency_is_visible(client):
    controls = {c["control_id"]: c for c in client.get("/internal-controls").json()}
    assert controls["DP-005"]["design_effectiveness"] == "DEFICIENT"
    assert controls["DP-005"]["operating_effectiveness"] == "INEFFECTIVE"
    # A control that failed its test supports no credited basis.
    assert controls["DP-005"]["strongest_supported_basis"] == "TESTED_INEFFECTIVE"


def test_untested_controls_support_design_only_when_the_design_was_assessed(client):
    controls = {c["control_id"]: c for c in client.get("/internal-controls").json()}
    assert controls["BC-001"]["operating_effectiveness"] == "NOT_TESTED"
    assert controls["BC-001"]["design_effectiveness"] == "EFFECTIVE"
    assert controls["BC-001"]["strongest_supported_basis"] == "DESIGN_ONLY"


def test_overview_surfaces_optimistic_risk_links(client):
    overview = client.get("/control-tests/overview").json()
    assert overview["total_tests"] == 12
    assert overview["controls_design_deficient"] == 1
    assert overview["rationales_outstanding"] == 4
    assert overview["open_findings"] == 4
    assert overview["tests_unreviewed"] == 0
    # AC-002 passed for the workforce and failed for privileged accounts, so two risks
    # legitimately record a stronger basis than the control-level rollup.
    assert overview["optimistic_risk_links"] == ["RISK-001/AC-002", "RISK-015/AC-002"]


# --- Write path: the design/operating rule ------------------------------------


def test_operating_cannot_be_effective_when_design_is_deficient(client):
    response = client.patch(
        "/internal-controls/DP-005/effectiveness", json={"operating_effectiveness": "EFFECTIVE"}
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "operating_effectiveness"


def test_a_deficient_design_still_permits_operating_with_exceptions(client):
    response = client.patch(
        "/internal-controls/DP-005/effectiveness",
        json={"operating_effectiveness": "EFFECTIVE_WITH_EXCEPTIONS"},
    )
    assert response.status_code == 200
    assert response.json()["operating_effectiveness"] == "EFFECTIVE_WITH_EXCEPTIONS"


def test_fixing_the_design_permits_full_effectiveness(client):
    response = client.patch(
        "/internal-controls/DP-005/effectiveness",
        json={"design_effectiveness": "EFFECTIVE", "operating_effectiveness": "EFFECTIVE"},
    )
    assert response.status_code == 200


# --- Write path: workpapers and the auto-created cascade -----------------------


def test_recording_a_clean_test_creates_no_finding(client):
    response = client.post("/control-tests", json=BASE_TEST)
    assert response.status_code == 201
    body = response.json()
    assert body["conclusion"] == "PASS"
    assert body["linked_finding_ref"] is None


def test_a_test_with_exceptions_auto_creates_a_draft_finding_and_remediation(client):
    before = len(client.get("/findings").json())
    response = client.post(
        "/control-tests",
        json={
            **BASE_TEST,
            "exceptions_count": 3,
            "exception_details": "Three repositories grant direct individual write access.",
            "conclusion": "PASS_WITH_EXCEPTIONS",
        },
    )
    assert response.status_code == 201
    finding_ref = response.json()["linked_finding_ref"]
    assert finding_ref

    findings = client.get("/findings").json()
    assert len(findings) == before + 1
    finding = client.get(f"/findings/{finding_ref}").json()
    # DRAFT deliberately: the system observed a fact, a human decides if it is a finding.
    assert finding["status"] == "DRAFT"
    assert finding["source"] == "CONTROL_TEST"
    assert finding["control_id"] == "AC-006"
    assert finding["source_test_ref"] == response.json()["test_ref"]
    assert len(finding["remediation"]) == 1
    assert finding["remediation"][0]["owner"]
    assert finding["remediation"][0]["due_date"]


def test_a_failing_test_re_rates_the_control(client):
    client.post(
        "/control-tests",
        json={
            **BASE_TEST,
            "exceptions_count": 12,
            "exception_details": "Most repositories bypass team assignment.",
            "conclusion": "FAIL",
        },
    )
    controls = {c["control_id"]: c for c in client.get("/internal-controls").json()}
    assert controls["AC-006"]["operating_effectiveness"] == "INEFFECTIVE"
    assert controls["AC-006"]["last_tested"] == "2026-08-10"


def test_a_workpaper_without_a_sampling_rationale_is_rejected(client):
    response = client.post("/control-tests", json={**BASE_TEST, "sampling_rationale": "  "})
    assert response.status_code == 422
    assert any(e["field"] == "sampling_rationale" for e in response.json()["detail"])


def test_a_sample_larger_than_its_population_is_rejected(client):
    response = client.post("/control-tests", json={**BASE_TEST, "sample_size": 500})
    assert response.status_code == 422
    assert any(e["field"] == "sample_size" for e in response.json()["detail"])


def test_exceptions_with_a_clean_pass_are_rejected(client):
    response = client.post(
        "/control-tests",
        json={**BASE_TEST, "exceptions_count": 2, "exception_details": "two", "conclusion": "PASS"},
    )
    assert response.status_code == 422
    assert any(e["field"] == "conclusion" for e in response.json()["detail"])


def test_self_review_is_rejected(client):
    response = client.post(
        "/control-tests", json={**BASE_TEST, "reviewed_by": BASE_TEST["tester"]}
    )
    assert response.status_code == 422
    assert any(e["field"] == "reviewed_by" for e in response.json()["detail"])


def test_unknown_control_and_test_return_404(client):
    assert client.get("/control-tests/TEST-999").status_code == 404
    assert client.post("/control-tests", json={**BASE_TEST, "control_id": "ZZ-999"}).status_code == 404


# --- ISMS clause records -------------------------------------------------------


def test_internal_audit_programme_records_independence(client):
    audits = client.get("/isms/audits").json()
    assert len(audits) == 3
    for audit in audits:
        assert len(audit["independence_note"].split()) >= 25, audit["audit_ref"]
    statuses = {a["audit_ref"]: a["status"] for a in audits}
    assert statuses == {"AUD-001": "COMPLETED", "AUD-002": "IN_PROGRESS", "AUD-003": "PLANNED"}


def test_management_reviews_cover_the_clause_9_3_2_inputs(client):
    reviews = client.get("/isms/management-reviews").json()
    assert len(reviews) == 2
    for review in reviews:
        inputs = review["inputs_considered"]
        for marker in ("(a)", "(b)", "(c)", "(d)", "(e)", "(f)"):
            assert marker in inputs, f"{review['review_ref']} missing input {marker}"
        assert review["decisions"]
        assert review["actions"]


def test_nonconformities_separate_correction_from_corrective_action(client):
    ncs = client.get("/isms/nonconformities").json()
    assert len(ncs) == 3
    for nc in ncs:
        assert nc["immediate_correction"]
    closed = [nc for nc in ncs if nc["status"] == "CLOSED"]
    assert closed, "expected at least one closed nonconformity"
    for nc in closed:
        # Clause 10.2 d): closure requires evidence the corrective action worked.
        assert nc["effectiveness_check_result"]
        assert nc["corrective_action"]
        assert nc["root_cause_analysis"]


def test_isms_records_export_renders_a_pdf(client):
    response = client.get("/isms/records.pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")


def test_the_records_export_is_not_one_of_the_three_reports(client):
    """The report set was cut to three on purpose; this is a records export."""
    reports = client.get("/reports").json()
    assert len(reports) == 3
    assert "/isms/records.pdf" not in {r["endpoint"] for r in reports}


# --- The cascade: testing changes what the risk register and SoA say ------------


def test_a_failed_test_propagates_to_the_risk_register_and_the_soa(client):
    """TEST-008 is the worked example of testing doing real work.

    It found unmasked customer data outside production, which rated DP-005 ineffective,
    which withdrew the reduction RISK-008 was claiming, which pushed RISK-008 above its
    Data Privacy ceiling — and downgraded A.8.11 from implemented to a gap.
    """
    test = client.get("/control-tests/TEST-008").json()
    assert test["conclusion"] == "FAIL"
    assert test["control_id"] == "DP-005"

    controls = {c["control_id"]: c for c in client.get("/internal-controls").json()}
    assert controls["DP-005"]["operating_effectiveness"] == "INEFFECTIVE"

    # The risk link no longer earns credit ...
    risk = client.get("/risks/RISK-008").json()
    dp005 = next(c for c in risk["controls"] if c["control_id"] == "DP-005")
    assert dp005["effectiveness_basis"] == "TESTED_INEFFECTIVE"
    assert dp005["credits_reduction"] is False
    assert risk["has_uncredited_controls"] is True

    # ... so the residual sits above the Data Privacy ceiling of Low.
    assert risk["residual"]["score"] == 8
    assert risk["appetite"]["max_acceptable_band"] == "LOW"
    assert risk["appetite"]["exceeds_appetite"] is True

    # ... and the SoA entry that rested on the control became a gap.
    entry = client.get("/soa/A.8.11").json()
    assert entry["implementation_status"] == "PARTIALLY_IMPLEMENTED"
    assert entry["is_gap"] is True
    assert "REM-017" in [r["remediation_ref"] for r in entry["remediation"]]
