"""Evidence, remediation items and the Statement of Applicability.

Revision ID: 0003
Revises: 0002
Create Date: Phase 3
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.db.migration_types import pg_enum

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

evidence_type = pg_enum(
    "POLICY", "CONFIG_EXPORT", "REPORT", "LOG_EXTRACT", "SCREENSHOT", "ATTESTATION",
    "CERTIFICATE", "TICKET",
    name="evidence_type",
)
remediation_status = pg_enum(
    "OPEN", "IN_PROGRESS", "BLOCKED", "COMPLETED", "CANCELLED", name="remediation_status"
)
remediation_priority = pg_enum(
    "LOW", "MEDIUM", "HIGH", "CRITICAL", name="remediation_priority"
)
remediation_source = pg_enum(
    "SOA_GAP", "CONTROL_TEST", "AUDIT_FINDING", "RISK_TREATMENT", name="remediation_source"
)
implementation_status = pg_enum(
    "NOT_IMPLEMENTED", "PARTIALLY_IMPLEMENTED", "IMPLEMENTED", name="implementation_status"
)

_ENUMS = (
    evidence_type, remediation_status, remediation_priority, remediation_source,
    implementation_status,
)

def _timestamps() -> list[sa.Column]:
    """Fresh Column objects each call -- a Column instance cannot be reused."""
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
        "evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("evidence_ref", sa.String(length=24), nullable=False, unique=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence_type", evidence_type, nullable=False),
        sa.Column("source_system", sa.String(length=120), nullable=False),
        sa.Column("collected_by", sa.String(length=120), nullable=False),
        sa.Column("collected_date", sa.Date(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=False),
        sa.Column("file_reference", sa.String(length=300), nullable=True),
        sa.Column("control_id", sa.Integer(), sa.ForeignKey("controls.id", ondelete="SET NULL"), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("valid_until >= valid_from", name="ck_evidence_validity_window"),
    )

    op.create_table(
        "remediation_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("remediation_ref", sa.String(length=24), nullable=False, unique=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        # NOT NULL by design: a remediation item without an owner and a date is a wish,
        # and the SoA gap rule would otherwise be satisfiable by an empty promise.
        sa.Column("owner", sa.String(length=120), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", remediation_status, nullable=False),
        sa.Column("priority", remediation_priority, nullable=False),
        sa.Column("source", remediation_source, nullable=False),
        sa.Column("completed_date", sa.Date(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("length(trim(owner)) > 0", name="ck_remediation_owner_present"),
    )
    op.create_index("ix_remediation_status", "remediation_items", ["status"])

    op.create_table(
        "soa_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "framework_control_id",
            sa.Integer(),
            sa.ForeignKey("framework_controls.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("control_ref", sa.String(length=24), nullable=False, unique=True),
        sa.Column("control_title", sa.String(length=300), nullable=False),
        sa.Column("theme", sa.String(length=16), nullable=False),
        sa.Column("applicable", sa.Boolean(), nullable=False),
        sa.Column("justification_inclusion", sa.Text(), nullable=True),
        sa.Column("justification_exclusion", sa.Text(), nullable=True),
        sa.Column("implementation_status", implementation_status, nullable=False),
        sa.Column("implementation_description", sa.Text(), nullable=True),
        sa.Column("owner", sa.String(length=120), nullable=False),
        sa.Column("last_reviewed", sa.Date(), nullable=True),
        sa.Column("next_review", sa.Date(), nullable=True),
        sa.Column("approved_by", sa.String(length=120), nullable=True),
        sa.Column("approved_date", sa.Date(), nullable=True),
        sa.Column("version", sa.String(length=16), nullable=False, server_default="1.0"),
        *_timestamps(),
        # Clause 6.1.3 d) in database form: an applicability decision must carry the
        # justification that matches it, and an excluded control cannot claim to be
        # implemented. The remediation rule needs a join, so it lives in the API layer.
        sa.CheckConstraint(
            "(applicable AND length(trim(coalesce(justification_inclusion, ''))) > 0) "
            "OR (NOT applicable AND length(trim(coalesce(justification_exclusion, ''))) > 0)",
            name="ck_soa_justification_matches_applicability",
        ),
        sa.CheckConstraint(
            "applicable OR implementation_status = 'NOT_IMPLEMENTED'",
            name="ck_soa_excluded_not_implemented",
        ),
    )
    op.create_index("ix_soa_entries_theme", "soa_entries", ["theme"])

    for table, column, target, constraint in (
        ("soa_control_links", "control_id", "controls.id", "uq_soa_control"),
        ("soa_risk_links", "risk_id", "risks.id", "uq_soa_risk"),
        ("soa_evidence_links", "evidence_id", "evidence.id", "uq_soa_evidence"),
        ("soa_remediation_links", "remediation_id", "remediation_items.id", "uq_soa_remediation"),
    ):
        op.create_table(
            table,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "soa_entry_id",
                sa.Integer(),
                sa.ForeignKey("soa_entries.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(column, sa.Integer(), sa.ForeignKey(target, ondelete="CASCADE"), nullable=False),
            *_timestamps(),
            sa.UniqueConstraint("soa_entry_id", column, name=constraint),
        )


def downgrade() -> None:
    for table in (
        "soa_remediation_links", "soa_evidence_links", "soa_risk_links", "soa_control_links",
    ):
        op.drop_table(table)
    op.drop_index("ix_soa_entries_theme", table_name="soa_entries")
    op.drop_table("soa_entries")
    op.drop_index("ix_remediation_status", table_name="remediation_items")
    op.drop_table("remediation_items")
    op.drop_table("evidence")

    bind = op.get_bind()
    for enum in reversed(_ENUMS):
        enum.drop(bind, checkfirst=True)
