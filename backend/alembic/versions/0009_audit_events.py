"""The application's audit trail.

One append-only table recording every mutation made through the API: who, when, which
record, the changed fields before and after. It adds no column and no constraint to any
existing table; the trail is written alongside a change, not into it.

``action`` is a plain string rather than a native enum. Migration 0008 is the reason:
adding a value to a PostgreSQL enum type is a dialect-specific migration that
autogenerate cannot detect, and a new kind of mutation should not cost one.

Revision ID: 0009
Revises: 0008
Create Date: Audit trail
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        # Text, not a foreign key: the trail must outlive the account it names.
        sa.Column("actor_username", sa.String(64), nullable=False),
        sa.Column("actor_role", sa.String(32), nullable=False),
        sa.Column("action", sa.String(48), nullable=False),
        sa.Column("record_type", sa.String(32), nullable=False),
        sa.Column("record_ref", sa.String(32), nullable=False),
        sa.Column("before", sa.JSON(), nullable=True),
        sa.Column("after", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_audit_events_record", "audit_events", ["record_type", "record_ref"])
    op.create_index("ix_audit_events_actor", "audit_events", ["actor_username"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_actor", table_name="audit_events")
    op.drop_index("ix_audit_events_record", table_name="audit_events")
    op.drop_table("audit_events")
