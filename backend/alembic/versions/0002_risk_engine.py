"""Internal control library, risk register, risk-control links and risk appetite.

Revision ID: 0002
Revises: 0001
Create Date: Phase 2
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

risk_category = sa.Enum(
    "CYBERSECURITY", "DATA_PRIVACY", "THIRD_PARTY", "OPERATIONAL", "FINANCIAL",
    "LEGAL", "COMPLIANCE", "BUSINESS_CONTINUITY", "TECHNOLOGY",
    name="risk_category",
)
risk_band = sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="risk_band")
risk_status = sa.Enum(
    "OPEN", "TREATMENT_IN_PROGRESS", "MONITORING", "CLOSED", name="risk_status"
)
treatment_decision = sa.Enum(
    "MITIGATE", "ACCEPT", "TRANSFER", "AVOID", name="treatment_decision"
)
control_effectiveness_basis = sa.Enum(
    "NOT_TESTED", "DESIGN_ONLY", "TESTED_EFFECTIVE", "TESTED_WITH_EXCEPTIONS",
    "TESTED_INEFFECTIVE",
    name="control_effectiveness_basis",
)

_ENUMS = (
    risk_category, risk_band, risk_status, treatment_decision, control_effectiveness_basis,
)

# Likelihood and impact are constrained in the database as well as the API. The 1-5
# scale is a property of the methodology, not of one write path.
_SCALE = "BETWEEN 1 AND 5"


def upgrade() -> None:
    bind = op.get_bind()
    for enum in _ENUMS:
        enum.create(bind, checkfirst=True)

    op.create_table(
        "controls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("control_id", sa.String(length=24), nullable=False, unique=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("control_family", sa.String(length=64), nullable=False),
        sa.Column("owner_role", sa.String(length=120), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "control_annex_a_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("control_id", sa.Integer(), sa.ForeignKey("controls.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "framework_control_id",
            sa.Integer(),
            sa.ForeignKey("framework_controls.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("control_id", "framework_control_id", name="uq_control_annex_a"),
    )

    op.create_table(
        "risk_appetite_thresholds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category", risk_category, nullable=False, unique=True),
        sa.Column("max_acceptable_band", risk_band, nullable=False),
        sa.Column("approver_role", sa.String(length=120), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("last_reviewed", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "risks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("risk_ref", sa.String(length=16), nullable=False, unique=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", risk_category, nullable=False),
        sa.Column("owner_role", sa.String(length=120), nullable=False),
        sa.Column("status", risk_status, nullable=False),
        sa.Column("asset", sa.String(length=240), nullable=False),
        sa.Column("threat", sa.Text(), nullable=False),
        sa.Column("vulnerability", sa.Text(), nullable=False),
        sa.Column("inherent_likelihood", sa.Integer(), nullable=False),
        sa.Column("inherent_impact", sa.Integer(), nullable=False),
        sa.Column("residual_likelihood", sa.Integer(), nullable=False),
        sa.Column("residual_impact", sa.Integer(), nullable=False),
        sa.Column("residual_justification", sa.Text(), nullable=False),
        sa.Column("treatment_decision", treatment_decision, nullable=False),
        sa.Column("treatment_summary", sa.Text(), nullable=False),
        sa.Column("date_identified", sa.Date(), nullable=False),
        sa.Column("last_reviewed", sa.Date(), nullable=True),
        sa.Column("next_review", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(f"inherent_likelihood {_SCALE}", name="ck_risks_inherent_likelihood"),
        sa.CheckConstraint(f"inherent_impact {_SCALE}", name="ck_risks_inherent_impact"),
        sa.CheckConstraint(f"residual_likelihood {_SCALE}", name="ck_risks_residual_likelihood"),
        sa.CheckConstraint(f"residual_impact {_SCALE}", name="ck_risks_residual_impact"),
        # A residual score without a written justification is the failure mode this
        # phase exists to remove, so the database refuses it too.
        sa.CheckConstraint(
            "length(trim(residual_justification)) > 0",
            name="ck_risks_residual_justification_present",
        ),
    )
    op.create_index("ix_risks_category", "risks", ["category"])

    op.create_table(
        "risk_controls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("risk_id", sa.Integer(), sa.ForeignKey("risks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("control_id", sa.Integer(), sa.ForeignKey("controls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("effectiveness_basis", control_effectiveness_basis, nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("risk_id", "control_id", name="uq_risk_control"),
    )
    op.create_index("ix_risk_controls_risk", "risk_controls", ["risk_id"])


def downgrade() -> None:
    op.drop_index("ix_risk_controls_risk", table_name="risk_controls")
    op.drop_table("risk_controls")
    op.drop_index("ix_risks_category", table_name="risks")
    op.drop_table("risks")
    op.drop_table("risk_appetite_thresholds")
    op.drop_table("control_annex_a_links")
    op.drop_table("controls")

    bind = op.get_bind()
    for enum in reversed(_ENUMS):
        enum.drop(bind, checkfirst=True)
