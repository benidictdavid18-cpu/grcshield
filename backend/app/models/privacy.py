"""Asset register, risk acceptance, GDPR records and business impact analysis.

The asset register arrives here because RoPA, DPIA and BIA all need something concrete
to point at. "Customer data" is not an asset; "the production RDS cluster in eu-west-1
holding cardholder references" is.
"""

from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.risk import Control, Risk
from app.services.privacy_continuity import (
    AssetType,
    Classification,
    DpiaOutcome,
    ExceptionStatus,
    LawfulBasis,
    ResidualRiskLevel,
    TransferSafeguard,
    exception_state,
)


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_ref: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType, name="asset_type"), nullable=False)
    classification: Mapped[Classification] = mapped_column(
        Enum(Classification, name="asset_classification"), nullable=False
    )
    owner_role: Mapped[str] = mapped_column(String(120), nullable=False)
    hosting_location: Mapped[str] = mapped_column(String(160), nullable=False)
    holds_personal_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class RiskException(Base):
    """A formal, time-boxed acceptance of a risk.

    The expiry date is the whole point. An acceptance without one is a permanent
    decision disguised as a temporary one, and the conditions that made it reasonable
    will change without anybody revisiting it.
    """

    __tablename__ = "risk_exceptions"
    __table_args__ = (Index("ix_risk_exceptions_expiry", "expiry_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exception_ref: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    risk_id: Mapped[int] = mapped_column(ForeignKey("risks.id", ondelete="CASCADE"), nullable=False)

    requested_by: Mapped[str] = mapped_column(String(120), nullable=False)
    business_justification: Mapped[str] = mapped_column(Text, nullable=False)
    compensating_controls: Mapped[str] = mapped_column(Text, nullable=False)

    # Must be the risk owner or a named escalation approver, and never the security
    # function. Enforced in app.services.privacy_continuity.validate_exception.
    approver_role: Mapped[str] = mapped_column(String(120), nullable=False)
    approval_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    review_trigger: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ExceptionStatus] = mapped_column(
        Enum(ExceptionStatus, name="exception_status"), nullable=False
    )
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    risk: Mapped[Risk] = relationship()

    def state(self, as_of: date) -> str:
        return exception_state(self.expiry_date, self.status, as_of)

    def days_remaining(self, as_of: date) -> int:
        return (self.expiry_date - as_of).days


class RopaAssetLink(Base):
    __tablename__ = "ropa_asset_links"
    __table_args__ = (UniqueConstraint("ropa_id", "asset_id", name="uq_ropa_asset"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ropa_id: Mapped[int] = mapped_column(
        ForeignKey("ropa_entries.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)

    ropa: Mapped["RopaEntry"] = relationship(back_populates="asset_links")
    asset: Mapped[Asset] = relationship()


class RopaRiskLink(Base):
    __tablename__ = "ropa_risk_links"
    __table_args__ = (UniqueConstraint("ropa_id", "risk_id", name="uq_ropa_risk"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ropa_id: Mapped[int] = mapped_column(
        ForeignKey("ropa_entries.id", ondelete="CASCADE"), nullable=False
    )
    risk_id: Mapped[int] = mapped_column(ForeignKey("risks.id", ondelete="CASCADE"), nullable=False)

    ropa: Mapped["RopaEntry"] = relationship(back_populates="risk_links")
    risk: Mapped[Risk] = relationship()


class RopaControlLink(Base):
    """Article 30(1)(g) — the technical and organisational security measures."""

    __tablename__ = "ropa_control_links"
    __table_args__ = (UniqueConstraint("ropa_id", "control_id", name="uq_ropa_control"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ropa_id: Mapped[int] = mapped_column(
        ForeignKey("ropa_entries.id", ondelete="CASCADE"), nullable=False
    )
    control_id: Mapped[int] = mapped_column(
        ForeignKey("controls.id", ondelete="CASCADE"), nullable=False
    )

    ropa: Mapped["RopaEntry"] = relationship(back_populates="control_links")
    control: Mapped[Control] = relationship()


class RopaEntry(Base):
    """GDPR Article 30 — Record of Processing Activities."""

    __tablename__ = "ropa_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ropa_ref: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    processing_activity: Mapped[str] = mapped_column(String(240), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    lawful_basis: Mapped[LawfulBasis] = mapped_column(
        Enum(LawfulBasis, name="lawful_basis"), nullable=False
    )
    legitimate_interests_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_subject_categories: Mapped[str] = mapped_column(Text, nullable=False)
    personal_data_categories: Mapped[str] = mapped_column(Text, nullable=False)
    special_category_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recipients: Mapped[str] = mapped_column(Text, nullable=False)

    transfers_outside_eea: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    transfer_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    transfer_safeguard: Mapped[TransferSafeguard] = mapped_column(
        Enum(TransferSafeguard, name="transfer_safeguard"), nullable=False
    )

    retention_period: Mapped[str] = mapped_column(Text, nullable=False)
    security_measures_summary: Mapped[str] = mapped_column(Text, nullable=False)
    controller_role: Mapped[str] = mapped_column(String(120), nullable=False)
    owner_role: Mapped[str] = mapped_column(String(120), nullable=False)
    last_reviewed: Mapped[date | None] = mapped_column(Date, nullable=True)

    asset_links: Mapped[list[RopaAssetLink]] = relationship(
        back_populates="ropa", cascade="all, delete-orphan"
    )
    risk_links: Mapped[list[RopaRiskLink]] = relationship(
        back_populates="ropa", cascade="all, delete-orphan"
    )
    control_links: Mapped[list[RopaControlLink]] = relationship(
        back_populates="ropa", cascade="all, delete-orphan"
    )

    @property
    def linked_assets(self) -> list[Asset]:
        return sorted((link.asset for link in self.asset_links), key=lambda a: a.asset_ref)

    @property
    def linked_risks(self) -> list[Risk]:
        return sorted((link.risk for link in self.risk_links), key=lambda r: r.risk_ref)

    @property
    def linked_controls(self) -> list[Control]:
        return sorted((link.control for link in self.control_links), key=lambda c: c.control_id)


class DpiaAssetLink(Base):
    __tablename__ = "dpia_asset_links"
    __table_args__ = (UniqueConstraint("dpia_id", "asset_id", name="uq_dpia_asset"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dpia_id: Mapped[int] = mapped_column(ForeignKey("dpias.id", ondelete="CASCADE"), nullable=False)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)

    dpia: Mapped["Dpia"] = relationship(back_populates="asset_links")
    asset: Mapped[Asset] = relationship()


class DpiaRiskLink(Base):
    __tablename__ = "dpia_risk_links"
    __table_args__ = (UniqueConstraint("dpia_id", "risk_id", name="uq_dpia_risk"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dpia_id: Mapped[int] = mapped_column(ForeignKey("dpias.id", ondelete="CASCADE"), nullable=False)
    risk_id: Mapped[int] = mapped_column(ForeignKey("risks.id", ondelete="CASCADE"), nullable=False)

    dpia: Mapped["Dpia"] = relationship(back_populates="risk_links")
    risk: Mapped[Risk] = relationship()


class Dpia(Base):
    """GDPR Article 35 — Data Protection Impact Assessment."""

    __tablename__ = "dpias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dpia_ref: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    ropa_id: Mapped[int | None] = mapped_column(
        ForeignKey("ropa_entries.id", ondelete="SET NULL"), nullable=True
    )

    trigger_reason: Mapped[str] = mapped_column(Text, nullable=False)
    processing_description: Mapped[str] = mapped_column(Text, nullable=False)
    necessity_and_proportionality: Mapped[str] = mapped_column(Text, nullable=False)
    risks_to_data_subjects: Mapped[str] = mapped_column(Text, nullable=False)
    mitigating_measures: Mapped[str] = mapped_column(Text, nullable=False)
    residual_risk: Mapped[ResidualRiskLevel] = mapped_column(
        Enum(ResidualRiskLevel, name="dpia_residual_risk"), nullable=False
    )
    residual_risk_note: Mapped[str] = mapped_column(Text, nullable=False)

    dpo_consulted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dpo_advice: Mapped[str | None] = mapped_column(Text, nullable=True)
    supervisory_authority_consulted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    data_subjects_consulted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    outcome: Mapped[DpiaOutcome] = mapped_column(
        Enum(DpiaOutcome, name="dpia_outcome"), nullable=False
    )
    assessed_by: Mapped[str] = mapped_column(String(120), nullable=False)
    assessment_date: Mapped[date] = mapped_column(Date, nullable=False)
    review_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    ropa: Mapped[RopaEntry | None] = relationship()
    asset_links: Mapped[list[DpiaAssetLink]] = relationship(
        back_populates="dpia", cascade="all, delete-orphan"
    )
    risk_links: Mapped[list[DpiaRiskLink]] = relationship(
        back_populates="dpia", cascade="all, delete-orphan"
    )

    @property
    def linked_assets(self) -> list[Asset]:
        return sorted((link.asset for link in self.asset_links), key=lambda a: a.asset_ref)

    @property
    def linked_risks(self) -> list[Risk]:
        return sorted((link.risk for link in self.risk_links), key=lambda r: r.risk_ref)

    def review_overdue(self, as_of: date) -> bool:
        return self.review_date is not None and self.review_date < as_of


class BiaAssetLink(Base):
    __tablename__ = "bia_asset_links"
    __table_args__ = (UniqueConstraint("bia_id", "asset_id", name="uq_bia_asset"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bia_id: Mapped[int] = mapped_column(
        ForeignKey("business_impact_analyses.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)

    bia: Mapped["BusinessImpactAnalysis"] = relationship(back_populates="asset_links")
    asset: Mapped[Asset] = relationship()


class BiaControlLink(Base):
    __tablename__ = "bia_control_links"
    __table_args__ = (UniqueConstraint("bia_id", "control_id", name="uq_bia_control"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bia_id: Mapped[int] = mapped_column(
        ForeignKey("business_impact_analyses.id", ondelete="CASCADE"), nullable=False
    )
    control_id: Mapped[int] = mapped_column(
        ForeignKey("controls.id", ondelete="CASCADE"), nullable=False
    )

    bia: Mapped["BusinessImpactAnalysis"] = relationship(back_populates="control_links")
    control: Mapped[Control] = relationship()


class BiaRiskLink(Base):
    __tablename__ = "bia_risk_links"
    __table_args__ = (UniqueConstraint("bia_id", "risk_id", name="uq_bia_risk"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bia_id: Mapped[int] = mapped_column(
        ForeignKey("business_impact_analyses.id", ondelete="CASCADE"), nullable=False
    )
    risk_id: Mapped[int] = mapped_column(ForeignKey("risks.id", ondelete="CASCADE"), nullable=False)

    bia: Mapped["BusinessImpactAnalysis"] = relationship(back_populates="risk_links")
    risk: Mapped[Risk] = relationship()


class BusinessImpactAnalysis(Base):
    """Business impact analysis for one process.

    RTO and RPO are recovery *targets*; MTPD is the business's tolerance. The
    relationship between them is the only arithmetic in a BIA that can be wrong on its
    face, and it is enforced.
    """

    __tablename__ = "business_impact_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bia_ref: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    process_name: Mapped[str] = mapped_column(String(240), nullable=False)
    process_description: Mapped[str] = mapped_column(Text, nullable=False)
    owner_role: Mapped[str] = mapped_column(String(120), nullable=False)

    rto_hours: Mapped[float] = mapped_column(Float, nullable=False)
    rpo_hours: Mapped[float] = mapped_column(Float, nullable=False)
    mtpd_hours: Mapped[float] = mapped_column(Float, nullable=False)

    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="GBP")
    impact_1h: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    impact_24h: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    impact_1w: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    impact_note: Mapped[str] = mapped_column(Text, nullable=False)

    workaround: Mapped[str] = mapped_column(Text, nullable=False)
    recovery_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_reviewed: Mapped[date | None] = mapped_column(Date, nullable=True)

    asset_links: Mapped[list[BiaAssetLink]] = relationship(
        back_populates="bia", cascade="all, delete-orphan"
    )
    control_links: Mapped[list[BiaControlLink]] = relationship(
        back_populates="bia", cascade="all, delete-orphan"
    )
    risk_links: Mapped[list[BiaRiskLink]] = relationship(
        back_populates="bia", cascade="all, delete-orphan"
    )

    @property
    def linked_assets(self) -> list[Asset]:
        return sorted((link.asset for link in self.asset_links), key=lambda a: a.asset_ref)

    @property
    def linked_controls(self) -> list[Control]:
        return sorted((link.control for link in self.control_links), key=lambda c: c.control_id)

    @property
    def linked_risks(self) -> list[Risk]:
        return sorted((link.risk for link in self.risk_links), key=lambda r: r.risk_ref)
