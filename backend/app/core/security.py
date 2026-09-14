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

# bcrypt reads the first 72 bytes of a password and silently ignores the rest, so a
# passphrase padded past 72 bytes verifies against the same 72 bytes with anything
# appended. The bcrypt package used here does not refuse this (checked: a 73-byte
# password verifies against a 72-byte hash). Refusing at hash time is the honest
# answer; a password that cannot be stored in full cannot be checked in full.
PASSWORD_MAX_BYTES = 72


class PasswordTooLong(ValueError):
    pass


def hash_password(plain: str) -> str:
    encoded = plain.encode("utf-8")
    if len(encoded) > PASSWORD_MAX_BYTES:
        raise PasswordTooLong(
            f"Passwords are limited to {PASSWORD_MAX_BYTES} bytes; bcrypt would silently "
            "truncate a longer one."
        )
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    encoded = plain.encode("utf-8")
    if len(encoded) > PASSWORD_MAX_BYTES:
        # Cannot have been stored, so cannot be correct. Fail closed rather than let
        # bcrypt compare the first 72 bytes and say yes.
        return False
    try:
        return bcrypt.checkpw(encoded, hashed.encode("utf-8"))
    except (ValueError, TypeError):
        # A malformed stored hash must fail closed, not raise into a 500 that tells an
        # attacker the account exists.
        return False


# A real hash of a fixed value, compared against when the username is unknown, so the
# unknown-user path costs one bcrypt like the wrong-password path does. Without it the
# 401 is uniform but the response time is not, and the timing tells an attacker which
# usernames exist. Computed once at import; the value is never a valid password.
_DUMMY_HASH = bcrypt.hashpw(
    b"grcshield-timing-equaliser", bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
).decode()


def burn_a_verification(plain: str) -> None:
    """Spend the bcrypt cost a real verification would, and discard the result."""
    verify_password(plain, _DUMMY_HASH)


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
