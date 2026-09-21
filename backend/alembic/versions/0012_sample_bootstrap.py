"""Preserve existing business records when startup initializes a new release."""
import sqlalchemy as sa
from alembic import op
revision="0012"
down_revision="0011"
branch_labels=depends_on=None

def upgrade():
    op.create_table("sample_bootstrap",sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("status",sa.String(16),nullable=False),sa.Column("reason",sa.Text(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.CheckConstraint("id = 1",name="ck_single_bootstrap"),
        sa.CheckConstraint("status IN ('INITIALIZED', 'PRESERVED', 'REAPPLIED')",name="ck_bootstrap_status"),
        sa.CheckConstraint("length(trim(reason)) > 0",name="ck_bootstrap_reason"))
    op.execute("INSERT INTO sample_bootstrap (id,status,reason) SELECT 1,'PRESERVED','Existing records preserved on upgrade; sample reapplication was not requested.' WHERE EXISTS (SELECT 1 FROM risks) OR EXISTS (SELECT 1 FROM users) OR EXISTS (SELECT 1 FROM framework_controls)")

def downgrade():
    op.drop_table("sample_bootstrap")
