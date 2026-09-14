"""The application's own audit trail.

Every write endpoint leaves an event naming the actor and the values before and after;
a refused write leaves nothing; the read-only auditor can read the trail but, like every
other register, cannot touch it.
"""

from tests.test_registers_api import VALID_EXCEPTION
from tests.test_testing_api import BASE_TEST


def _events(client, **params):
    response = client.get("/audit-events", params=params)
    assert response.status_code == 200
    return response.json()


def test_the_trail_starts_empty_and_seeding_is_not_a_user_action(client):
    assert _events(client) == []


def test_lowering_a_residual_records_who_and_from_what(client):
    response = client.patch(
        "/risks/RISK-004/residual",
        json={
            "residual_likelihood": 2,
            "residual_impact": 5,
            "residual_justification": "Privileged MFA enrolment reached 100% on 2026-09-01; "
            "AC-002 re-tested clean.",
        },
    )
    assert response.status_code == 200

    (event,) = _events(client, record_ref="RISK-004")
    assert event["actor_username"] == "isms.manager"
    assert event["actor_role"] == "ISMS_MANAGER"
    assert event["action"] == "RESIDUAL_RESCORED"
    assert event["record_type"] == "RISK"
    assert event["before"]["residual_likelihood"] == 3
    assert event["before"]["residual_band"] == "HIGH"
    assert event["after"]["residual_likelihood"] == 2
    # 2 x 5 = 10 is still HIGH on this matrix. Halving the likelihood did not change
    # the band, which is the kind of thing the trail exists to make visible.
    assert event["after"]["residual_band"] == "HIGH"
    # Impact did not move, and the trail shows that too.
    assert event["before"]["residual_impact"] == event["after"]["residual_impact"] == 5
    assert event["summary"] == "Residual re-scored from 3 x 5 (15, HIGH) to 2 x 5 (10, HIGH)."
    assert event["occurred_at"]


def test_revising_only_the_justification_says_so(client):
    risk = client.get("/risks/RISK-004").json()
    response = client.patch(
        "/risks/RISK-004/residual",
        json={
            "residual_likelihood": risk["residual"]["likelihood"],
            "residual_impact": risk["residual"]["impact"],
            "residual_justification": risk["residual_justification"] + " Re-affirmed.",
        },
    )
    assert response.status_code == 200
    (event,) = _events(client, record_ref="RISK-004")
    assert event["summary"] == "Residual justification revised; score unchanged at 3 x 5 (15, HIGH)."

    # And the same values again is not an event.
    response = client.patch(
        "/risks/RISK-004/residual",
        json={
            "residual_likelihood": risk["residual"]["likelihood"],
            "residual_impact": risk["residual"]["impact"],
            "residual_justification": risk["residual_justification"] + " Re-affirmed.",
        },
    )
    assert response.status_code == 200
    assert len(_events(client, record_ref="RISK-004")) == 1


def test_a_refused_write_leaves_no_event(client):
    """A 422 rolls the change back, and the event with it."""
    response = client.patch("/soa/A.8.13", json={"justification_inclusion": "Required by ISO 27001."})
    assert response.status_code == 422
    assert _events(client, record_ref="A.8.13") == []

    response = client.patch(
        "/risks/RISK-019/residual",
        json={"residual_likelihood": 1, "residual_impact": 1, "residual_justification": "x"},
    )
    assert response.status_code == 422
    assert _events(client, record_ref="RISK-019") == []


def test_an_soa_edit_names_the_fields_that_changed(client):
    entry = client.get("/soa/A.8.13").json()
    response = client.patch(
        "/soa/A.8.13",
        json={"implementation_description": entry["implementation_description"] + " Re-verified."},
    )
    assert response.status_code == 200
    (event,) = _events(client, record_ref="A.8.13")
    assert event["action"] == "SOA_ENTRY_UPDATED"
    assert event["summary"] == "SoA entry updated: implementation_description."
    assert event["before"]["applicable"] == event["after"]["applicable"]


def test_resubmitting_the_same_values_is_not_an_event(client):
    entry = client.get("/soa/A.8.13").json()
    response = client.patch("/soa/A.8.13", json={"owner": entry["owner"]})
    assert response.status_code == 200
    assert _events(client, record_ref="A.8.13") == []


def test_a_workpaper_with_exceptions_records_the_cascade(client):
    payload = {
        **BASE_TEST,
        "exceptions_count": 2,
        "conclusion": "PASS_WITH_EXCEPTIONS",
        "exception_details": "Two repositories had a departed contractor as collaborator.",
    }
    response = client.post("/control-tests", json=payload)
    assert response.status_code == 201
    test_ref = response.json()["test_ref"]
    finding_ref = response.json()["linked_finding_ref"]

    (event,) = _events(client, record_ref=test_ref)
    assert event["action"] == "CONTROL_TEST_RECORDED"
    assert event["before"] is None
    assert event["after"]["control_id"] == "AC-006"
    assert event["after"]["finding_ref"] == finding_ref
    assert event["after"]["remediation_ref"].startswith("REM-")
    assert finding_ref in event["summary"]

    # The control's rating moved as a consequence, and that is its own event, pointing
    # back at the test that caused it.
    (rating,) = _events(client, record_type="CONTROL", record_ref="AC-006")
    assert rating["action"] == "CONTROL_EFFECTIVENESS_UPDATED"
    assert rating["after"]["operating_effectiveness"] == "EFFECTIVE_WITH_EXCEPTIONS"
    assert rating["after"]["last_tested"] == "2026-08-10"
    assert test_ref in rating["summary"]


def test_recording_an_acceptance_is_an_event(client):
    response = client.post("/risk-exceptions", json=VALID_EXCEPTION)
    assert response.status_code == 201
    ref = response.json()["exception_ref"]
    (event,) = _events(client, record_ref=ref)
    assert event["action"] == "RISK_EXCEPTION_RECORDED"
    assert event["after"]["risk_ref"] == "RISK-005"
    assert event["after"]["expiry_date"] == "2026-12-31"
    assert event["after"]["approver_role"] == "Chief Technology Officer"


def test_events_list_most_recent_first_and_filter_by_actor(client):
    client.patch(
        "/risks/RISK-004/residual",
        json={"residual_likelihood": 2, "residual_impact": 5, "residual_justification": "First."},
    )
    client.patch(
        "/risks/RISK-004/residual",
        json={"residual_likelihood": 3, "residual_impact": 5, "residual_justification": "Back."},
    )
    events = _events(client, actor="isms.manager")
    assert [e["after"]["residual_likelihood"] for e in events] == [3, 2]
    assert _events(client, actor="nobody") == []


def test_the_auditor_can_read_the_trail_and_cannot_write_to_it(auditor_client):
    assert auditor_client.get("/audit-events").status_code == 200
    # There is no write endpoint at all. A POST to the collection is refused by the
    # router-level rule before FastAPI can say 405; a DELETE on an id has no route.
    assert auditor_client.post("/audit-events", json={}).status_code in (403, 405)
    assert auditor_client.delete("/audit-events/1").status_code in (403, 404, 405)


def test_no_endpoint_can_edit_or_remove_an_event(client):
    from app.main import app

    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/audit-events"):
            assert getattr(route, "methods", set()) <= {"GET", "HEAD"}, path
