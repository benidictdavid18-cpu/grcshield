"""maintained assurance workflows

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-21 18:00:14.626621
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '0019'
down_revision: str | None = '0018'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('audit_programmes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('programme_ref', sa.String(length=32), nullable=False),
    sa.Column('owner', sa.String(length=160), nullable=False),
    sa.Column('risk_basis', sa.Text(), nullable=False),
    sa.Column('coverage', sa.Text(), nullable=False),
    sa.Column('frequency', sa.Text(), nullable=False),
    sa.Column('methods', sa.Text(), nullable=False),
    sa.Column('reporting', sa.Text(), nullable=False),
    sa.Column('starts_on', sa.Date(), nullable=False),
    sa.Column('ends_on', sa.Date(), nullable=False),
    sa.Column('review_date', sa.Date(), nullable=False),
    sa.Column('revision', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint('review_date >= starts_on AND ends_on >= starts_on', name='ck_programme_dates'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('programme_ref')
    )
    op.create_table('assurance_cycles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cycle_ref', sa.String(length=32), nullable=False),
    sa.Column('kind', sa.String(length=16), nullable=False),
    sa.Column('audit_id', sa.Integer(), nullable=True),
    sa.Column('review_id', sa.Integer(), nullable=True),
    sa.Column('programme_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('revision', sa.Integer(), nullable=False),
    sa.Column('completed_on', sa.Date(), nullable=True),
    sa.Column('completed_by', sa.String(length=64), nullable=True),
    sa.Column('evidence_id', sa.Integer(), nullable=True),
    sa.Column('completion_snapshot', sa.JSON(none_as_null=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("(kind='AUDIT' AND audit_id IS NOT NULL AND review_id IS NULL AND programme_id IS NOT NULL) OR (kind='REVIEW' AND review_id IS NOT NULL AND audit_id IS NULL AND programme_id IS NULL)", name='ck_assurance_kind'),
    sa.CheckConstraint("status != 'COMPLETED' OR (completed_on IS NOT NULL AND completed_by IS NOT NULL AND evidence_id IS NOT NULL AND completion_snapshot IS NOT NULL)", name='ck_assurance_completion'),
    sa.CheckConstraint("status IN ('DRAFT','IN_PROGRESS','COMPLETED')", name='ck_assurance_status'),
    sa.ForeignKeyConstraint(['audit_id'], ['internal_audits.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['programme_id'], ['audit_programmes.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['review_id'], ['management_reviews.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('audit_id'),
    sa.UniqueConstraint('cycle_ref'),
    sa.UniqueConstraint('review_id')
    )
    op.create_table('assurance_actions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('action_ref', sa.String(length=32), nullable=False),
    sa.Column('cycle_id', sa.Integer(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('owner', sa.String(length=160), nullable=False),
    sa.Column('due_date', sa.Date(), nullable=False),
    sa.Column('finding_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('evidence_id', sa.Integer(), nullable=True),
    sa.Column('completed_on', sa.Date(), nullable=True),
    sa.Column('completed_by', sa.String(length=64), nullable=True),
    sa.Column('completion_note', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("status != 'COMPLETED' OR (evidence_id IS NOT NULL AND completed_on IS NOT NULL AND completed_by IS NOT NULL AND length(trim(coalesce(completion_note,'')))>0)", name='ck_assurance_action_completion'),
    sa.CheckConstraint("status IN ('OPEN','COMPLETED')", name='ck_assurance_action_status'),
    sa.ForeignKeyConstraint(['cycle_id'], ['assurance_cycles.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['finding_id'], ['audit_findings.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('action_ref')
    )
    op.create_table('assurance_inputs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cycle_id', sa.Integer(), nullable=False),
    sa.Column('category', sa.String(length=48), nullable=False),
    sa.Column('consideration', sa.Text(), nullable=False),
    sa.Column('evidence_id', sa.Integer(), nullable=True),
    sa.Column('no_evidence_reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("evidence_id IS NOT NULL OR length(trim(coalesce(no_evidence_reason,'')))>0", name='ck_assurance_input_basis'),
    sa.ForeignKeyConstraint(['cycle_id'], ['assurance_cycles.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('cycle_id', 'category', name='uq_assurance_input')
    )
    op.create_table('corrective_verifications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nonconformity_id', sa.Integer(), nullable=False),
    sa.Column('checked_on', sa.Date(), nullable=False),
    sa.Column('result', sa.String(length=16), nullable=False),
    sa.Column('note', sa.Text(), nullable=False),
    sa.Column('evidence_id', sa.Integer(), nullable=False),
    sa.Column('actor', sa.String(length=64), nullable=False),
    sa.Column('snapshot', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint("result IN ('EFFECTIVE','INEFFECTIVE')", name='ck_corrective_result'),
    sa.CheckConstraint('length(trim(note))>0 AND length(trim(actor))>0', name='ck_corrective_note'),
    sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['nonconformity_id'], ['nonconformities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('corrective_verifications')
    op.drop_table('assurance_inputs')
    op.drop_table('assurance_actions')
    op.drop_table('assurance_cycles')
    op.drop_table('audit_programmes')
