"""The AI interaction log.

Because this is a GRC platform, "an assistant helped write that" is itself a fact worth
recording. If a finding description was drafted with model assistance, an auditor asking
"who wrote this?" deserves an answer better than a shrug.

**What is deliberately not stored: the prompt and the response text.**

Every prompt this application builds is assembled from records that are already in this
database, under the access control those records already carry. Copying that content
into a second table would duplicate sensitive material into a place with weaker
handling, and would add no assurance that the originating record does not already give.

What is stored instead is the *shape* of the interaction — who, when, which feature,
which record, which model, what happened, how big — plus a truncated SHA-256 digest of
the response. The digest is the useful half: it lets a suggestion someone pasted into a
workpaper be tied back to the interaction that produced it, without the platform
retaining the text of either.
"""

import enum

from sqlalchemy import (
    CheckConstraint,
    Enum,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AiFeature(str, enum.Enum):
    """Which assistant was invoked. One value per endpoint, so the log answers
    "what is this being used for?" without parsing free text."""

    RISK_ASSIST = "RISK_ASSIST"
    RISK_DESCRIPTION = "RISK_DESCRIPTION"
    CONTROL_MAPPING = "CONTROL_MAPPING"
    CONTROL_TEST_ASSIST = "CONTROL_TEST_ASSIST"
    FINDING_DRAFT = "FINDING_DRAFT"
    REMEDIATION_ASSIST = "REMEDIATION_ASSIST"
    POLICY_DRAFT = "POLICY_DRAFT"
    CONSISTENCY_SWEEP = "CONSISTENCY_SWEEP"


class AiInteractionStatus(str, enum.Enum):
    """How the interaction ended.

    The failure states are enumerated rather than collapsed into "error" because they
    call for different responses: DISABLED is a configuration choice, PROVIDER_UNAVAILABLE
    is an operational problem, and INVALID_RESPONSE is a model problem.
    """

    OK = "OK"
    DISABLED = "DISABLED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    INVALID_RESPONSE = "INVALID_RESPONSE"


class AiInteraction(Base):
    __tablename__ = "ai_interactions"
    __table_args__ = (
        Index("ix_ai_interactions_feature", "feature"),
        Index("ix_ai_interactions_entity", "entity_ref"),
        CheckConstraint(
            "status <> 'OK' OR response_digest IS NOT NULL",
            name="ck_ai_interaction_ok_has_digest",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    interaction_ref: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)

    # Stored as text rather than a foreign key. An activity log has to stay readable
    # after the account it refers to is deactivated or removed; a SET NULL would erase
    # exactly the fact the log exists to record.
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    user_role: Mapped[str] = mapped_column(String(32), nullable=False)

    feature: Mapped[AiFeature] = mapped_column(Enum(AiFeature, name="ai_feature"), nullable=False)

    # The GRC record the request was about, by its business reference (RISK-004,
    # TEST-008) rather than a surrogate key, so the log is legible on its own.
    entity_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    entity_ref: Mapped[str | None] = mapped_column(String(32), nullable=True)

    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)

    status: Mapped[AiInteractionStatus] = mapped_column(
        Enum(AiInteractionStatus, name="ai_interaction_status"), nullable=False
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Sizes, not contents. Enough to spot a prompt that has grown unreasonable or a
    # model that has started returning nothing.
    prompt_chars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    response_chars: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # First 16 hex characters of the SHA-256 of the response body. Ties a suggestion
    # somebody kept back to the interaction that produced it, without storing the text.
    response_digest: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # Which output guardrails fired, comma separated. A response that claimed
    # certification, or invented a control identifier, leaves a trace here.
    guardrail_flags: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Why a failed interaction failed, in words. Never contains prompt content.
    error_note: Mapped[str | None] = mapped_column(Text, nullable=True)
