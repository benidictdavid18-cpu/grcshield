from app.schemas.operations import BiaIn, DpiaIn, RopaIn

BASE = "/operations"
APPROVE = {
    "completed_on": "2026-09-04",
    "evidence_ref": "EV-002",
    "note": "Reviewed the changed record and its supporting evidence.",
}


def proposal(client, kind, ref, content, revision=0):
    return client.post(
        BASE + "/revisions",
        json={
            "kind": kind,
            "record_ref": ref,
            "content": content,
            "expected_revision": revision,
            "owner": "ISMS Manager",
            "review_date": "2026-12-01",
            "change_note": "Review this operational change.",
        },
    )


def existing(client, kind, schema):
    row = client.get(BASE + "/registers/" + kind).json()[0]
    return row, {key: value for key, value in row.items() if key in schema.model_fields}


def test_bia_review_preserves_prior_record_and_opens_risk_reassessment(client):
    row, content = existing(client, "BIA", BiaIn)
    before = client.get("/risks/RISK-004").json()
    result = proposal(
        client, "BIA", row["bia_ref"], {**content, "workaround": "Revised fallback procedure."}, 1
    )
    assert result.status_code == 201, result.text
    revision = result.json()
    assert client.get(BASE + "/registers/BIA").json()[0]["workaround"] == row["workaround"]
    response = client.post(f"{BASE}/revisions/{revision['id']}/review", json=APPROVE)
    assert response.status_code == 200, response.text
    assert (
        client.get(BASE + "/registers/BIA").json()[0]["workaround"] == "Revised fallback procedure."
    )
    assert response.json()["previous"]["workaround"] == row["workaround"]
    assert client.get(BASE + "/reassessments").json()
    assert client.get("/risks/RISK-004").json() == before


def test_existing_bia_ropa_and_dpia_rules_still_reject_invalid_proposals(client):
    row, data = existing(client, "BIA", BiaIn)
    assert (
        proposal(
            client, "BIA", row["bia_ref"], {**data, "rto_hours": data["mtpd_hours"] + 1}, 1
        ).status_code
        == 422
    )
    row, data = existing(client, "ROPA", RopaIn)
    assert (
        proposal(
            client,
            "ROPA",
            row["ropa_ref"],
            {**data, "transfers_outside_eea": True, "transfer_safeguard": "NOT_APPLICABLE"},
        ).status_code
        == 422
    )
    row, data = existing(client, "DPIA", DpiaIn)
    assert (
        proposal(
            client,
            "DPIA",
            row["dpia_ref"],
            {
                **data,
                "residual_risk": "HIGH",
                "outcome": "PROCEED",
                "supervisory_authority_consulted": False,
            },
        ).status_code
        == 422
    )


def test_competing_proposal_cannot_overwrite_reviewed_record(client):
    row, data = existing(client, "BIA", BiaIn)
    first = proposal(
        client, "BIA", row["bia_ref"], {**data, "workaround": "First change."}, 1
    ).json()
    second = proposal(
        client, "BIA", row["bia_ref"], {**data, "workaround": "Second change."}, 2
    ).json()
    assert client.post(f"{BASE}/revisions/{first['id']}/review", json=APPROVE).status_code == 200
    assert client.post(f"{BASE}/revisions/{second['id']}/review", json=APPROVE).status_code == 422


def test_exercise_retains_measured_failure_against_targets(client):
    row = client.get(BASE + "/registers/BIA").json()[0]
    response = client.post(
        BASE + "/exercises/EXER-TEST",
        json={
            "bia_ref": row["bia_ref"],
            "performed_on": "2026-09-01",
            "recovery_hours": row["rto_hours"] + 1,
            "data_loss_hours": 0,
            "evidence_ref": "EV-002",
            "note": "Measured restore during the exercise.",
            "follow_up": "Owner to review the recovery procedure.",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["target_snapshot"]["targets_met"] is False


def test_coverage_refuses_unknown_records_and_unwritten_claims(client):
    payload = {
        "control_ref": "AC-002",
        "evidence_ref": "EV-002",
        "source_system": "Identity provider",
        "owner": "ISMS Manager",
        "period_start": "2026-08-01",
        "period_end": "2026-08-31",
        "review_date": "2026-12-01",
        "coverage_note": "Full privileged account population.",
    }
    assert (
        client.post(BASE + "/coverage", json={**payload, "evidence_ref": "MISSING"}).status_code
        == 422
    )
    assert (
        client.post(
            BASE + "/coverage", json={**payload, "coverage_note": "TODO AUTHOR:BENNY - confirm"}
        ).status_code
        == 422
    )
    assert client.post(BASE + "/coverage", json=payload).status_code == 201
