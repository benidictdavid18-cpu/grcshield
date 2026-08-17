"""Authentication and authorisation dependencies.

Two enforcement points, and only two, so they are easy to audit:

    ``current_user``  every route outside /health and /auth requires a valid token.
    ``require_write`` mutating routes additionally require a write role.

Applied at the router level rather than per-endpoint, because a per-endpoint decorator
is a rule you can forget to apply to the next endpoint you add.
"""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import Role, User

_bearer = HTTPBearer(auto_error=False)

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Authentication required.",
    headers={"WWW-Authenticate": "Bearer"},
)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise _UNAUTHENTICATED

    payload = decode_access_token(credentials.credentials)
    if payload is None or not payload.get("sub"):
        raise _UNAUTHENTICATED

    user = db.scalar(select(User).where(User.username == payload["sub"]))
    # The role is re-read from the database rather than trusted from the token, so a
    # role change or a deactivation takes effect immediately instead of at token expiry.
    if user is None or not user.is_active:
        raise _UNAUTHENTICATED
    return user


def require_write(request: Request, user: User = Depends(current_user)) -> User:
    """Refuse mutating requests from a read-only role."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return user
    if not user.can_write:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"The {user.role.value} role is read-only. Maintaining the registers "
                "requires the ISMS_MANAGER or ADMIN role."
            ),
        )
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required."
        )
    return user
