import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import get_settings
from app.core.rate_limit import login_failures
from app.core.security import burn_a_verification, create_access_token, verify_password
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
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)) -> TokenOut:
    """Exchange credentials for a bearer token.

    The same 401 is returned for an unknown username, a wrong password and a deactivated
    account, and it is returned in the same time: an unknown username still pays for one
    bcrypt comparison. Distinguishing the cases by body or by clock would let an attacker
    enumerate valid usernames.

    Repeated failures from one client against one account are refused with 429 before
    any of that runs. See core/rate_limit.py for the shape of the limit.
    """
    settings = get_settings()
    username = payload.username.strip().lower()
    key = (request.client.host if request.client else "unknown", username)
    now = time.monotonic()

    retry_after = login_failures.retry_after(
        key,
        now=now,
        limit=settings.auth_failure_limit,
        window=settings.auth_failure_window_seconds,
    )
    if retry_after is not None:
        plural = "" if retry_after == 1 else "s"
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed sign-in attempts. Try again in {retry_after} second{plural}.",
            headers={"Retry-After": str(retry_after)},
        )

    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        burn_a_verification(payload.password)
        authenticated = False
    else:
        authenticated = user.is_active and verify_password(payload.password, user.hashed_password)

    if not authenticated or user is None:
        login_failures.record_failure(key, now=now)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    login_failures.clear(key)

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
