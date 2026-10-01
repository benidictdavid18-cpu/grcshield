from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReferenceCounter(Base):
    __tablename__ = "reference_counters"
    __table_args__ = (CheckConstraint("last_value >= 0", name="ck_reference_counter_nonnegative"),)
    prefix: Mapped[str] = mapped_column(String(24), primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer)
