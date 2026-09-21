"""Freeze the exact SoA approved; edits remain a working copy."""
import sqlalchemy as sa
from alembic import op
revision="0016"
down_revision="0015"
branch_labels=depends_on=None

def upgrade():
    op.create_table("soa_releases",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("version",sa.String(32),nullable=False,unique=True),
        sa.Column("status",sa.String(16),nullable=False),sa.Column("entries",sa.JSON(),nullable=False),sa.Column("entry_count",sa.Integer(),nullable=False),
        sa.Column("content_digest",sa.String(64),nullable=False),sa.Column("change_note",sa.Text(),nullable=False),sa.Column("prepared_by",sa.String(120),nullable=False),
        sa.Column("evidence_warnings",sa.JSON(),nullable=False),sa.Column("evidence_limitations_acknowledged",sa.Boolean(),nullable=False),
        sa.Column("approved_by",sa.String(64)),sa.Column("approved_at",sa.DateTime(timezone=True)),sa.Column("approval_note",sa.Text()),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('DRAFT','APPROVED')",name="ck_soa_release_status"),
        sa.CheckConstraint("entry_count=93 AND length(content_digest)=64 AND length(trim(change_note))>0",name="ck_soa_release_content"),
        sa.CheckConstraint("status != 'APPROVED' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL AND approval_note IS NOT NULL AND length(trim(approval_note))>0 AND approval_note NOT LIKE '%TODO AUTHOR:BENNY%' AND change_note NOT LIKE '%TODO AUTHOR:BENNY%')",name="ck_soa_release_approval"))

def downgrade(): op.drop_table("soa_releases")
