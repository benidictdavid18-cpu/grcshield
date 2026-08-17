from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.user import Role, User

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    username: str
    full_name: str
    role: Role
    can_write: bool


class MeOut(BaseModel):
    username: str
    full_name: str
    email: str
    role: Role
    can_write: bool


@router.post("/token", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    """Exchange credentials for a bearer token.

    The same 401 is returned for an unknown username, a wrong password and a deactivated
    account. Distinguishing them would let an attacker enumerate valid usernames.
    """
    user = db.scalar(select(User).where(User.username == payload.username.strip().lower()))
    if user is None or not user.is_active or not verify_password(
        payload.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token, expires_in = create_access_token(username=user.username, role=user.role.value)
    return TokenOut(
        access_token=token,
        expires_in=expires_in,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        can_write=user.can_write,
    )


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(current_user)) -> MeOut:
    return MeOut(
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        can_write=user.can_write,
    )
