"""Framework registry, control library and ISO -> SOC 2 mappings.

Revision ID: 0001
Revises:
Create Date: Phase 1
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

scope_status = sa.Enum("PRIMARY", "SECONDARY", "ROADMAP", name="scope_status")
mapping_relationship = sa.Enum("EQUIVALENT", "PARTIAL", "SUPPORTING", name="mapping_relationship")


def upgrade() -> None:
    bind = op.get_bind()
    scope_status.create(bind, checkfirst=True)
    mapping_relationship.create(bind, checkfirst=True)

    op.create_table(
        "frameworks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False, unique=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("publisher", sa.String(length=120), nullable=False),
        sa.Column("scope_status", scope_status, nullable=False),
        sa.Column("scope_note", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "framework_controls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "framework_id",
            sa.Integer(),
            sa.ForeignKey("frameworks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("control_ref", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("group_ref", sa.String(length=16), nullable=False),
        sa.Column("group_title", sa.String(length=120), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("in_scope", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("scope_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("framework_id", "control_ref", name="uq_framework_control_ref"),
    )
    op.create_index("ix_framework_controls_group", "framework_controls", ["framework_id", "group_ref"])

    op.create_table(
        "control_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "source_control_id",
            sa.Integer(),
            sa.ForeignKey("framework_controls.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_control_id",
            sa.Integer(),
            sa.ForeignKey("framework_controls.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relationship_type", mapping_relationship, nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source_control_id", "target_control_id", name="uq_control_mapping_pair"),
    )
    op.create_index("ix_control_mappings_source", "control_mappings", ["source_control_id"])


def downgrade() -> None:
    op.drop_index("ix_control_mappings_source", table_name="control_mappings")
    op.drop_table("control_mappings")
    op.drop_index("ix_framework_controls_group", table_name="framework_controls")
    op.drop_table("framework_controls")
    op.drop_table("frameworks")

    bind = op.get_bind()
    mapping_relationship.drop(bind, checkfirst=True)
    scope_status.drop(bind, checkfirst=True)
