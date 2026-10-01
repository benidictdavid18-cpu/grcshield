"""Controlled documents, retained revisions and version-specific acknowledgements."""
from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ControlledDocument(Base):
    __tablename__="controlled_documents"
    __table_args__=(
        CheckConstraint("classification IN ('PUBLIC','INTERNAL','CONFIDENTIAL','RESTRICTED')",name="ck_document_classification"),
        CheckConstraint("source_kind IN ('INTERNAL','EXTERNAL')",name="ck_document_source_kind"),
        CheckConstraint("length(trim(title))>0 AND length(trim(owner))>0 AND length(trim(distribution))>0",name="ck_document_required"),
        CheckConstraint("source_kind != 'EXTERNAL' OR (external_source IS NOT NULL AND length(trim(external_source))>0)",name="ck_document_external_source"),
    )
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    document_ref: Mapped[str]=mapped_column(String(32),unique=True)
    title: Mapped[str]=mapped_column(String(240))
    owner: Mapped[str]=mapped_column(String(160))
    classification: Mapped[str]=mapped_column(String(16))
    source_kind: Mapped[str]=mapped_column(String(16))
    external_source: Mapped[str | None]=mapped_column(Text)
    distribution: Mapped[str]=mapped_column(Text)
    review_date: Mapped[date]=mapped_column(Date)

class DocumentRevision(Base):
    __tablename__="document_revisions"
    __table_args__=(
        UniqueConstraint("document_id","version",name="uq_document_version"),
        Index("uq_document_published","document_id",unique=True,sqlite_where=text("status = 'PUBLISHED'"),postgresql_where=text("status = 'PUBLISHED'")),
        CheckConstraint("status IN ('DRAFT','APPROVED','PUBLISHED','SUPERSEDED','WITHDRAWN')",name="ck_document_revision_status"),
        CheckConstraint("length(trim(content))>0 AND length(trim(change_note))>0 AND length(content_digest)=64",name="ck_document_revision_content"),
        CheckConstraint("status = 'DRAFT' OR (approved_by IS NOT NULL AND approved_on IS NOT NULL AND approval_note IS NOT NULL AND length(trim(approval_note))>0 AND approval_note NOT LIKE '%TODO AUTHOR:BENNY%' AND content NOT LIKE '%TODO AUTHOR:BENNY%')",name="ck_document_revision_approval"),
        CheckConstraint("status NOT IN ('PUBLISHED','SUPERSEDED','WITHDRAWN') OR published_on IS NOT NULL",name="ck_document_revision_publication"),
    )
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    document_id: Mapped[int]=mapped_column(ForeignKey("controlled_documents.id",ondelete="RESTRICT"))
    version: Mapped[str]=mapped_column(String(32))
    content: Mapped[str]=mapped_column(Text)
    content_digest: Mapped[str]=mapped_column(String(64))
    change_note: Mapped[str]=mapped_column(Text)
    author: Mapped[str]=mapped_column(String(120))
    status: Mapped[str]=mapped_column(String(16),default="DRAFT")
    evidence_id: Mapped[int | None]=mapped_column(ForeignKey("evidence.id",ondelete="RESTRICT"))
    approved_by: Mapped[str | None]=mapped_column(String(64))
    approved_on: Mapped[date | None]=mapped_column(Date)
    approval_note: Mapped[str | None]=mapped_column(Text)
    published_on: Mapped[date | None]=mapped_column(Date)
    withdrawal_note: Mapped[str | None]=mapped_column(Text)

class DocumentAcknowledgement(Base):
    __tablename__="document_acknowledgements"
    __table_args__=(UniqueConstraint("revision_id","username",name="uq_document_acknowledgement"),)
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    revision_id: Mapped[int]=mapped_column(ForeignKey("document_revisions.id",ondelete="RESTRICT"))
    username: Mapped[str]=mapped_column(String(64))
