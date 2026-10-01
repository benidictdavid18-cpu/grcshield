from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.core.config import get_settings
from app.models.ai import AiFeature, AiInteraction, AiInteractionStatus
from app.models.audit_trail import AuditEvent
from app.models.maintenance import RetentionState
from app.services import retention
from app.services.ai.limits import inference_limits
from app.services.ai.provider import AiUnavailable


def test_api_limits_repeated_calls_and_outage_releases_slot(
    client, ai_provider, ai_service, monkeypatch
):
    monkeypatch.setattr(get_settings(), "ai_request_limit", 1)
    ai_provider.raises = AiUnavailable("Provider unavailable; sensitive response fragment.")
    assert client.post("/ai/risk-assist", json={"risk_ref": "RISK-004"}).status_code == 503
    second = client.post("/ai/risk-assist", json={"risk_ref": "RISK-004"})
    assert second.status_code == 429 and "Retry-After" in second.headers
    assert inference_limits.active == 0
    rows = client.get("/ai/interactions").json()
    assert all("sensitive response" not in (row.get("error_note") or "") for row in rows)


def test_concurrency_limit_covers_different_users_and_releases_on_error(monkeypatch):
    monkeypatch.setattr(get_settings(), "ai_concurrency_limit", 1)
    with pytest.raises(RuntimeError), inference_limits.acquire("one", "test"):
        with pytest.raises(HTTPException) as error, inference_limits.acquire("two", "test"):
            pass
        assert error.value.status_code == 429
        raise RuntimeError("fixture")
    with inference_limits.acquire("two", "test"):
        assert inference_limits.active == 1


def test_retention_prunes_only_old_diagnostics_and_records_result(db_session):
    now = datetime.now(UTC)
    for ref, created in [("AI-OLD", now - timedelta(days=60)), ("AI-NEW", now)]:
        db_session.add(
            AiInteraction(
                interaction_ref=ref,
                username="fixture",
                user_role="AUDITOR",
                feature=AiFeature.RISK_ASSIST,
                provider="fixture",
                model="fixture",
                status=AiInteractionStatus.DISABLED,
                created_at=created,
            )
        )
    db_session.flush()
    before = db_session.scalar(select(func.count()).select_from(AuditEvent))
    assert retention.prune(db_session, now) == 1
    db_session.flush()
    assert db_session.scalar(select(AiInteraction).where(AiInteraction.interaction_ref == "AI-NEW"))
    assert db_session.scalar(select(func.count()).select_from(AuditEvent)) == before
    assert db_session.get(RetentionState, 1).deleted_count == 1


def test_manager_cannot_trigger_admin_pruning(client):
    assert client.post("/maintenance/prune-ai").status_code == 403
    assert client.get("/maintenance/policy").json()["ai_retention_days"] == 30
