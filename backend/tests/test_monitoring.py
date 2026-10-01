BASE = "/monitoring/plans/KRI-001"
PLAN = {
    "method": "Count coverage against the complete control population.",
    "population": "In-scope controls",
    "source": "Control library export",
    "collection_owner": "ISMS Manager",
    "evaluation_owner": "Head of Engineering",
    "frequency": "MONTHLY",
    "next_collection": "2026-10-01",
    "expected_revision": 1,
}
OBS = {
    "expected_revision": 2,
    "period_start": "2026-08-01",
    "period_end": "2026-08-31",
    "value": 0,
    "source_query": "Count rows by testing state with the frozen source export.",
    "population": "All in-scope controls",
    "evidence_ref": "EV-002",
}


def test_observations_retain_definition_and_reject_duplicate_period(client):
    assert client.put(BASE, json=PLAN).status_code == 200
    result = client.post(BASE + "/observations", json=OBS)
    assert result.status_code == 201, result.text
    frozen = result.json()["definition_snapshot"]
    assert client.post(BASE + "/observations", json=OBS).status_code == 409
    assert (
        client.put(
            BASE, json={**PLAN, "expected_revision": 2, "population": "Revised population"}
        ).status_code
        == 200
    )
    assert client.get("/monitoring/observations").json()[0]["definition_snapshot"] == frozen


def test_red_observation_needs_owned_follow_up(client):
    client.put(BASE, json=PLAN)
    row = client.post(BASE + "/observations", json=OBS).json()
    assert row["band"] == "RED"
    path = f"/monitoring/observations/{row['id']}/evaluate"
    assert (
        client.post(
            path, json={"evaluated_on": "2026-09-01", "note": "Investigate coverage shortfall."}
        ).status_code
        == 422
    )
    assert (
        client.post(
            path,
            json={
                "evaluated_on": "2026-09-01",
                "note": "Investigate coverage shortfall.",
                "remediation_ref": "REM-017",
            },
        ).status_code
        == 200
    )


def test_seed_does_not_backfill_observations_and_null_is_not_zero(client):
    assert client.get("/monitoring/observations").json() == []
    assert (
        client.post(BASE + "/observations", json={**OBS, "expected_revision": 1}).status_code == 422
    )
    client.put(BASE, json=PLAN)
    assert (
        client.post(BASE + "/observations", json={**OBS, "value": None}).json()["band"] == "NO_DATA"
    )


def test_residual_write_retains_assessment_provenance(client):
    response = client.patch(
        "/risks/RISK-004/residual",
        json={
            "residual_likelihood": 3,
            "residual_impact": 5,
            "residual_justification": "MFA exceptions remain; reviewed evidence supports the existing independently assessed score.",
        },
    )
    assert response.status_code == 200, response.text
    rows = client.get("/monitoring/risks/RISK-004/history").json()
    assert len(rows) == 1 and rows[0]["actor"] == "isms.manager"
    assert rows[0]["snapshot"]["control_links"]
