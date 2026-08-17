"""Users and roles.

Three roles, matching the three things people actually do with an ISMS:

    AUDITOR       read everything, change nothing. The demo account.
    ISMS_MANAGER  read everything, maintain the registers.
    ADMIN         as above, plus user administration.

Read access is not open. An ISMS holds the map of an organisation's weaknesses — the
risks it has accepted, the controls that failed testing, the gaps with dates attached.
A read-only role exists so an auditor can be given exactly that and nothing more, which
is only meaningful if unauthenticated reads are refused.
"""

import enum

from sqlalchemy import Boolean, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Role(str, enum.Enum):
    AUDITOR = "AUDITOR"
    ISMS_MANAGER = "ISMS_MANAGER"
    ADMIN = "ADMIN"


WRITE_ROLES = frozenset({Role.ISMS_MANAGER, Role.ADMIN})


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(160), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role, name="user_role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    @property
    def can_write(self) -> bool:
        return self.role in WRITE_ROLES
