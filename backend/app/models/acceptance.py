"""Approval authority and retained acceptance decisions."""
from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AcceptanceAuthority(Base):
    __tablename__ = "acceptance_authorities"
    __table_args__ = (UniqueConstraint("user_id", "business_role", name="uq_acceptance_authority"),
        CheckConstraint("length(trim(business_role)) > 0 AND length(trim(grant_reason)) > 0", name="ck_authority_reason"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    business_role: Mapped[str] = mapped_column(String(120))
    grant_reason: Mapped[str] = mapped_column(Text)
    granted_by: Mapped[str] = mapped_column(String(64))
    expires_on: Mapped[date] = mapped_column(Date)

class AcceptanceDecision(Base):
    __tablename__ = "acceptance_decisions"
    __table_args__ = (
        CheckConstraint("source IN ('AUTHENTICATED', 'SAMPLE_AUTHORED')", name="ck_acceptance_source"),
        CheckConstraint("decision IN ('APPROVED', 'REJECTED', 'WITHDRAWN', 'EXPIRED')", name="ck_acceptance_decision"),
        CheckConstraint("length(trim(note)) > 0 AND length(trim(actor)) > 0", name="ck_acceptance_note"),
        CheckConstraint("decision != 'APPROVED' OR (approval_date IS NOT NULL AND expiry_date > approval_date)", name="ck_signed_acceptance_dates"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exception_id: Mapped[int] = mapped_column(ForeignKey("risk_exceptions.id", ondelete="RESTRICT"))
    record_digest: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(24))
    actor: Mapped[str] = mapped_column(String(120))
    business_role: Mapped[str] = mapped_column(String(120))
    note: Mapped[str] = mapped_column(Text)
    approval_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date] = mapped_column(Date)
