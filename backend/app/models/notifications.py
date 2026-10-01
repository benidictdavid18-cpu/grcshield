from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationRouting(Base):
    __tablename__ = "notification_routing"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner: Mapped[str] = mapped_column(String(160), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    assigned_by: Mapped[str] = mapped_column(String(64))


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','DELIVERED','ACKNOWLEDGED')", name="ck_notification_status"
        ),
        CheckConstraint(
            "status != 'ACKNOWLEDGED' OR (acknowledged_on IS NOT NULL AND acknowledged_by IS NOT NULL)",
            name="ck_notification_ack",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    dedup_key: Mapped[str] = mapped_column(String(64), unique=True)
    record_ref: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(String(160))
    due_date: Mapped[date] = mapped_column(Date)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    attempts: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    delivered_on: Mapped[date | None] = mapped_column(Date)
    escalated_on: Mapped[date | None] = mapped_column(Date)
    acknowledged_on: Mapped[date | None] = mapped_column(Date)
    acknowledged_by: Mapped[str | None] = mapped_column(String(64))
