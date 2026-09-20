"""Separate recorded acceptance claims from attributable decisions."""
import sqlalchemy as sa
from alembic import op
revision = "0011"
down_revision = "0010"
branch_labels = depends_on = None

def timestamps():
    return [sa.Column(n,sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()) for n in ("created_at","updated_at")]

def upgrade():
    op.create_table("acceptance_authorities",sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("user_id",sa.Integer(),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),
        sa.Column("business_role",sa.String(120),nullable=False),sa.Column("grant_reason",sa.Text(),nullable=False),
        sa.Column("granted_by",sa.String(64),nullable=False),sa.Column("expires_on",sa.Date(),nullable=False),
        sa.UniqueConstraint("user_id","business_role",name="uq_acceptance_authority"),
        sa.CheckConstraint("length(trim(business_role)) > 0 AND length(trim(grant_reason)) > 0",name="ck_authority_reason"),*timestamps())
    op.create_table("acceptance_decisions",sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("exception_id",sa.Integer(),sa.ForeignKey("risk_exceptions.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("record_digest",sa.String(64),nullable=False),
        sa.Column("decision",sa.String(16),nullable=False),sa.Column("source",sa.String(24),nullable=False),
        sa.Column("actor",sa.String(120),nullable=False),sa.Column("business_role",sa.String(120),nullable=False),
        sa.Column("note",sa.Text(),nullable=False),sa.Column("approval_date",sa.Date()),sa.Column("expiry_date",sa.Date(),nullable=False),
        sa.CheckConstraint("source IN ('AUTHENTICATED', 'SAMPLE_AUTHORED')",name="ck_acceptance_source"),
        sa.CheckConstraint("decision IN ('APPROVED', 'REJECTED', 'WITHDRAWN', 'EXPIRED')",name="ck_acceptance_decision"),
        sa.CheckConstraint("length(trim(note)) > 0 AND length(trim(actor)) > 0",name="ck_acceptance_note"),
        sa.CheckConstraint("decision != 'APPROVED' OR (approval_date IS NOT NULL AND expiry_date > approval_date)",name="ck_signed_acceptance_dates"),*timestamps())

def downgrade():
    op.drop_table("acceptance_decisions")
    op.drop_table("acceptance_authorities")
