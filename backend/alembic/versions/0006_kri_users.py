"""Users and roles, KRI definitions and measurements, remediation raised date.

Revision ID: 0006
Revises: 0005
Create Date: Phase 6
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = sa.Enum("AUDITOR", "ISMS_MANAGER", "ADMIN", name="user_role")
kri_unit = sa.Enum("PERCENT", "COUNT", "DAYS", name="kri_unit")
kri_direction = sa.Enum("HIGHER_IS_BETTER", "LOWER_IS_BETTER", name="kri_direction")
measurement_frequency = sa.Enum(
    "MONTHLY", "QUARTERLY", "ANNUAL", name="measurement_frequency"
)

_ENUMS = (user_role, kri_unit, kri_direction, measurement_frequency)


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
    bind = op.get_bind()
    for enum in _ENUMS:
        enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=160), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
    )

    op.create_table(
        "kri_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kri_ref", sa.String(length=24), nullable=False, unique=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("formula_description", sa.Text(), nullable=False),
        sa.Column("data_source", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("unit", kri_unit, nullable=False),
        sa.Column("direction", kri_direction, nullable=False),
        sa.Column("green_threshold", sa.Float(), nullable=False),
        sa.Column("amber_threshold", sa.Float(), nullable=False),
        sa.Column("owner_role", sa.String(length=120), nullable=False),
        sa.Column("measurement_frequency", measurement_frequency, nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        *_timestamps(),
        # An indicator with no formula is a number nobody can reproduce.
        sa.CheckConstraint(
            "length(trim(formula_description)) > 0", name="ck_kri_formula_present"
        ),
    )

    op.create_table(
        "kri_measurements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "kri_id", sa.Integer(), sa.ForeignKey("kri_definitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period_end", sa.Date(), nullable=False),
        # Nullable on purpose: a period with nothing to measure is NO_DATA, which is a
        # different statement from zero.
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("kri_id", "period_end", name="uq_kri_period"),
    )

    op.add_column("remediation_items", sa.Column("raised_date", sa.Date(), nullable=True))
    with op.batch_alter_table("remediation_items") as batch:
        batch.create_check_constraint(
            "ck_remediation_raised_before_completed",
            "raised_date IS NULL OR completed_date IS NULL OR completed_date >= raised_date",
        )


def downgrade() -> None:
    with op.batch_alter_table("remediation_items") as batch:
        batch.drop_constraint("ck_remediation_raised_before_completed", type_="check")
    op.drop_column("remediation_items", "raised_date")
    op.drop_table("kri_measurements")
    op.drop_table("kri_definitions")
    op.drop_table("users")

    bind = op.get_bind()
    for enum in reversed(_ENUMS):
        enum.drop(bind, checkfirst=True)
