"""API contract tests for the framework registry and control library."""

THEME_COUNTS = {"A.5": 37, "A.6": 8, "A.7": 14, "A.8": 34}


def test_health_reports_a_fully_seeded_catalogue(client):
    body = client.get("/health").json()
    assert body["annex_a_controls"] == 93
    assert body["seeded"] is True
    assert body["status"] == "ok"
    # Rule 1: the disclaimer travels with the data.
    assert "fictional" in body["disclaimer"].lower()


def test_four_frameworks_with_the_expected_scope_split(client):
    frameworks = {f["code"]: f for f in client.get("/frameworks").json()}
    assert set(frameworks) == {"ISO27001_2022", "SOC2_TSC", "NIST_CSF_2_0", "GDPR"}
    assert frameworks["ISO27001_2022"]["scope_status"] == "PRIMARY"
    assert frameworks["SOC2_TSC"]["scope_status"] == "SECONDARY"
    assert frameworks["NIST_CSF_2_0"]["scope_status"] == "ROADMAP"
    assert frameworks["GDPR"]["scope_status"] == "ROADMAP"


def test_roadmap_frameworks_carry_no_control_catalogue(client):
    """A progress bar against controls nobody has assessed reads as assurance."""
    frameworks = {f["code"]: f for f in client.get("/frameworks").json()}
    assert frameworks["NIST_CSF_2_0"]["control_count"] == 0
    assert frameworks["GDPR"]["control_count"] == 0
    assert len(frameworks["GDPR"]["scope_note"]) > 100


def test_annex_a_theme_counts(client):
    detail = client.get("/frameworks/ISO27001_2022").json()
    assert detail["control_count"] == 93
    counts = {g["group_ref"]: g["total"] for g in detail["groups"]}
    assert counts == THEME_COUNTS


def test_nine_provisional_exclusions_each_explaining_where_the_risk_went(client):
    excluded = client.get("/frameworks/ISO27001_2022/controls?in_scope=false").json()
    refs = {c["control_ref"] for c in excluded}
    assert refs == {
        "A.7.1", "A.7.2", "A.7.3", "A.7.4", "A.7.5", "A.7.6",
        "A.7.11", "A.7.12", "A.8.30",
    }
    for control in excluded:
        assert control["scope_note"], f"{control['control_ref']} excluded without a note"
        assert len(control["scope_note"].split()) >= 15


def test_remote_relevant_physical_controls_are_kept(client):
    """A remote workforce relocates physical risk; it does not delete it."""
    kept = {
        c["control_ref"]
        for c in client.get("/frameworks/ISO27001_2022/controls?group_ref=A.7&in_scope=true").json()
    }
    assert kept == {"A.7.7", "A.7.8", "A.7.9", "A.7.10", "A.7.13", "A.7.14"}


def test_control_detail_exposes_typed_soc2_mappings(client):
    body = client.get("/frameworks/ISO27001_2022/controls/A.8.5").json()
    assert body["title"] == "Secure authentication"
    assert body["in_scope"] is True
    mappings = {m["control_ref"]: m["relationship_type"] for m in body["mappings"]}
    assert mappings == {"CC6.1": "EQUIVALENT"}


def test_excluded_controls_have_no_soc2_mappings(client):
    """No evidence is produced for an excluded control, so it satisfies no criterion."""
    for ref in ("A.7.1", "A.8.30"):
        body = client.get(f"/frameworks/ISO27001_2022/controls/{ref}").json()
        assert body["in_scope"] is False
        assert body["mappings"] == []


def test_privacy_gap_is_left_visible(client):
    """A.5.34 maps nowhere because FinFlow does not elect the SOC 2 Privacy category."""
    body = client.get("/frameworks/ISO27001_2022/controls/A.5.34").json()
    assert body["in_scope"] is True
    assert body["mappings"] == []


def test_soc2_common_criteria_are_elected_and_privacy_is_not(client):
    controls = client.get("/frameworks/SOC2_TSC/controls").json()
    by_ref = {c["control_ref"]: c for c in controls}
    assert len([c for c in controls if c["group_ref"].startswith("CC")]) == 33
    assert by_ref["CC6.1"]["in_scope"] is True
    assert by_ref["A1.2"]["in_scope"] is True
    assert by_ref["C1.1"]["in_scope"] is True
    assert by_ref["PI1.1"]["in_scope"] is False
    assert by_ref["P1.1"]["in_scope"] is False


def test_control_search_filter(client):
    results = client.get("/frameworks/ISO27001_2022/controls?q=cryptography").json()
    assert [c["control_ref"] for c in results] == ["A.8.24"]


def test_unknown_framework_and_control_return_404(client):
    assert client.get("/frameworks/NOPE").status_code == 404
    assert client.get("/frameworks/ISO27001_2022/controls/A.9.99").status_code == 404


def test_report_set_is_exactly_three(client):
    reports = client.get("/reports").json()
    assert [r["code"] for r in reports] == [
        "RISK_REGISTER",
        "SOA_GAP_ANALYSIS",
        "EXECUTIVE_SUMMARY",
    ]
    for report in reports:
        assert report["audience"]
        assert report["decision_supported"]
