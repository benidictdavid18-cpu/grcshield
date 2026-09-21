"""Record objectives, resource commitments and evaluated management-system changes."""
import sqlalchemy as sa
from alembic import op
revision="0018"
down_revision="0017"
branch_labels=depends_on=None

def timestamps():
    return [sa.Column(n,sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()) for n in ("created_at","updated_at")]

def upgrade():
    op.create_table("isms_plans",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("plan_ref",sa.String(32),nullable=False,unique=True),
        sa.Column("kind",sa.String(16),nullable=False),sa.Column("title",sa.String(240),nullable=False),sa.Column("owner",sa.String(160),nullable=False),
        sa.Column("resources",sa.Text(),nullable=False),sa.Column("rationale",sa.Text(),nullable=False),sa.Column("context_id",sa.Integer(),sa.ForeignKey("isms_context.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("risk_id",sa.Integer(),sa.ForeignKey("risks.id",ondelete="RESTRICT")),sa.Column("kri_id",sa.Integer(),sa.ForeignKey("kri_definitions.id",ondelete="RESTRICT")),
        sa.Column("due_date",sa.Date()),sa.Column("measure_definition",sa.Text()),sa.Column("target_value",sa.Float()),sa.Column("direction",sa.String(24)),sa.Column("impact_assessment",sa.Text()),sa.Column("rollback_plan",sa.Text()),
        sa.Column("status",sa.String(16),nullable=False),sa.Column("revision",sa.Integer(),nullable=False),sa.Column("approved_by",sa.String(64)),sa.Column("approved_at",sa.DateTime(timezone=True)),
        sa.Column("approved_snapshot",sa.JSON(none_as_null=True)),sa.Column("approval_note",sa.Text()),sa.Column("implementation_date",sa.Date()),
        sa.Column("implementation_evidence_id",sa.Integer(),sa.ForeignKey("evidence.id",ondelete="RESTRICT")),sa.Column("implementation_note",sa.Text()),sa.Column("cancellation_note",sa.Text()),
        sa.CheckConstraint("kind IN ('OBJECTIVE','CHANGE')",name="ck_isms_plan_kind"),sa.CheckConstraint("status IN ('DRAFT','APPROVED','IMPLEMENTED','EVALUATED','CANCELLED')",name="ck_isms_plan_status"),
        sa.CheckConstraint("length(trim(title))>0 AND length(trim(owner))>0 AND length(trim(resources))>0 AND length(trim(rationale))>0",name="ck_isms_plan_required"),
        sa.CheckConstraint("direction IS NULL OR direction IN ('HIGHER_IS_BETTER','LOWER_IS_BETTER')",name="ck_isms_plan_direction"),
        sa.CheckConstraint("status IN ('DRAFT','CANCELLED') OR (due_date IS NOT NULL AND approved_by IS NOT NULL AND approved_at IS NOT NULL AND approval_note IS NOT NULL AND approved_snapshot IS NOT NULL AND ((kind='OBJECTIVE' AND measure_definition IS NOT NULL AND target_value IS NOT NULL AND direction IS NOT NULL) OR (kind='CHANGE' AND impact_assessment IS NOT NULL AND rollback_plan IS NOT NULL)))",name="ck_isms_plan_approval"),
        sa.CheckConstraint("status != 'IMPLEMENTED' OR (kind='CHANGE' AND implementation_date IS NOT NULL AND implementation_evidence_id IS NOT NULL AND implementation_note IS NOT NULL)",name="ck_isms_change_implementation"),*timestamps())
    op.create_table("isms_plan_evaluations",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("plan_id",sa.Integer(),sa.ForeignKey("isms_plans.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("observed_on",sa.Date(),nullable=False),sa.Column("observed_value",sa.Float()),sa.Column("evaluation_note",sa.Text(),nullable=False),
        sa.Column("evidence_id",sa.Integer(),sa.ForeignKey("evidence.id",ondelete="RESTRICT"),nullable=False),sa.Column("actor",sa.String(64),nullable=False),
        sa.CheckConstraint("length(trim(evaluation_note))>0 AND length(trim(actor))>0",name="ck_plan_evaluation_note"),*timestamps())

def downgrade():
    op.drop_table("isms_plan_evaluations")
    op.drop_table("isms_plans")
