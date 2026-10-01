"""One-time sample initialization boundary."""
from sqlalchemy import CheckConstraint, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SampleBootstrap(Base):
    __tablename__ = "sample_bootstrap"
    __table_args__ = (
        CheckConstraint("id = 1",name="ck_single_bootstrap"),
        CheckConstraint("status IN ('INITIALIZED', 'PRESERVED', 'REAPPLIED')",name="ck_bootstrap_status"),
        CheckConstraint("length(trim(reason)) > 0",name="ck_bootstrap_reason"),
    )
    id: Mapped[int] = mapped_column(Integer,primary_key=True)
    status: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str] = mapped_column(Text)
