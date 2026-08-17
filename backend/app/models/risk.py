"""Risk register, internal control library and risk appetite.

Scoring rules and their justification live in ``app.services.risk_scoring``. The models
here store what a human decided; they compute bands from those decisions but never
compute the decisions themselves.
"""

from datetime import date

from sqlalchemy import (
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.framework import FrameworkControl
from app.services.control_testing import (
    DesignEffectiveness,
    OperatingEffectiveness,
    basis_is_optimistic,
)
from app.services.risk_scoring import (
    ControlEffectivenessBasis,
    RiskBand,
    RiskCategory,
    RiskStatus,
    TreatmentDecision,
    band_for,
    basis_credits_reduction,
    exceeds_appetite,
    score,
)


class ControlAnnexALink(Base):
    """Which Annex A control(s) an internal control helps satisfy."""

    __tablename__ = "control_annex_a_links"
    __table_args__ = (
        UniqueConstraint("control_id", "framework_control_id", name="uq_control_annex_a"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    control_id: Mapped[int] = mapped_column(
        ForeignKey("controls.id", ondelete="CASCADE"), nullable=False
    )
    framework_control_id: Mapped[int] = mapped_column(
        ForeignKey("framework_controls.id", ondelete="CASCADE"), nullable=False
    )

    control: Mapped["Control"] = relationship(back_populates="annex_a_links")
    framework_control: Mapped[FrameworkControl] = relationship()


class Control(Base):
    """An internal control FinFlow actually operates.

    Distinct from ``FrameworkControl``, which is a catalogue entry in a published
    standard. Annex A says "secure authentication"; the internal library says "MFA is
    enforced for all Okta users, owned by the Head of Engineering". Conflating the two
    is what produces a control library that cannot be tested.
    """

    __tablename__ = "controls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    control_id: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    control_family: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_role: Mapped[str] = mapped_column(String(120), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Two independent questions, deliberately not collapsed into one rating. See
    # app.services.control_testing for why, and for the rule that a deficient design
    # caps operating effectiveness below EFFECTIVE.
    design_effectiveness: Mapped[DesignEffectiveness] = mapped_column(
        Enum(DesignEffectiveness, name="design_effectiveness"),
        nullable=False,
        default=DesignEffectiveness.NOT_ASSESSED,
    )
    operating_effectiveness: Mapped[OperatingEffectiveness] = mapped_column(
        Enum(OperatingEffectiveness, name="operating_effectiveness"),
        nullable=False,
        default=OperatingEffectiveness.NOT_TESTED,
    )
    effectiveness_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_tested: Mapped[date | None] = mapped_column(Date, nullable=True)

    annex_a_links: Mapped[list[ControlAnnexALink]] = relationship(
        back_populates="control", cascade="all, delete-orphan"
    )
    risk_links: Mapped[list["RiskControl"]] = relationship(
        back_populates="control", cascade="all, delete-orphan"
    )

    @property
    def annex_a_refs(self) -> list[str]:
        return sorted(link.framework_control.control_ref for link in self.annex_a_links)


class RiskAppetiteThreshold(Base):
    """Per-category appetite.

    A single organisation-wide appetite says the business tolerates the same exposure
    to a privacy breach as to a laptop running an old OS. It does not, and pretending
    otherwise makes the appetite line meaningless. Each category therefore carries its
    own ceiling and its own approver -- because appetite is set by whoever answers for
    the consequence, not by the security team.
    """

    __tablename__ = "risk_appetite_thresholds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[RiskCategory] = mapped_column(
        Enum(RiskCategory, name="risk_category"), unique=True, nullable=False
    )
    max_acceptable_band: Mapped[RiskBand] = mapped_column(
        Enum(RiskBand, name="risk_band"), nullable=False
    )
    approver_role: Mapped[str] = mapped_column(String(120), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    last_reviewed: Mapped[date | None] = mapped_column(Date, nullable=True)


class RiskControl(Base):
    """A control applied to a risk, with the basis on which it may be credited."""

    __tablename__ = "risk_controls"
    __table_args__ = (
        UniqueConstraint("risk_id", "control_id", name="uq_risk_control"),
        Index("ix_risk_controls_risk", "risk_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    risk_id: Mapped[int] = mapped_column(ForeignKey("risks.id", ondelete="CASCADE"), nullable=False)
    control_id: Mapped[int] = mapped_column(
        ForeignKey("controls.id", ondelete="CASCADE"), nullable=False
    )
    effectiveness_basis: Mapped[ControlEffectivenessBasis] = mapped_column(
        Enum(ControlEffectivenessBasis, name="control_effectiveness_basis"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    risk: Mapped["Risk"] = relationship(back_populates="control_links")
    control: Mapped[Control] = relationship(back_populates="risk_links")

    @property
    def credits_reduction(self) -> bool:
        return basis_credits_reduction(self.effectiveness_basis)

    @property
    def basis_is_optimistic(self) -> bool:
        """The recorded basis claims more than the control library supports.

        Surfaced rather than blocked: an analyst may legitimately be scoping to a
        population the exceptions did not touch. Visible beats silent.
        """
        return basis_is_optimistic(
            self.effectiveness_basis,
            self.control.operating_effectiveness,
            self.control.design_effectiveness,
        )


class Risk(Base):
    __tablename__ = "risks"
    __table_args__ = (Index("ix_risks_category", "category"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    risk_ref: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[RiskCategory] = mapped_column(
        Enum(RiskCategory, name="risk_category"), nullable=False
    )
    owner_role: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[RiskStatus] = mapped_column(
        Enum(RiskStatus, name="risk_status"), nullable=False, default=RiskStatus.OPEN
    )

    # The analysis chain that produced the inherent score, kept as separate fields so
    # the register can be reviewed rather than just read.
    asset: Mapped[str] = mapped_column(String(240), nullable=False)
    threat: Mapped[str] = mapped_column(Text, nullable=False)
    vulnerability: Mapped[str] = mapped_column(Text, nullable=False)

    inherent_likelihood: Mapped[int] = mapped_column(Integer, nullable=False)
    inherent_impact: Mapped[int] = mapped_column(Integer, nullable=False)

    # Scored directly by the analyst. Never derived from the inherent score.
    residual_likelihood: Mapped[int] = mapped_column(Integer, nullable=False)
    residual_impact: Mapped[int] = mapped_column(Integer, nullable=False)
    residual_justification: Mapped[str] = mapped_column(Text, nullable=False)

    treatment_decision: Mapped[TreatmentDecision] = mapped_column(
        Enum(TreatmentDecision, name="treatment_decision"), nullable=False
    )
    treatment_summary: Mapped[str] = mapped_column(Text, nullable=False)

    date_identified: Mapped[date] = mapped_column(Date, nullable=False)
    last_reviewed: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_review: Mapped[date | None] = mapped_column(Date, nullable=True)

    control_links: Mapped[list[RiskControl]] = relationship(
        back_populates="risk", cascade="all, delete-orphan"
    )

    # --- Derived values. Bands are computed; judgments are not. ------------
    @property
    def inherent_score(self) -> int:
        return score(self.inherent_likelihood, self.inherent_impact)

    @property
    def inherent_band(self) -> RiskBand:
        return band_for(self.inherent_score)

    @property
    def residual_score(self) -> int:
        return score(self.residual_likelihood, self.residual_impact)

    @property
    def residual_band(self) -> RiskBand:
        return band_for(self.residual_score)

    @property
    def claims_reduction(self) -> bool:
        return self.residual_score < self.inherent_score

    @property
    def crediting_control_links(self) -> list[RiskControl]:
        return [link for link in self.control_links if link.credits_reduction]

    @property
    def uncredited_control_links(self) -> list[RiskControl]:
        return [link for link in self.control_links if not link.credits_reduction]

    def exceeds(self, threshold: RiskAppetiteThreshold | None) -> bool | None:
        """None when no threshold is defined for the category -- not False.

        A missing appetite is an unanswered governance question, and rendering it as
        "within appetite" would answer it in the reassuring direction.
        """
        if threshold is None:
            return None
        return exceeds_appetite(self.residual_band, threshold.max_acceptable_band)
