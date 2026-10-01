"""Context decisions and immutable approved scope snapshots (clauses 4.1–4.4)."""
from datetime import date

from sqlalchemy import JSON, CheckConstraint, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ContextEntry(Base):
    __tablename__ = "isms_context"
    __table_args__ = (
        CheckConstraint("kind IN ('ISSUE', 'PARTY_REQUIREMENT', 'PROCESS')", name="ck_context_kind"),
        CheckConstraint("relevance IN ('UNASSESSED', 'RELEVANT', 'NOT_RELEVANT')", name="ck_context_relevance"),
        CheckConstraint("status IN ('DRAFT', 'REVIEWED')", name="ck_context_status"),
        CheckConstraint("length(trim(owner)) > 0 AND length(trim(source)) > 0 AND length(trim(statement)) > 0", name="ck_context_required"),
        CheckConstraint("status != 'REVIEWED' OR (reviewed_by IS NOT NULL AND reviewed_on IS NOT NULL AND relevance != 'UNASSESSED' AND length(trim(decision_note)) > 0 AND decision_note NOT LIKE '%TODO AUTHOR:BENNY%' AND owner NOT LIKE '%TODO AUTHOR:BENNY%')", name="ck_context_review"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    context_ref: Mapped[str] = mapped_column(String(32), unique=True)
    kind: Mapped[str] = mapped_column(String(24))
    topic: Mapped[str] = mapped_column(String(64), default="GENERAL")
    title: Mapped[str] = mapped_column(String(240))
    statement: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(String(160))
    review_date: Mapped[date] = mapped_column(Date)
    relevance: Mapped[str] = mapped_column(String(16), default="UNASSESSED")
    decision_note: Mapped[str] = mapped_column(Text)
    risk_id: Mapped[int | None] = mapped_column(ForeignKey("risks.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    reviewed_by: Mapped[str | None] = mapped_column(String(64))
    reviewed_on: Mapped[date | None] = mapped_column(Date)

class ScopeRevision(Base):
    __tablename__ = "isms_scope_revisions"
    __table_args__ = (
        CheckConstraint("status IN ('DRAFT', 'APPROVED')", name="ck_scope_status"),
        CheckConstraint("length(trim(statement)) > 0 AND length(trim(interfaces)) > 0 AND length(trim(owner)) > 0", name="ck_scope_required"),
        CheckConstraint("status != 'APPROVED' OR (approved_by IS NOT NULL AND approved_on IS NOT NULL AND approval_note IS NOT NULL AND length(trim(approval_note)) > 0 AND approval_note NOT LIKE '%TODO AUTHOR:BENNY%')", name="ck_scope_approval"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(32), unique=True)
    statement: Mapped[str] = mapped_column(Text)
    interfaces: Mapped[str] = mapped_column(Text)
    exclusions: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(String(160))
    review_date: Mapped[date] = mapped_column(Date)
    context_snapshot: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    approved_by: Mapped[str | None] = mapped_column(String(64))
    approved_on: Mapped[date | None] = mapped_column(Date)
    approval_note: Mapped[str | None] = mapped_column(Text)
