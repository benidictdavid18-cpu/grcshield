"""API tests for the Statement of Applicability, its overview and the PDF report."""

EXCLUDED_REFS = {
    "A.7.1", "A.7.2", "A.7.3", "A.7.4", "A.7.5", "A.7.6", "A.7.11", "A.7.12", "A.8.30",
}
# The eight written last: the ones whose driver was a judgment call rather than an
# obvious single risk.
AUTHORED_REFS = {
    "A.5.7", "A.5.15", "A.5.23", "A.6.3", "A.8.5", "A.8.12", "A.8.16", "A.8.28",
}


def test_every_annex_a_control_has_exactly_one_soa_entry(client):
    entries = client.get("/soa").json()
    assert len(entries) == 93
    refs = [e["control_ref"] for e in entries]
    assert len(set(refs)) == 93
    # Returned in Annex A order, so A.5.9 precedes A.5.10.
    assert refs[:11] == [f"A.5.{n}" for n in range(1, 12)]


def test_overview_counts_percent_over_applicable_controls_only(client):
    overview = client.get("/soa/overview").json()
    assert overview["total_controls"] == 93
    assert overview["applicable"] == 84
    assert overview["excluded"] == 9
    assert overview["implemented"] + overview["partially_implemented"] + overview[
        "not_implemented"
    ] == 84
    # Denominator is applicable controls (84), not all 93.
    expected = round(100 * overview["implemented"] / overview["applicable"], 1)
    assert overview["percent_implemented"] == expected
    assert overview["gaps"] == overview["partially_implemented"] + overview["not_implemented"]


def test_theme_counts_match_annex_a(client):
    overview = client.get("/soa/overview").json()
    totals = {t["theme"]: t["total"] for t in overview["themes"]}
    assert totals == {"A.5": 37, "A.6": 8, "A.7": 14, "A.8": 34}
    physical = next(t for t in overview["themes"] if t["theme"] == "A.7")
    assert physical["excluded"] == 8
    assert physical["applicable"] == 6


def test_exclusions_match_the_scope_decision_and_say_where_the_risk_went(client):
    excluded = client.get("/soa?applicable=false").json()
    assert {e["control_ref"] for e in excluded} == EXCLUDED_REFS
    for summary in excluded:
        entry = client.get(f"/soa/{summary['control_ref']}").json()
        assert entry["justification_exclusion"]
        assert entry["justification_inclusion"] is None
        # Excluded controls are forced to NOT_IMPLEMENTED.
        assert entry["implementation_status"] == "NOT_IMPLEMENTED"
        # "Where the risk went" -- a destination, not just an absence.
        text = entry["justification_exclusion"].lower()
        assert any(
            marker in text
            for marker in ("aws", "transferred", "retained", "addressed by", "managed through",
                           "a.6.7", "a.8.3", "a.8.16", "a.8.24", "a.8.14", "a.5.21")
        ), summary["control_ref"]


def test_no_soa_entry_fails_its_own_validation_rules(client):
    """Seed data must satisfy the same rules the write path enforces."""
    for summary in client.get("/soa").json():
        entry = client.get(f"/soa/{summary['control_ref']}").json()
        assert entry["validation_errors"] == [], summary["control_ref"]


def test_every_gap_carries_remediation_with_an_owner_and_a_due_date(client):
    gaps = client.get("/soa?gaps_only=true").json()
    # Twenty-nine, not twenty-eight: A.8.11 was downgraded from Implemented when Phase 4's
    # TEST-008 found unmasked customer data outside production.
    assert len(gaps) == 29
    for summary in gaps:
        entry = client.get(f"/soa/{summary['control_ref']}").json()
        live = [r for r in entry["remediation"] if r["status"] not in ("COMPLETED", "CANCELLED")]
        assert live, summary["control_ref"]
        for item in live:
            assert item["owner"].strip()
            assert item["due_date"]


def test_no_inclusion_justification_is_left_unwritten(client):
    outstanding = [e for e in client.get("/soa").json() if e["justification_outstanding"]]
    assert outstanding == []


def test_every_inclusion_justification_names_a_driver(client):
    """Clause 6.1.3 d) asks why a control is *necessary*.

    ``soa_validation`` already refuses a justification that names no driver at all. This
    goes further and checks the stronger property: that the driver named is one this
    database actually holds -- a risk reference that exists, or a stated legal,
    regulatory or contractual obligation -- rather than prose that merely reads well.
    """
    for summary in client.get("/soa").json():
        if not summary["applicable"]:
            continue
        entry = client.get(f"/soa/{summary['control_ref']}").json()
        text = entry["justification_inclusion"]
        assert text and "TODO AUTHOR:BENNY" not in text
        # A floor against a stub, not a quality bar. A.5.16 says what it needs to in
        # thirteen words and is better for it; length is not the property being tested.
        assert len(text.split()) >= 10, summary["control_ref"]

        linked = {risk["risk_ref"] for risk in entry["risks"]}
        names_a_linked_risk = any(risk_ref in text for risk_ref in linked)
        names_an_obligation = any(
            term in text.lower()
            for term in ("gdpr", "article", "contract", "regulat", "legal", "law", "pci")
        )
        assert names_a_linked_risk or names_an_obligation, summary["control_ref"]


def test_the_eight_authored_justifications_are_the_longest_form(client):
    """The eight that were written last are the ones an auditor is most likely to open,
    so they carry the fullest reasoning rather than a single sentence."""
    for ref in sorted(AUTHORED_REFS):
        entry = client.get(f"/soa/{ref}").json()
        assert len(entry["justification_inclusion"].split()) >= 60, ref


def test_a_8_5_carries_the_full_traceability_chain(client):
    """Risk -> control -> SoA -> evidence -> gap -> remediation -> residual."""
    entry = client.get("/soa/A.8.5").json()
    assert entry["control_title"] == "Secure authentication"
    assert entry["applicable"] is True
    assert entry["implementation_status"] == "PARTIALLY_IMPLEMENTED"
    assert entry["is_gap"] is True

    risk = next(r for r in entry["risks"] if r["risk_ref"] == "RISK-004")
    assert risk["residual_score"] == 15
    assert risk["exceeds_appetite"] is True

    assert [c["control_id"] for c in entry["controls"]] == ["AC-002"]
    assert "EV-002" in [e["evidence_ref"] for e in entry["evidence"]]
    assert "60%" in next(e for e in entry["evidence"] if e["evidence_ref"] == "EV-002")["description"]

    remediation = next(r for r in entry["remediation"] if r["remediation_ref"] == "REM-001")
    assert remediation["owner"] == "Head of Engineering"
    assert remediation["status"] == "IN_PROGRESS"

    # The test-result step of the chain resolves through the internal control.
    test = next(t for t in entry["tests"] if t["test_ref"] == "TEST-003")
    assert test["control_id"] == "AC-002"
    assert test["conclusion"] == "PASS_WITH_EXCEPTIONS"
    assert test["exceptions_count"] == 6
    assert test["finding_ref"] == "FIND-001"


def test_the_test_result_step_is_wired_to_real_workpapers(client):
    """Regression: this step of the chain was a hardcoded 'arrives in Phase 4' placeholder
    that was never connected once the workpapers existed."""
    # A control with tests surfaces them.
    assert len(client.get("/soa/A.8.5").json()["tests"]) >= 1
    # A control with none says so rather than claiming a future phase.
    assert client.get("/soa/A.5.5").json()["tests"] == []


def test_expired_evidence_is_surfaced(client):
    overview = client.get("/soa/overview").json()
    assert overview["expired_evidence"] == 3
    # A.7.1's exclusion rests on the AWS SOC 2 report, which has expired.
    entry = client.get("/soa/A.7.1").json()
    assert entry["has_expired_evidence"] is True
    assert any(e["expired"] for e in entry["evidence"])


def test_overdue_remediation_is_surfaced(client):
    overview = client.get("/soa/overview").json()
    assert overview["overdue_remediation"] == 2


def test_filters(client):
    assert len(client.get("/soa?theme=A.6").json()) == 8
    assert all(
        e["implementation_status"] == "NOT_IMPLEMENTED"
        for e in client.get("/soa?implementation_status=NOT_IMPLEMENTED").json()
    )
    assert [e["control_ref"] for e in client.get("/soa?q=secure+authentication").json()] == ["A.8.5"]


def test_unknown_control_returns_404(client):
    assert client.get("/soa/A.9.99").status_code == 404


# --- Write-path rules -------------------------------------------------------


def test_applicable_without_justification_is_rejected(client):
    response = client.patch("/soa/A.8.13", json={"justification_inclusion": "   "})
    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "justification_inclusion"


def test_circular_justification_is_rejected(client):
    response = client.patch(
        "/soa/A.8.13", json={"justification_inclusion": "Required by ISO 27001."}
    )
    assert response.status_code == 422
    assert "circular" in response.json()["detail"][0]["message"].lower()


def test_excluding_a_control_requires_an_exclusion_justification(client):
    response = client.patch("/soa/A.8.13", json={"applicable": False})
    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "justification_exclusion"


def test_excluded_control_cannot_be_implemented(client):
    response = client.patch(
        "/soa/A.8.13",
        json={
            "applicable": False,
            "justification_exclusion": "Transferred to AWS under shared responsibility.",
            "implementation_status": "IMPLEMENTED",
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "implementation_status"


def test_excluding_a_control_forces_not_implemented(client):
    """Flipping applicability without restating status should not be a trap."""
    response = client.patch(
        "/soa/A.8.13",
        json={
            "applicable": False,
            "justification_exclusion": "Backups are provided and assured by AWS under the "
            "shared responsibility model.",
        },
    )
    assert response.status_code == 200
    assert response.json()["implementation_status"] == "NOT_IMPLEMENTED"


def test_downgrading_an_implemented_control_without_remediation_is_rejected(client):
    """A.8.13 has no remediation linked, so it cannot become a gap."""
    response = client.patch("/soa/A.8.13", json={"implementation_status": "PARTIALLY_IMPLEMENTED"})
    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "linked_remediation_ids"


def test_a_valid_update_is_accepted(client):
    response = client.patch(
        "/soa/A.8.5",
        json={
            "justification_inclusion": "RISK-004 records privileged AWS compromise through "
            "incomplete MFA; this control is the primary preventive treatment.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["justification_outstanding"] is False
    assert body["validation_errors"] == []


def test_closing_a_gap_is_allowed(client):
    response = client.patch("/soa/A.8.2", json={"implementation_status": "IMPLEMENTED"})
    assert response.status_code == 200
    assert response.json()["is_gap"] is False


# --- Report -----------------------------------------------------------------


def test_soa_gap_report_renders_a_pdf(client):
    response = client.get("/soa/report.pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 10_000


def test_report_registry_exposes_the_soa_report_endpoint(client):
    reports = {r["code"]: r for r in client.get("/reports").json()}
    assert reports["SOA_GAP_ANALYSIS"]["implemented"] is True
    assert reports["SOA_GAP_ANALYSIS"]["endpoint"] == "/soa/report.pdf"
