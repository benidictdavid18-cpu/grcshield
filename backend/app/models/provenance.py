"""Proof and reassessment records; no automatic compliance decisions."""
from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TestDisposition(Base):
    __tablename__ = "test_dispositions"
    __table_args__ = (
        CheckConstraint("kind IN ('SUPERSEDED', 'WITHDRAWN')", name="ck_disposition_kind"),
        CheckConstraint("length(trim(reason)) > 0", name="ck_disposition_reason"),
        CheckConstraint("(kind = 'SUPERSEDED' AND replacement_id IS NOT NULL AND replacement_id != test_id) OR (kind = 'WITHDRAWN' AND replacement_id IS NULL)", name="ck_disposition_replacement"),
    )
    test_id: Mapped[int] = mapped_column(ForeignKey("control_tests.id", ondelete="RESTRICT"), primary_key=True)
    replacement_id: Mapped[int | None] = mapped_column(ForeignKey("control_tests.id", ondelete="RESTRICT"))
    kind: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(64))

class Reassessment(Base):
    __tablename__ = "reassessments"
    __table_args__ = (
        UniqueConstraint("trigger_test_id", "record_type", "record_ref", name="uq_reassessment_trigger"),
        CheckConstraint("status IN ('OPEN', 'RESOLVED')", name="ck_reassessment_status"),
        CheckConstraint("length(trim(owner)) > 0", name="ck_reassessment_owner"),
        CheckConstraint("status != 'RESOLVED' OR (resolution IS NOT NULL AND length(trim(resolution)) > 0 AND evidence_id IS NOT NULL AND resolved_by IS NOT NULL)", name="ck_reassessment_resolution"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trigger_test_id: Mapped[int] = mapped_column(ForeignKey("control_tests.id", ondelete="RESTRICT"))
    record_type: Mapped[str] = mapped_column(String(24))
    record_ref: Mapped[str] = mapped_column(String(32))
    owner: Mapped[str] = mapped_column(String(160))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="OPEN", server_default="OPEN")
    resolution: Mapped[str | None] = mapped_column(Text)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id", ondelete="RESTRICT"))
    resolved_by: Mapped[str | None] = mapped_column(String(64))
