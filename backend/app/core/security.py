"""Password hashing and token issuing.

Choices and their reasons, so SECURITY.md can describe something real:

**bcrypt at cost 12** for password storage. Not SHA-256, not a homemade salt scheme —
a deliberately slow, salted KDF is the only acceptable answer for passwords, and bcrypt
is used directly rather than through passlib because passlib is effectively unmaintained
and its bcrypt backend breaks against bcrypt 4.x.

**HS256 JWTs with a short expiry.** Symmetric signing is appropriate here because one
service both issues and verifies the token; asymmetric signing buys nothing until a
second service needs to verify without being able to issue. Tokens carry the role so
authorisation does not need a database round trip, and expire in 8 hours so a leaked
token has a bounded life.

**No refresh tokens.** They exist to let access tokens be short-lived without annoying
users, and add a revocation problem of their own. For a portfolio ISMS the honest
trade-off is a single 8-hour token and a re-login.
"""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import get_settings

ALGORITHM = "HS256"
TOKEN_TTL_HOURS = 8
BCRYPT_ROUNDS = 12


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        # A malformed stored hash must fail closed, not raise into a 500 that tells an
        # attacker the account exists.
        return False


def create_access_token(*, username: str, role: str) -> tuple[str, int]:
    """Return (token, expires_in_seconds)."""
    settings = get_settings()
    now = datetime.now(UTC)
    expires = now + timedelta(hours=TOKEN_TTL_HOURS)
    payload = {
        "sub": username,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "iss": "grcshield",
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
    return token, int((expires - now).total_seconds())


def decode_access_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        return jwt.decode(
            token, settings.jwt_secret, algorithms=[ALGORITHM], issuer="grcshield"
        )
    except jwt.PyJWTError:
        return None
