BASE = "/people/requirements/COMP-TEST"
REQUIREMENT = {
    "role": "Risk owner",
    "requirement": "Assess and explain an independently scored residual risk.",
    "evaluation_method": "Observed case exercise and questioning",
    "owner": "ISMS Manager",
    "review_date": "2026-12-01",
}
EVALUATION = {
    "expected_revision": 1,
    "subject_ref": "ROLE-HOLDER-01",
    "evaluated_on": "2026-09-01",
    "review_date": "2026-12-01",
    "result": "COMPETENT",
    "evidence_ref": "EV-002",
    "demonstrated_outcome": "Explained and defended the case assessment.",
}


def test_personnel_evaluations_are_private_and_preserve_requirement(client, auditor_client):
    assert client.put(BASE, json=REQUIREMENT).status_code == 200
    result = client.post(BASE + "/evaluations", json=EVALUATION)
    assert result.status_code == 201, result.text
    assert auditor_client.get(BASE + "/evaluations").status_code == 403
    assert (
        client.put(
            BASE,
            json={
                **REQUIREMENT,
                "expected_revision": 1,
                "requirement": "Additional skill required.",
            },
        ).status_code
        == 200
    )
    assert (
        client.get(BASE + "/evaluations").json()[0]["requirement_snapshot"]
        == result.json()["requirement_snapshot"]
    )
    assert client.post(BASE + "/evaluations", json=EVALUATION).status_code == 422


def test_evaluation_refuses_hints_missing_development_and_bad_dates(client):
    client.put(BASE, json=REQUIREMENT)
    for change in (
        {"demonstrated_outcome": "TODO AUTHOR:BENNY - evaluate"},
        {"result": "DEVELOPMENT_REQUIRED"},
        {"review_date": "2026-08-01"},
        {"evidence_ref": "MISSING"},
    ):
        assert client.post(BASE + "/evaluations", json={**EVALUATION, **change}).status_code == 422
    assert (
        client.post(
            BASE + "/evaluations",
            json={
                **EVALUATION,
                "result": "DEVELOPMENT_REQUIRED",
                "development_action": "Repeat observed exercise with coaching.",
                "action_due": "2026-10-01",
            },
        ).status_code
        == 201
    )


def test_communication_requires_published_revision_and_delivery_evidence(client, auditor_client):
    path = "/people/communications/COM-TEST"
    plan = {
        "topic": "Response responsibilities",
        "audience": "Response team",
        "owner": "ISMS Manager",
        "method": "Briefing",
        "planned_on": "2026-09-01",
    }
    assert client.put(path, json={**plan, "document_revision_id": 999}).status_code == 422
    assert client.put(path, json=plan).status_code == 200
    complete = {
        "completed_on": "2026-09-02",
        "evidence_ref": "EV-002",
        "note": "Briefing delivered and questions recorded.",
    }
    assert auditor_client.post(path + "/deliver", json=complete).status_code == 403
    assert (
        client.post(path + "/deliver", json={**complete, "evidence_ref": "MISSING"}).status_code
        == 422
    )
    assert client.post(path + "/deliver", json=complete).status_code == 200
    assert client.post(path + "/deliver", json=complete).status_code == 422


def test_seed_has_no_invented_personnel_assessments(client):
    assert "TODO AUTHOR:BENNY" in client.get("/people/requirements").json()[0]["requirement"]
    assert client.get("/people/requirements/COMP-001/evaluations").json() == []
