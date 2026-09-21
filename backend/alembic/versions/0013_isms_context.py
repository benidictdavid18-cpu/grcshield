"""Retain scope decisions and the context that informed them."""
import sqlalchemy as sa
from alembic import op
revision="0013"
down_revision="0012"
branch_labels=depends_on=None

def timestamps():
    return [sa.Column(n,sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()) for n in ("created_at","updated_at")]

def upgrade():
    op.create_table("isms_context",
        sa.Column("id",sa.Integer(),primary_key=True),sa.Column("context_ref",sa.String(32),nullable=False,unique=True),
        sa.Column("kind",sa.String(24),nullable=False),sa.Column("topic",sa.String(64),nullable=False),sa.Column("title",sa.String(240),nullable=False),
        sa.Column("statement",sa.Text(),nullable=False),sa.Column("source",sa.Text(),nullable=False),sa.Column("owner",sa.String(160),nullable=False),
        sa.Column("review_date",sa.Date(),nullable=False),sa.Column("relevance",sa.String(16),nullable=False),sa.Column("decision_note",sa.Text(),nullable=False),
        sa.Column("risk_id",sa.Integer(),sa.ForeignKey("risks.id",ondelete="RESTRICT")),sa.Column("status",sa.String(16),nullable=False),
        sa.Column("revision",sa.Integer(),nullable=False),sa.Column("reviewed_by",sa.String(64)),sa.Column("reviewed_on",sa.Date()),
        sa.CheckConstraint("kind IN ('ISSUE', 'PARTY_REQUIREMENT', 'PROCESS')",name="ck_context_kind"),
        sa.CheckConstraint("relevance IN ('UNASSESSED', 'RELEVANT', 'NOT_RELEVANT')",name="ck_context_relevance"),
        sa.CheckConstraint("status IN ('DRAFT', 'REVIEWED')",name="ck_context_status"),
        sa.CheckConstraint("length(trim(owner)) > 0 AND length(trim(source)) > 0 AND length(trim(statement)) > 0",name="ck_context_required"),
        sa.CheckConstraint("status != 'REVIEWED' OR (reviewed_by IS NOT NULL AND reviewed_on IS NOT NULL AND relevance != 'UNASSESSED' AND length(trim(decision_note)) > 0 AND decision_note NOT LIKE '%TODO AUTHOR:BENNY%' AND owner NOT LIKE '%TODO AUTHOR:BENNY%')",name="ck_context_review"),*timestamps())
    op.create_table("isms_scope_revisions",
        sa.Column("id",sa.Integer(),primary_key=True),sa.Column("version",sa.String(32),nullable=False,unique=True),
        sa.Column("statement",sa.Text(),nullable=False),sa.Column("interfaces",sa.Text(),nullable=False),sa.Column("exclusions",sa.Text(),nullable=False),
        sa.Column("owner",sa.String(160),nullable=False),sa.Column("review_date",sa.Date(),nullable=False),sa.Column("context_snapshot",sa.JSON(),nullable=False),
        sa.Column("status",sa.String(16),nullable=False),sa.Column("approved_by",sa.String(64)),sa.Column("approved_on",sa.Date()),sa.Column("approval_note",sa.Text()),
        sa.CheckConstraint("status IN ('DRAFT', 'APPROVED')",name="ck_scope_status"),
        sa.CheckConstraint("length(trim(statement)) > 0 AND length(trim(interfaces)) > 0 AND length(trim(owner)) > 0",name="ck_scope_required"),
        sa.CheckConstraint("status != 'APPROVED' OR (approved_by IS NOT NULL AND approved_on IS NOT NULL AND approval_note IS NOT NULL AND length(trim(approval_note)) > 0 AND approval_note NOT LIKE '%TODO AUTHOR:BENNY%')",name="ck_scope_approval"),*timestamps())

def downgrade():
    op.drop_table("isms_scope_revisions")
    op.drop_table("isms_context")
