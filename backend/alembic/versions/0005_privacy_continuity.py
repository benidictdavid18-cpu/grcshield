"""Asset register, risk acceptance, GDPR records and business impact analysis.

Revision ID: 0005
Revises: 0004
Create Date: Phase 5
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.db.migration_types import pg_enum

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

asset_type = pg_enum(
    "SYSTEM", "DATA_STORE", "SAAS_SERVICE", "THIRD_PARTY_SERVICE", "DEVICE_FLEET", "PROCESS",
    name="asset_type",
)
asset_classification = pg_enum(
    "PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED", name="asset_classification"
)
exception_status = pg_enum(
    "PENDING", "APPROVED", "EXPIRED", "WITHDRAWN", "REJECTED", name="exception_status"
)
lawful_basis = pg_enum(
    "CONSENT", "CONTRACT", "LEGAL_OBLIGATION", "VITAL_INTERESTS", "PUBLIC_TASK",
    "LEGITIMATE_INTERESTS",
    name="lawful_basis",
)
transfer_safeguard = pg_enum(
    "NOT_APPLICABLE", "ADEQUACY_DECISION", "STANDARD_CONTRACTUAL_CLAUSES",
    "BINDING_CORPORATE_RULES", "DEROGATION",
    name="transfer_safeguard",
)
dpia_outcome = pg_enum(
    "PROCEED", "PROCEED_WITH_MEASURES", "CONSULT_SUPERVISORY_AUTHORITY", "DO_NOT_PROCEED",
    name="dpia_outcome",
)
dpia_residual_risk = pg_enum("LOW", "MEDIUM", "HIGH", name="dpia_residual_risk")

_ENUMS = (
    asset_type, asset_classification, exception_status, lawful_basis, transfer_safeguard,
    dpia_outcome, dpia_residual_risk,
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def _link_table(name: str, parent: str, parent_table: str, child: str, child_table: str, uq: str):
    op.create_table(
        name,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            parent, sa.Integer(), sa.ForeignKey(f"{parent_table}.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            child, sa.Integer(), sa.ForeignKey(f"{child_table}.id", ondelete="CASCADE"),
            nullable=False,
        ),
        *_timestamps(),
        sa.UniqueConstraint(parent, child, name=uq),
    )


def upgrade() -> None:
    bind = op.get_bind()
    for enum in _ENUMS:
        enum.create(bind, checkfirst=True)

    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_ref", sa.String(length=24), nullable=False, unique=True),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("asset_type", asset_type, nullable=False),
        sa.Column("classification", asset_classification, nullable=False),
        sa.Column("owner_role", sa.String(length=120), nullable=False),
        sa.Column("hosting_location", sa.String(length=160), nullable=False),
        sa.Column("holds_personal_data", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        *_timestamps(),
    )

    op.create_table(
        "risk_exceptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("exception_ref", sa.String(length=24), nullable=False, unique=True),
        sa.Column("risk_id", sa.Integer(), sa.ForeignKey("risks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_by", sa.String(length=120), nullable=False),
        sa.Column("business_justification", sa.Text(), nullable=False),
        sa.Column("compensating_controls", sa.Text(), nullable=False),
        sa.Column("approver_role", sa.String(length=120), nullable=False),
        sa.Column("approval_date", sa.Date(), nullable=True),
        # NOT NULL by design. An acceptance with no end date is a permanent decision
        # disguised as a temporary one.
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("review_trigger", sa.Text(), nullable=False),
        sa.Column("status", exception_status, nullable=False),
        sa.Column("decision_note", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "approval_date IS NULL OR expiry_date > approval_date",
            name="ck_exception_expiry_after_approval",
        ),
        sa.CheckConstraint(
            "length(trim(review_trigger)) > 0", name="ck_exception_review_trigger_present"
        ),
    )
    op.create_index("ix_risk_exceptions_expiry", "risk_exceptions", ["expiry_date"])

    op.create_table(
        "ropa_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ropa_ref", sa.String(length=24), nullable=False, unique=True),
        sa.Column("processing_activity", sa.String(length=240), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("lawful_basis", lawful_basis, nullable=False),
        sa.Column("legitimate_interests_assessment", sa.Text(), nullable=True),
        sa.Column("data_subject_categories", sa.Text(), nullable=False),
        sa.Column("personal_data_categories", sa.Text(), nullable=False),
        sa.Column("special_category_data", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("recipients", sa.Text(), nullable=False),
        sa.Column("transfers_outside_eea", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("transfer_detail", sa.Text(), nullable=True),
        sa.Column("transfer_safeguard", transfer_safeguard, nullable=False),
        sa.Column("retention_period", sa.Text(), nullable=False),
        sa.Column("security_measures_summary", sa.Text(), nullable=False),
        sa.Column("controller_role", sa.String(length=120), nullable=False),
        sa.Column("owner_role", sa.String(length=120), nullable=False),
        sa.Column("last_reviewed", sa.Date(), nullable=True),
        *_timestamps(),
        # Chapter V: a transfer outside the EEA requires a safeguard, and a safeguard
        # without a transfer means one of the two fields is wrong.
        sa.CheckConstraint(
            "(transfers_outside_eea AND transfer_safeguard <> 'NOT_APPLICABLE') "
            "OR (NOT transfers_outside_eea AND transfer_safeguard = 'NOT_APPLICABLE')",
            name="ck_ropa_transfer_safeguard_matches",
        ),
        # Article 30(1)(f): envisaged time limits for erasure.
        sa.CheckConstraint(
            "length(trim(retention_period)) > 0", name="ck_ropa_retention_present"
        ),
    )

    op.create_table(
        "dpias",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dpia_ref", sa.String(length=24), nullable=False, unique=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column(
            "ropa_id", sa.Integer(), sa.ForeignKey("ropa_entries.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("trigger_reason", sa.Text(), nullable=False),
        sa.Column("processing_description", sa.Text(), nullable=False),
        sa.Column("necessity_and_proportionality", sa.Text(), nullable=False),
        sa.Column("risks_to_data_subjects", sa.Text(), nullable=False),
        sa.Column("mitigating_measures", sa.Text(), nullable=False),
        sa.Column("residual_risk", dpia_residual_risk, nullable=False),
        sa.Column("residual_risk_note", sa.Text(), nullable=False),
        sa.Column("dpo_consulted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("dpo_advice", sa.Text(), nullable=True),
        sa.Column(
            "supervisory_authority_consulted", sa.Boolean(), nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "data_subjects_consulted", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("outcome", dpia_outcome, nullable=False),
        sa.Column("assessed_by", sa.String(length=120), nullable=False),
        sa.Column("assessment_date", sa.Date(), nullable=False),
        sa.Column("review_date", sa.Date(), nullable=True),
        *_timestamps(),
        # Article 36(1): high residual risk cannot simply be proceeded with.
        sa.CheckConstraint(
            "residual_risk <> 'HIGH' "
            "OR outcome NOT IN ('PROCEED', 'PROCEED_WITH_MEASURES') "
            "OR supervisory_authority_consulted",
            name="ck_dpia_high_residual_requires_consultation",
        ),
    )

    op.create_table(
        "business_impact_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bia_ref", sa.String(length=24), nullable=False, unique=True),
        sa.Column("process_name", sa.String(length=240), nullable=False),
        sa.Column("process_description", sa.Text(), nullable=False),
        sa.Column("owner_role", sa.String(length=120), nullable=False),
        sa.Column("rto_hours", sa.Float(), nullable=False),
        sa.Column("rpo_hours", sa.Float(), nullable=False),
        sa.Column("mtpd_hours", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="GBP"),
        sa.Column("impact_1h", sa.Numeric(14, 2), nullable=False),
        sa.Column("impact_24h", sa.Numeric(14, 2), nullable=False),
        sa.Column("impact_1w", sa.Numeric(14, 2), nullable=False),
        sa.Column("impact_note", sa.Text(), nullable=False),
        sa.Column("workaround", sa.Text(), nullable=False),
        sa.Column("recovery_note", sa.Text(), nullable=True),
        sa.Column("last_reviewed", sa.Date(), nullable=True),
        *_timestamps(),
        # A recovery target beyond the tolerable outage is a plan that fails on the day
        # it is written.
        sa.CheckConstraint("rto_hours <= mtpd_hours", name="ck_bia_rto_within_mtpd"),
        sa.CheckConstraint("rpo_hours <= mtpd_hours", name="ck_bia_rpo_within_mtpd"),
        sa.CheckConstraint(
            "rto_hours >= 0 AND rpo_hours >= 0 AND mtpd_hours >= 0", name="ck_bia_non_negative"
        ),
    )

    _link_table("ropa_asset_links", "ropa_id", "ropa_entries", "asset_id", "assets", "uq_ropa_asset")
    _link_table("ropa_risk_links", "ropa_id", "ropa_entries", "risk_id", "risks", "uq_ropa_risk")
    _link_table(
        "ropa_control_links", "ropa_id", "ropa_entries", "control_id", "controls", "uq_ropa_control"
    )
    _link_table("dpia_asset_links", "dpia_id", "dpias", "asset_id", "assets", "uq_dpia_asset")
    _link_table("dpia_risk_links", "dpia_id", "dpias", "risk_id", "risks", "uq_dpia_risk")
    _link_table(
        "bia_asset_links", "bia_id", "business_impact_analyses", "asset_id", "assets",
        "uq_bia_asset",
    )
    _link_table(
        "bia_control_links", "bia_id", "business_impact_analyses", "control_id", "controls",
        "uq_bia_control",
    )
    _link_table(
        "bia_risk_links", "bia_id", "business_impact_analyses", "risk_id", "risks", "uq_bia_risk"
    )


def downgrade() -> None:
    for table in (
        "bia_risk_links", "bia_control_links", "bia_asset_links",
        "dpia_risk_links", "dpia_asset_links",
        "ropa_control_links", "ropa_risk_links", "ropa_asset_links",
        "business_impact_analyses", "dpias", "ropa_entries",
    ):
        op.drop_table(table)
    op.drop_index("ix_risk_exceptions_expiry", table_name="risk_exceptions")
    op.drop_table("risk_exceptions")
    op.drop_table("assets")

    bind = op.get_bind()
    for enum in reversed(_ENUMS):
        enum.drop(bind, checkfirst=True)
