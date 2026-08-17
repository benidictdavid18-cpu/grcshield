"""Framework registry and control library.

Three tables:
    frameworks          -- which standards GRCShield tracks, and at what depth
    framework_controls  -- the control/criterion catalogue for each framework
    control_mappings    -- ISO -> SOC 2 crosswalk

A framework's ``scope_status`` is the Phase 1 scope decision, and it is data rather
than code so the UI can explain the difference between "we assess this" and "we
have not assessed this yet" without hard-coding either.
"""

import enum

from sqlalchemy import (
    Boolean,
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


class ScopeStatus(str, enum.Enum):
    """How deeply GRCShield assesses a framework."""

    PRIMARY = "PRIMARY"
    """Fully populated and independently assessed. Drives the SoA."""

    SECONDARY = "SECONDARY"
    """Not assessed directly. Coverage is derived by mapping from the primary."""

    ROADMAP = "ROADMAP"
    """Catalogued but not yet assessed. Read-only in the UI."""


class MappingRelationship(str, enum.Enum):
    EQUIVALENT = "EQUIVALENT"
    PARTIAL = "PARTIAL"
    SUPPORTING = "SUPPORTING"


class Framework(Base):
    __tablename__ = "frameworks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    publisher: Mapped[str] = mapped_column(String(120), nullable=False)
    scope_status: Mapped[ScopeStatus] = mapped_column(
        Enum(ScopeStatus, name="scope_status"), nullable=False
    )
    scope_note: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    controls: Mapped[list["FrameworkControl"]] = relationship(
        back_populates="framework", cascade="all, delete-orphan", order_by="FrameworkControl.sort_order"
    )


class FrameworkControl(Base):
    """One control (ISO Annex A) or one criterion (SOC 2 TSC)."""

    __tablename__ = "framework_controls"
    __table_args__ = (
        UniqueConstraint("framework_id", "control_ref", name="uq_framework_control_ref"),
        Index("ix_framework_controls_group", "framework_id", "group_ref"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    framework_id: Mapped[int] = mapped_column(ForeignKey("frameworks.id", ondelete="CASCADE"), nullable=False)
    control_ref: Mapped[str] = mapped_column(String(24), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)

    # ISO: "A.5".."A.8". SOC 2: "CC1".."CC9", "A1", "C1", "PI1", "P1".."P8".
    group_ref: Mapped[str] = mapped_column(String(16), nullable=False)
    group_title: Mapped[str] = mapped_column(String(120), nullable=False)

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Provisional scope decision. The Statement of Applicability (Phase 3) is the
    # authoritative record; this flag exists so mappings and metrics have something
    # sane to work from before the SoA is built.
    in_scope: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    scope_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    framework: Mapped[Framework] = relationship(back_populates="controls")

    mapped_to: Mapped[list["ControlMapping"]] = relationship(
        back_populates="source_control",
        foreign_keys="ControlMapping.source_control_id",
        cascade="all, delete-orphan",
    )
    mapped_from: Mapped[list["ControlMapping"]] = relationship(
        back_populates="target_control",
        foreign_keys="ControlMapping.target_control_id",
        cascade="all, delete-orphan",
    )


class ControlMapping(Base):
    """Crosswalk from a primary-framework control to a secondary-framework criterion."""

    __tablename__ = "control_mappings"
    __table_args__ = (
        UniqueConstraint("source_control_id", "target_control_id", name="uq_control_mapping_pair"),
        Index("ix_control_mappings_source", "source_control_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_control_id: Mapped[int] = mapped_column(
        ForeignKey("framework_controls.id", ondelete="CASCADE"), nullable=False
    )
    target_control_id: Mapped[int] = mapped_column(
        ForeignKey("framework_controls.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type: Mapped[MappingRelationship] = mapped_column(
        Enum(MappingRelationship, name="mapping_relationship"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_control: Mapped[FrameworkControl] = relationship(
        back_populates="mapped_to", foreign_keys=[source_control_id]
    )
    target_control: Mapped[FrameworkControl] = relationship(
        back_populates="mapped_from", foreign_keys=[target_control_id]
    )
