from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RetentionState(Base):
    __tablename__ = "retention_state"
    id: Mapped[int] = mapped_column(primary_key=True)
    last_run: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cutoff: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted_count: Mapped[int] = mapped_column(Integer)
    policy: Mapped[str] = mapped_column(String(160))
