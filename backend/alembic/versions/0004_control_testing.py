"""Control testing workpapers, audit findings and ISO clause-level records.

Adds design/operating effectiveness to the internal control library, the control_tests
workpaper table, audit_findings, and the Clause 9.2 / 9.3 / 10.2 registers.

Revision ID: 0004
Revises: 0003
Create Date: Phase 4
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.db.migration_types import pg_enum

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

design_effectiveness = pg_enum(
    "NOT_ASSESSED", "EFFECTIVE", "DEFICIENT", name="design_effectiveness"
)
operating_effectiveness = pg_enum(
    "NOT_TESTED", "EFFECTIVE", "EFFECTIVE_WITH_EXCEPTIONS", "INEFFECTIVE",
    name="operating_effectiveness",
)
sample_selection_method = pg_enum(
    "RANDOM", "HAPHAZARD", "JUDGMENTAL", "FULL_POPULATION", name="sample_selection_method"
)
test_conclusion = pg_enum(
    "PASS", "PASS_WITH_EXCEPTIONS", "FAIL", name="test_conclusion"
)
finding_severity = pg_enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="finding_severity")
finding_status = pg_enum("DRAFT", "OPEN", "REMEDIATED", "CLOSED", name="finding_status")
finding_source = pg_enum(
    "CONTROL_TEST", "INTERNAL_AUDIT", "MANAGEMENT_REVIEW", "INCIDENT", name="finding_source"
)
audit_status = pg_enum(
    "PLANNED", "IN_PROGRESS", "COMPLETED", "DEFERRED", name="audit_status"
)
nonconformity_status = pg_enum(
    "OPEN", "CORRECTION_APPLIED", "CORRECTIVE_ACTION_IN_PROGRESS",
    "AWAITING_EFFECTIVENESS_CHECK", "CLOSED",
    name="nonconformity_status",
)

_ENUMS = (
    design_effectiveness, operating_effectiveness, sample_selection_method,
    test_conclusion, finding_severity, finding_status, finding_source, audit_status,
    nonconformity_status,
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


def upgrade() -> None:
    bind = op.get_bind()
    for enum in _ENUMS:
        enum.create(bind, checkfirst=True)

    # --- Effectiveness on the internal control library ------------------------
    op.add_column(
        "controls",
        sa.Column(
            "design_effectiveness", design_effectiveness, nullable=False,
            server_default="NOT_ASSESSED",
        ),
    )
    op.add_column(
        "controls",
        sa.Column(
            "operating_effectiveness", operating_effectiveness, nullable=False,
            server_default="NOT_TESTED",
        ),
    )
    op.add_column("controls", sa.Column("effectiveness_note", sa.Text(), nullable=True))
    op.add_column("controls", sa.Column("last_tested", sa.Date(), nullable=True))
    # A deficient design caps operating effectiveness below EFFECTIVE. Enforced in the
    # database as well as the API so it holds regardless of write path.
    #
    # batch_alter_table emits a plain ALTER on PostgreSQL and a table rebuild on SQLite,
    # which is what lets the migration chain be exercised end to end in the test suite.
    with op.batch_alter_table("controls") as batch:
        batch.create_check_constraint(
            "ck_controls_design_caps_operating",
            "NOT (design_effectiveness = 'DEFICIENT' AND operating_effectiveness = 'EFFECTIVE')",
        )

    # --- Findings ---------------------------------------------------------------
    op.create_table(
        "audit_findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("finding_ref", sa.String(length=24), nullable=False, unique=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", finding_severity, nullable=False),
        sa.Column("status", finding_status, nullable=False),
        sa.Column("source", finding_source, nullable=False),
        sa.Column("identified_date", sa.Date(), nullable=False),
        sa.Column("identified_by", sa.String(length=120), nullable=False),
        sa.Column("owner", sa.String(length=120), nullable=False),
        sa.Column("closed_date", sa.Date(), nullable=True),
        sa.Column(
            "control_id", sa.Integer(), sa.ForeignKey("controls.id", ondelete="SET NULL"),
            nullable=True,
        ),
        *_timestamps(),
    )
    op.create_index("ix_audit_findings_status", "audit_findings", ["status"])

    op.create_table(
        "finding_remediation_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "finding_id", sa.Integer(),
            sa.ForeignKey("audit_findings.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "remediation_id", sa.Integer(),
            sa.ForeignKey("remediation_items.id", ondelete="CASCADE"), nullable=False,
        ),
        *_timestamps(),
        sa.UniqueConstraint("finding_id", "remediation_id", name="uq_finding_remediation"),
    )

    # --- Workpapers ---------------------------------------------------------------
    op.create_table(
        "control_tests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("test_ref", sa.String(length=24), nullable=False, unique=True),
        sa.Column(
            "control_id", sa.Integer(), sa.ForeignKey("controls.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tester", sa.String(length=120), nullable=False),
        sa.Column("test_date", sa.Date(), nullable=False),
        sa.Column("period_covered_start", sa.Date(), nullable=False),
        sa.Column("period_covered_end", sa.Date(), nullable=False),
        sa.Column("test_objective", sa.Text(), nullable=False),
        sa.Column("test_procedure", sa.Text(), nullable=False),
        sa.Column("population_description", sa.Text(), nullable=False),
        sa.Column("population_size", sa.Integer(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("sample_selection_method", sample_selection_method, nullable=False),
        sa.Column("sampling_rationale", sa.Text(), nullable=False),
        sa.Column("results_summary", sa.Text(), nullable=False),
        sa.Column("exceptions_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("exception_details", sa.Text(), nullable=True),
        sa.Column("conclusion", test_conclusion, nullable=False),
        sa.Column("reviewed_by", sa.String(length=120), nullable=True),
        sa.Column("review_date", sa.Date(), nullable=True),
        sa.Column(
            "linked_finding_id", sa.Integer(),
            sa.ForeignKey("audit_findings.id", ondelete="SET NULL"), nullable=True,
        ),
        *_timestamps(),
        sa.CheckConstraint("population_size >= 1", name="ck_control_tests_population"),
        sa.CheckConstraint("sample_size >= 1", name="ck_control_tests_sample_min"),
        sa.CheckConstraint(
            "sample_size <= population_size", name="ck_control_tests_sample_within_population"
        ),
        sa.CheckConstraint(
            "exceptions_count >= 0 AND exceptions_count <= sample_size",
            name="ck_control_tests_exceptions_within_sample",
        ),
        sa.CheckConstraint(
            "length(trim(sampling_rationale)) > 0", name="ck_control_tests_rationale_present"
        ),
        sa.CheckConstraint(
            "period_covered_end >= period_covered_start", name="ck_control_tests_period"
        ),
        # Exceptions and conclusions must agree in both directions.
        sa.CheckConstraint(
            "(exceptions_count = 0 AND conclusion <> 'PASS_WITH_EXCEPTIONS') "
            "OR (exceptions_count > 0 AND conclusion <> 'PASS')",
            name="ck_control_tests_conclusion_matches_exceptions",
        ),
    )
    op.create_index("ix_control_tests_control", "control_tests", ["control_id"])

    op.create_table(
        "control_test_evidence_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "control_test_id", sa.Integer(),
            sa.ForeignKey("control_tests.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "evidence_id", sa.Integer(), sa.ForeignKey("evidence.id", ondelete="CASCADE"),
            nullable=False,
        ),
        *_timestamps(),
        sa.UniqueConstraint(
            "control_test_id", "evidence_id", name="uq_control_test_evidence"
        ),
    )

    # --- Clause 9.2 / 9.3 / 10.2 ------------------------------------------------
    op.create_table(
        "internal_audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("audit_ref", sa.String(length=24), nullable=False, unique=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("objectives", sa.Text(), nullable=False),
        sa.Column("criteria", sa.Text(), nullable=False),
        sa.Column("auditor", sa.String(length=160), nullable=False),
        sa.Column("independence_note", sa.Text(), nullable=False),
        sa.Column("planned_start", sa.Date(), nullable=False),
        sa.Column("planned_end", sa.Date(), nullable=False),
        sa.Column("actual_start", sa.Date(), nullable=True),
        sa.Column("actual_end", sa.Date(), nullable=True),
        sa.Column("status", audit_status, nullable=False),
        sa.Column("outcome_summary", sa.Text(), nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "management_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("review_ref", sa.String(length=24), nullable=False, unique=True),
        sa.Column("review_date", sa.Date(), nullable=False),
        sa.Column("chair", sa.String(length=120), nullable=False),
        sa.Column("attendees", sa.Text(), nullable=False),
        sa.Column("inputs_considered", sa.Text(), nullable=False),
        sa.Column("decisions", sa.Text(), nullable=False),
        sa.Column("actions", sa.Text(), nullable=False),
        sa.Column("next_review_date", sa.Date(), nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "nonconformities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nc_ref", sa.String(length=24), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source", finding_source, nullable=False),
        sa.Column("identified_date", sa.Date(), nullable=False),
        sa.Column("identified_by", sa.String(length=120), nullable=False),
        sa.Column("owner", sa.String(length=120), nullable=False),
        sa.Column("immediate_correction", sa.Text(), nullable=False),
        sa.Column("root_cause_analysis", sa.Text(), nullable=True),
        sa.Column("corrective_action", sa.Text(), nullable=True),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("effectiveness_check_date", sa.Date(), nullable=True),
        sa.Column("effectiveness_check_result", sa.Text(), nullable=True),
        sa.Column("status", nonconformity_status, nullable=False),
        sa.Column("closure_date", sa.Date(), nullable=True),
        sa.Column(
            "finding_id", sa.Integer(),
            sa.ForeignKey("audit_findings.id", ondelete="SET NULL"), nullable=True,
        ),
        *_timestamps(),
        # Clause 10.2 d): closure requires evidence the corrective action worked.
        sa.CheckConstraint(
            "status <> 'CLOSED' OR length(trim(coalesce(effectiveness_check_result, ''))) > 0",
            name="ck_nonconformity_closed_needs_effectiveness_check",
        ),
    )


def downgrade() -> None:
    op.drop_table("nonconformities")
    op.drop_table("management_reviews")
    op.drop_table("internal_audits")
    op.drop_table("control_test_evidence_links")
    op.drop_index("ix_control_tests_control", table_name="control_tests")
    op.drop_table("control_tests")
    op.drop_table("finding_remediation_links")
    op.drop_index("ix_audit_findings_status", table_name="audit_findings")
    op.drop_table("audit_findings")

    with op.batch_alter_table("controls") as batch:
        batch.drop_constraint("ck_controls_design_caps_operating", type_="check")
    op.drop_column("controls", "last_tested")
    op.drop_column("controls", "effectiveness_note")
    op.drop_column("controls", "operating_effectiveness")
    op.drop_column("controls", "design_effectiveness")

    bind = op.get_bind()
    for enum in reversed(_ENUMS):
        enum.drop(bind, checkfirst=True)
