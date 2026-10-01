"""Bounded artifact bytes are transactional with their metadata and retention record."""
from datetime import date

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EvidenceAttachment(Base):
    __tablename__="evidence_attachments"
    __table_args__=(
        UniqueConstraint("evidence_id","version",name="uq_evidence_attachment_version"),
        CheckConstraint("byte_size > 0 AND byte_size <= 8388608 AND length(sha256)=64",name="ck_attachment_size_hash"),
        CheckConstraint("access_scope IN ('REGISTER_READERS','MAINTAINERS')",name="ck_attachment_access"),
        CheckConstraint("content_type IN ('application/pdf','image/png','image/jpeg','text/plain','text/csv','application/json')",name="ck_attachment_type"),
        CheckConstraint("length(trim(filename))>0 AND length(trim(version))>0 AND length(trim(source))>0 AND length(trim(retention_reason))>0",name="ck_attachment_required"),
        CheckConstraint("retention_until >= uploaded_on",name="ck_attachment_retention"),
        CheckConstraint("(purged_on IS NULL AND content_data IS NOT NULL AND length(content_data)=byte_size) OR (purged_on IS NOT NULL AND content_data IS NULL AND purged_by IS NOT NULL AND purge_reason IS NOT NULL AND length(trim(purge_reason))>0 AND NOT legal_hold AND purged_on>=retention_until)",name="ck_attachment_purge"),
    )
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    evidence_id: Mapped[int]=mapped_column(ForeignKey("evidence.id",ondelete="RESTRICT"))
    version: Mapped[str]=mapped_column(String(32))
    filename: Mapped[str]=mapped_column(String(240))
    content_type: Mapped[str]=mapped_column(String(64))
    byte_size: Mapped[int]=mapped_column(Integer)
    sha256: Mapped[str]=mapped_column(String(64))
    content_data: Mapped[bytes | None]=mapped_column(LargeBinary,deferred=True)
    source: Mapped[str]=mapped_column(Text)
    uploaded_by: Mapped[str]=mapped_column(String(64))
    uploaded_on: Mapped[date]=mapped_column(Date)
    access_scope: Mapped[str]=mapped_column(String(24))
    retention_until: Mapped[date]=mapped_column(Date)
    retention_reason: Mapped[str]=mapped_column(Text)
    legal_hold: Mapped[bool]=mapped_column(Boolean,default=False)
    purged_on: Mapped[date | None]=mapped_column(Date)
    purged_by: Mapped[str | None]=mapped_column(String(64))
    purge_reason: Mapped[str | None]=mapped_column(Text)
