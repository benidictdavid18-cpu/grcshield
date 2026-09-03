"""AI interaction log.

One table. The AI layer is advisory and deliberately owns no GRC state: it does not add
a column to risks, controls, tests or findings, and it does not change a constraint on
any of them. The only thing it needs to persist is the record that an interaction
happened, which is what this table is.

Revision ID: 0007
Revises: 0006
Create Date: Ollama integration
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ai_feature = sa.Enum(
    "RISK_ASSIST",
    "RISK_DESCRIPTION",
    "CONTROL_MAPPING",
    "CONTROL_TEST_ASSIST",
    "FINDING_DRAFT",
    "REMEDIATION_ASSIST",
    "POLICY_DRAFT",
    name="ai_feature",
)
ai_interaction_status = sa.Enum(
    "OK",
    "DISABLED",
    "PROVIDER_UNAVAILABLE",
    "TIMEOUT",
    "INVALID_RESPONSE",
    name="ai_interaction_status",
)

_ENUMS = (ai_feature, ai_interaction_status)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    for enum in _ENUMS:
        enum.create(bind, checkfirst=True)

    op.create_table(
        "ai_interactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("interaction_ref", sa.String(24), nullable=False, unique=True),
        # Text, not a foreign key: an activity log must stay readable after the account
        # it names is deactivated, and a SET NULL would erase the fact being recorded.
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("user_role", sa.String(32), nullable=False),
        sa.Column("feature", ai_feature, nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=True),
        sa.Column("entity_ref", sa.String(32), nullable=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("status", ai_interaction_status, nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        # Sizes and a digest. Never the prompt or the response text -- both are derived
        # from records this database already holds under their own access control, and
        # a second copy in a less controlled table adds exposure, not assurance.
        sa.Column("prompt_chars", sa.Integer(), nullable=False),
        sa.Column("response_chars", sa.Integer(), nullable=True),
        sa.Column("response_digest", sa.String(16), nullable=True),
        sa.Column("guardrail_flags", sa.Text(), nullable=True),
        sa.Column("error_note", sa.Text(), nullable=True),
        *_timestamps(),
        # A successful interaction that cannot be tied back to its output is not much of
        # a log entry.
        sa.CheckConstraint(
            "status <> 'OK' OR response_digest IS NOT NULL",
            name="ck_ai_interaction_ok_has_digest",
        ),
    )
    op.create_index("ix_ai_interactions_feature", "ai_interactions", ["feature"])
    op.create_index("ix_ai_interactions_entity", "ai_interactions", ["entity_ref"])


def downgrade() -> None:
    op.drop_index("ix_ai_interactions_entity", table_name="ai_interactions")
    op.drop_index("ix_ai_interactions_feature", table_name="ai_interactions")
    op.drop_table("ai_interactions")

    bind = op.get_bind()
    for enum in reversed(_ENUMS):
        enum.drop(bind, checkfirst=True)
