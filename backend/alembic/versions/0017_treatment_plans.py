"""Keep treatment milestones within risk review and retain accountable completion."""
import sqlalchemy as sa
from alembic import op
revision="0017"
down_revision="0016"
branch_labels=depends_on=None

def timestamps():
    return [sa.Column(n,sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()) for n in ("created_at","updated_at")]

def upgrade():
    op.create_table("treatment_plans",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("plan_ref",sa.String(32),nullable=False,unique=True),
        sa.Column("risk_id",sa.Integer(),sa.ForeignKey("risks.id",ondelete="RESTRICT"),nullable=False),sa.Column("title",sa.String(240),nullable=False),
        sa.Column("owner",sa.String(160),nullable=False),sa.Column("resources",sa.Text(),nullable=False),sa.Column("rationale",sa.Text(),nullable=False),
        sa.Column("review_deadline",sa.Date(),nullable=False),sa.Column("status",sa.String(16),nullable=False),sa.Column("revision",sa.Integer(),nullable=False),
        sa.Column("approved_by",sa.String(64)),sa.Column("approved_at",sa.DateTime(timezone=True)),sa.Column("approved_snapshot",sa.JSON(none_as_null=True)),sa.Column("approval_note",sa.Text()),
        sa.Column("verification_evidence_id",sa.Integer(),sa.ForeignKey("evidence.id",ondelete="RESTRICT")),sa.Column("verification_note",sa.Text()),sa.Column("closed_by",sa.String(64)),
        sa.UniqueConstraint("id","review_deadline",name="uq_plan_deadline"),
        sa.CheckConstraint("status IN ('DRAFT','APPROVED','COMPLETED','CANCELLED')",name="ck_plan_status"),
        sa.CheckConstraint("length(trim(title))>0 AND length(trim(owner))>0 AND length(trim(resources))>0 AND length(trim(rationale))>0",name="ck_plan_required"),
        sa.CheckConstraint("status NOT IN ('APPROVED','COMPLETED') OR (approved_by IS NOT NULL AND approved_at IS NOT NULL AND approved_snapshot IS NOT NULL AND approval_note IS NOT NULL AND length(trim(approval_note))>0)",name="ck_plan_approval"),
        sa.CheckConstraint("status != 'COMPLETED' OR (verification_evidence_id IS NOT NULL AND verification_note IS NOT NULL AND length(trim(verification_note))>0 AND closed_by IS NOT NULL)",name="ck_plan_completion"),*timestamps())
    op.create_table("treatment_control_links",sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("plan_id",sa.Integer(),sa.ForeignKey("treatment_plans.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("control_id",sa.Integer(),sa.ForeignKey("controls.id",ondelete="RESTRICT"),nullable=False),
        sa.UniqueConstraint("plan_id","control_id",name="uq_treatment_control"),*timestamps())
    op.create_table("treatment_milestones",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("plan_id",sa.Integer(),nullable=False),sa.Column("review_deadline",sa.Date(),nullable=False),
        sa.Column("milestone_ref",sa.String(32),nullable=False),sa.Column("title",sa.String(240),nullable=False),sa.Column("owner",sa.String(160),nullable=False),sa.Column("due_date",sa.Date(),nullable=False),
        sa.Column("dependency_id",sa.Integer()),sa.Column("remediation_id",sa.Integer(),sa.ForeignKey("remediation_items.id",ondelete="RESTRICT")),sa.Column("status",sa.String(16),nullable=False),
        sa.Column("evidence_id",sa.Integer(),sa.ForeignKey("evidence.id",ondelete="RESTRICT")),sa.Column("completion_note",sa.Text()),sa.Column("completed_on",sa.Date()),sa.Column("completed_by",sa.String(64)),
        sa.UniqueConstraint("plan_id","milestone_ref",name="uq_plan_milestone"),sa.UniqueConstraint("id","plan_id",name="uq_milestone_plan"),
        sa.ForeignKeyConstraint(["plan_id","review_deadline"],["treatment_plans.id","treatment_plans.review_deadline"],name="fk_milestone_deadline",onupdate="CASCADE",ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["dependency_id","plan_id"],["treatment_milestones.id","treatment_milestones.plan_id"],name="fk_milestone_dependency",ondelete="RESTRICT"),
        sa.CheckConstraint("due_date <= review_deadline",name="ck_milestone_review_deadline"),sa.CheckConstraint("length(trim(title))>0 AND length(trim(owner))>0",name="ck_milestone_required"),
        sa.CheckConstraint("status IN ('OPEN','IN_PROGRESS','COMPLETED')",name="ck_milestone_status"),sa.CheckConstraint("dependency_id IS NULL OR dependency_id != id",name="ck_milestone_not_self"),
        sa.CheckConstraint("status != 'COMPLETED' OR (evidence_id IS NOT NULL AND completed_on IS NOT NULL AND completed_by IS NOT NULL AND completion_note IS NOT NULL AND length(trim(completion_note))>0)",name="ck_milestone_completion"),*timestamps())
    if op.get_context().dialect.name=="sqlite":
        for event in ("INSERT","UPDATE"):
            op.execute(f"CREATE TRIGGER treatment_deadline_{event.lower()} BEFORE {event} ON treatment_plans WHEN NEW.status IN ('DRAFT','APPROVED') AND ((SELECT next_review FROM risks WHERE id=NEW.risk_id) IS NULL OR NEW.review_deadline > (SELECT next_review FROM risks WHERE id=NEW.risk_id)) BEGIN SELECT RAISE(ABORT, 'treatment deadline exceeds risk review'); END")
        op.execute("CREATE TRIGGER risk_treatment_review BEFORE UPDATE OF next_review ON risks WHEN EXISTS (SELECT 1 FROM treatment_plans WHERE risk_id=NEW.id AND status IN ('DRAFT','APPROVED') AND (NEW.next_review IS NULL OR review_deadline>NEW.next_review)) BEGIN SELECT RAISE(ABORT, 'risk review precedes active treatment deadline'); END")
    else:
        op.execute("""CREATE FUNCTION grc_treatment_deadline() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
        IF TG_TABLE_NAME = 'risks' THEN
          IF EXISTS (SELECT 1 FROM treatment_plans WHERE risk_id=NEW.id AND status IN ('DRAFT','APPROVED') AND (NEW.next_review IS NULL OR review_deadline>NEW.next_review)) THEN RAISE EXCEPTION 'risk review precedes active treatment deadline' USING ERRCODE='23514'; END IF;
        ELSE
          IF NEW.status IN ('DRAFT','APPROVED') AND ((SELECT next_review FROM risks WHERE id=NEW.risk_id) IS NULL OR NEW.review_deadline>(SELECT next_review FROM risks WHERE id=NEW.risk_id)) THEN RAISE EXCEPTION 'treatment deadline exceeds risk review' USING ERRCODE='23514'; END IF;
        END IF;
        RETURN NEW; END $$""")
        op.execute("CREATE TRIGGER treatment_deadline BEFORE INSERT OR UPDATE ON treatment_plans FOR EACH ROW EXECUTE FUNCTION grc_treatment_deadline()")
        op.execute("CREATE TRIGGER risk_treatment_review BEFORE UPDATE OF next_review ON risks FOR EACH ROW EXECUTE FUNCTION grc_treatment_deadline()")

def downgrade():
    if op.get_context().dialect.name=="sqlite":
        for name in ("treatment_deadline_insert","treatment_deadline_update","risk_treatment_review"): op.execute(f"DROP TRIGGER {name}")
    else:
        op.execute("DROP TRIGGER treatment_deadline ON treatment_plans")
        op.execute("DROP TRIGGER risk_treatment_review ON risks")
        op.execute("DROP FUNCTION grc_treatment_deadline()")
    op.drop_table("treatment_milestones")
    op.drop_table("treatment_control_links")
    op.drop_table("treatment_plans")
