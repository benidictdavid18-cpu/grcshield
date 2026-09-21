"""Hold controlled content and preserve the exact revision approved and distributed."""
import sqlalchemy as sa
from alembic import op
revision="0014"
down_revision="0013"
branch_labels=depends_on=None

def timestamps():
    return [sa.Column(n,sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()) for n in ("created_at","updated_at")]

def upgrade():
    op.create_table("controlled_documents",sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("document_ref",sa.String(32),nullable=False,unique=True),sa.Column("title",sa.String(240),nullable=False),
        sa.Column("owner",sa.String(160),nullable=False),sa.Column("classification",sa.String(16),nullable=False),sa.Column("source_kind",sa.String(16),nullable=False),
        sa.Column("external_source",sa.Text()),sa.Column("distribution",sa.Text(),nullable=False),sa.Column("review_date",sa.Date(),nullable=False),
        sa.CheckConstraint("classification IN ('PUBLIC','INTERNAL','CONFIDENTIAL','RESTRICTED')",name="ck_document_classification"),
        sa.CheckConstraint("source_kind IN ('INTERNAL','EXTERNAL')",name="ck_document_source_kind"),
        sa.CheckConstraint("length(trim(title))>0 AND length(trim(owner))>0 AND length(trim(distribution))>0",name="ck_document_required"),
        sa.CheckConstraint("source_kind != 'EXTERNAL' OR (external_source IS NOT NULL AND length(trim(external_source))>0)",name="ck_document_external_source"),*timestamps())
    op.create_table("document_revisions",sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("document_id",sa.Integer(),sa.ForeignKey("controlled_documents.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("version",sa.String(32),nullable=False),sa.Column("content",sa.Text(),nullable=False),sa.Column("content_digest",sa.String(64),nullable=False),
        sa.Column("change_note",sa.Text(),nullable=False),sa.Column("author",sa.String(120),nullable=False),sa.Column("status",sa.String(16),nullable=False),
        sa.Column("evidence_id",sa.Integer(),sa.ForeignKey("evidence.id",ondelete="RESTRICT")),sa.Column("approved_by",sa.String(64)),sa.Column("approved_on",sa.Date()),
        sa.Column("approval_note",sa.Text()),sa.Column("published_on",sa.Date()),sa.Column("withdrawal_note",sa.Text()),
        sa.UniqueConstraint("document_id","version",name="uq_document_version"),
        sa.CheckConstraint("status IN ('DRAFT','APPROVED','PUBLISHED','SUPERSEDED','WITHDRAWN')",name="ck_document_revision_status"),
        sa.CheckConstraint("length(trim(content))>0 AND length(trim(change_note))>0 AND length(content_digest)=64",name="ck_document_revision_content"),
        sa.CheckConstraint("status = 'DRAFT' OR (approved_by IS NOT NULL AND approved_on IS NOT NULL AND approval_note IS NOT NULL AND length(trim(approval_note))>0 AND approval_note NOT LIKE '%TODO AUTHOR:BENNY%' AND content NOT LIKE '%TODO AUTHOR:BENNY%')",name="ck_document_revision_approval"),
        sa.CheckConstraint("status NOT IN ('PUBLISHED','SUPERSEDED','WITHDRAWN') OR published_on IS NOT NULL",name="ck_document_revision_publication"),*timestamps())
    op.create_index("uq_document_published","document_revisions",["document_id"],unique=True,sqlite_where=sa.text("status = 'PUBLISHED'"),postgresql_where=sa.text("status = 'PUBLISHED'"))
    op.create_table("document_acknowledgements",sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("revision_id",sa.Integer(),sa.ForeignKey("document_revisions.id",ondelete="RESTRICT"),nullable=False),sa.Column("username",sa.String(64),nullable=False),
        sa.UniqueConstraint("revision_id","username",name="uq_document_acknowledgement"),*timestamps())

def downgrade():
    op.drop_table("document_acknowledgements")
    op.drop_index("uq_document_published",table_name="document_revisions")
    op.drop_table("document_revisions")
    op.drop_table("controlled_documents")
