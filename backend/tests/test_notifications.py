from datetime import date

from sqlalchemy import select

from app.models.notifications import Notification


def test_scan_deduplicates_and_keeps_unassigned_delivery_visible(client):
    first = client.post("/notifications/run")
    assert first.status_code == 200, first.text
    assert first.json()["created"] > 0
    assert client.post("/notifications/run").json()["created"] == 0
    rows = client.get("/notifications/outbox").json()
    assert all(row["status"] == "PENDING" and row["last_error"] for row in rows)
    assert client.get("/notifications").json() == []


def test_routing_delivers_only_to_owner_and_ack_does_not_close_source(client, auditor_client):
    client.post("/notifications/run")
    pending = client.get("/notifications/outbox").json()
    row = next(x for x in pending if "TODO AUTHOR:BENNY" not in x["owner"])
    assert (
        client.put(
            "/notifications/routing", json={"owner": row["owner"], "username": "isms.manager"}
        ).status_code
        == 200
    )
    assert client.post("/notifications/run").status_code == 200
    delivered = next(x for x in client.get("/notifications").json() if x["id"] == row["id"])
    assert delivered["status"] == "DELIVERED"
    assert auditor_client.post(f"/notifications/{row['id']}/acknowledge").status_code == 403
    before = client.get("/risks/RISK-004").json()
    assert client.post(f"/notifications/{row['id']}/acknowledge").status_code == 200
    assert client.get("/risks/RISK-004").json() == before


def test_overdue_unacknowledged_reminders_escalate(client, db_session):
    db_session.add(
        Notification(
            dedup_key="fixture-escalation",
            record_ref="RISK-004",
            kind="RISK_REVIEW",
            message="Review due",
            owner="Head of Engineering",
            due_date=date(2026, 1, 1),
        )
    )
    db_session.flush()
    client.post("/notifications/run")
    row = db_session.scalar(
        select(Notification).where(Notification.dedup_key == "fixture-escalation")
    )
    assert row.escalated_on is not None and row.last_error


def test_readonly_cannot_scan_or_change_delivery_routing(auditor_client):
    assert auditor_client.post("/notifications/run").status_code == 403
    assert (
        auditor_client.put(
            "/notifications/routing", json={"owner": "ISMS Manager", "username": "auditor"}
        ).status_code
        == 403
    )
