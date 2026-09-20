"""Name the workpaper supporting a risk claim and retain reassessment decisions."""
import sqlalchemy as sa
from alembic import op
revision = "0010"
down_revision = "0009"
branch_labels = depends_on = None

def timestamps():
    return [sa.Column(n, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()) for n in ("created_at", "updated_at")]

def upgrade():
    with op.batch_alter_table("control_tests") as b:
        b.create_unique_constraint("uq_test_control", ["id", "control_id"])
    with op.batch_alter_table("risk_controls") as b:
        b.add_column(sa.Column("supporting_test_id", sa.Integer(), nullable=True))
        b.add_column(sa.Column("proof_note", sa.Text(), nullable=True))
        b.create_foreign_key("fk_risk_control_supporting_test", "control_tests", ["supporting_test_id", "control_id"], ["id", "control_id"], ondelete="RESTRICT")
    # Legacy claims remain visible but explicitly unproven until an author binds a test.
    op.execute("UPDATE risk_controls SET proof_note = 'TODO AUTHOR:BENNY - identify the workpaper and population supporting this tested basis.' WHERE effectiveness_basis IN ('TESTED_EFFECTIVE','TESTED_WITH_EXCEPTIONS','TESTED_INEFFECTIVE')")
    op.create_table("test_dispositions",
        sa.Column("test_id", sa.Integer(), sa.ForeignKey("control_tests.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("replacement_id", sa.Integer(), sa.ForeignKey("control_tests.id", ondelete="RESTRICT")),
        sa.Column("kind", sa.String(16), nullable=False), sa.Column("reason", sa.Text(), nullable=False), sa.Column("actor", sa.String(64), nullable=False),
        sa.CheckConstraint("kind IN ('SUPERSEDED', 'WITHDRAWN')", name="ck_disposition_kind"),
        sa.CheckConstraint("length(trim(reason)) > 0", name="ck_disposition_reason"),
        sa.CheckConstraint("(kind = 'SUPERSEDED' AND replacement_id IS NOT NULL AND replacement_id != test_id) OR (kind = 'WITHDRAWN' AND replacement_id IS NULL)", name="ck_disposition_replacement"), *timestamps())
    op.create_table("reassessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trigger_test_id", sa.Integer(), sa.ForeignKey("control_tests.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("record_type", sa.String(24), nullable=False), sa.Column("record_ref", sa.String(32), nullable=False),
        sa.Column("owner", sa.String(160), nullable=False), sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="OPEN"), sa.Column("resolution", sa.Text()),
        sa.Column("evidence_id", sa.Integer(), sa.ForeignKey("evidence.id", ondelete="RESTRICT")), sa.Column("resolved_by", sa.String(64)),
        sa.UniqueConstraint("trigger_test_id", "record_type", "record_ref", name="uq_reassessment_trigger"),
        sa.CheckConstraint("status IN ('OPEN', 'RESOLVED')", name="ck_reassessment_status"),
        sa.CheckConstraint("length(trim(owner)) > 0", name="ck_reassessment_owner"),
        sa.CheckConstraint("status != 'RESOLVED' OR (resolution IS NOT NULL AND length(trim(resolution)) > 0 AND evidence_id IS NOT NULL AND resolved_by IS NOT NULL)", name="ck_reassessment_resolution"), *timestamps())

def downgrade():
    op.drop_table("reassessments")
    op.drop_table("test_dispositions")
    with op.batch_alter_table("risk_controls") as b:
        b.drop_constraint("fk_risk_control_supporting_test", type_="foreignkey")
        b.drop_column("proof_note")
        b.drop_column("supporting_test_id")
    with op.batch_alter_table("control_tests") as b:
        b.drop_constraint("uq_test_control", type_="unique")
