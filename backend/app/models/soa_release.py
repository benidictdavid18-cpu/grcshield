"""Immutable SoA snapshots and attributable management sign-off."""
from datetime import datetime

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SoARelease(Base):
    __tablename__="soa_releases"
    __table_args__=(
        CheckConstraint("status IN ('DRAFT','APPROVED')",name="ck_soa_release_status"),
        CheckConstraint("entry_count=93 AND length(content_digest)=64 AND length(trim(change_note))>0",name="ck_soa_release_content"),
        CheckConstraint("status != 'APPROVED' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL AND approval_note IS NOT NULL AND length(trim(approval_note))>0 AND approval_note NOT LIKE '%TODO AUTHOR:BENNY%' AND change_note NOT LIKE '%TODO AUTHOR:BENNY%')",name="ck_soa_release_approval"),
    )
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    version: Mapped[str]=mapped_column(String(32),unique=True)
    status: Mapped[str]=mapped_column(String(16),default="DRAFT")
    entries: Mapped[list]=mapped_column(JSON)
    entry_count: Mapped[int]=mapped_column(Integer)
    content_digest: Mapped[str]=mapped_column(String(64))
    change_note: Mapped[str]=mapped_column(Text)
    prepared_by: Mapped[str]=mapped_column(String(120))
    evidence_warnings: Mapped[list]=mapped_column(JSON)
    evidence_limitations_acknowledged: Mapped[bool]=mapped_column(Boolean,default=False)
    approved_by: Mapped[str | None]=mapped_column(String(64))
    approved_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True))
    approval_note: Mapped[str | None]=mapped_column(Text)
