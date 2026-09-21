"""Store retrievable evidence bytes with version, integrity and retention controls."""
import sqlalchemy as sa
from alembic import op
revision="0015"
down_revision="0014"
branch_labels=depends_on=None

def upgrade():
    op.create_table("evidence_attachments",sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("evidence_id",sa.Integer(),sa.ForeignKey("evidence.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("version",sa.String(32),nullable=False),sa.Column("filename",sa.String(240),nullable=False),sa.Column("content_type",sa.String(64),nullable=False),
        sa.Column("byte_size",sa.Integer(),nullable=False),sa.Column("sha256",sa.String(64),nullable=False),sa.Column("content_data",sa.LargeBinary()),
        sa.Column("source",sa.Text(),nullable=False),sa.Column("uploaded_by",sa.String(64),nullable=False),sa.Column("uploaded_on",sa.Date(),nullable=False),
        sa.Column("access_scope",sa.String(24),nullable=False),sa.Column("retention_until",sa.Date(),nullable=False),sa.Column("retention_reason",sa.Text(),nullable=False),
        sa.Column("legal_hold",sa.Boolean(),nullable=False),sa.Column("purged_on",sa.Date()),sa.Column("purged_by",sa.String(64)),sa.Column("purge_reason",sa.Text()),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.UniqueConstraint("evidence_id","version",name="uq_evidence_attachment_version"),
        sa.CheckConstraint("byte_size > 0 AND byte_size <= 8388608 AND length(sha256)=64",name="ck_attachment_size_hash"),
        sa.CheckConstraint("access_scope IN ('REGISTER_READERS','MAINTAINERS')",name="ck_attachment_access"),
        sa.CheckConstraint("content_type IN ('application/pdf','image/png','image/jpeg','text/plain','text/csv','application/json')",name="ck_attachment_type"),
        sa.CheckConstraint("length(trim(filename))>0 AND length(trim(version))>0 AND length(trim(source))>0 AND length(trim(retention_reason))>0",name="ck_attachment_required"),
        sa.CheckConstraint("retention_until >= uploaded_on",name="ck_attachment_retention"),
        sa.CheckConstraint("(purged_on IS NULL AND content_data IS NOT NULL AND length(content_data)=byte_size) OR (purged_on IS NOT NULL AND content_data IS NULL AND purged_by IS NOT NULL AND purge_reason IS NOT NULL AND length(trim(purge_reason))>0 AND NOT legal_hold AND purged_on>=retention_until)",name="ck_attachment_purge"))

def downgrade():
    op.drop_table("evidence_attachments")
