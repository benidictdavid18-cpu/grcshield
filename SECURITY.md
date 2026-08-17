# Security

> **Sample / Portfolio Assessment.** GRCShield is a portfolio project holding fictional
> data for a fictional company. It is not production software. Read
> [Known gaps](#known-gaps) before drawing any conclusion from the rest of this document.

This describes what the application actually does, with file references, and then states
plainly what it does not do.

## Authentication

### Password storage

**bcrypt, cost factor 12**, via the `bcrypt` package directly
([`app/core/security.py`](backend/app/core/security.py)).

- Not SHA-256, not a hand-rolled salt scheme. A deliberately slow, salted key derivation
  function is the only acceptable answer for passwords.
- `bcrypt` is used directly rather than through `passlib`, because passlib is effectively
  unmaintained and its bcrypt backend breaks against bcrypt 4.x.
- Cost 12 is roughly 250 ms per verification on commodity hardware — slow enough to make
  offline cracking expensive, fast enough not to be a denial-of-service vector on login.
- `verify_password` fails **closed** on a malformed stored hash rather than raising, so a
  corrupted record produces a normal 401 rather than a 500 that confirms the account
  exists.

A test asserts every stored hash begins `$2b$12$` and contains no plaintext
([`tests/test_auth_api.py`](backend/tests/test_auth_api.py)).

### Tokens

**HS256 JWT, 8-hour expiry, issuer-checked.**

| Claim | Purpose |
| --- | --- |
| `sub` | Username. Re-read from the database on every request. |
| `role` | Carried for convenience — **not trusted** for authorisation. |
| `iat` / `exp` | Issued-at and expiry. 8 hours. |
| `iss` | `grcshield`. Verified on decode. |

Symmetric signing is appropriate while one service both issues and verifies tokens;
asymmetric signing buys nothing until a second service must verify without being able to
issue.

**The role is re-read from the database on every request**
([`app/api/deps.py`](backend/app/api/deps.py)), not taken from the token. A role change or
a deactivation therefore takes effect immediately rather than at token expiry. A token
that decodes correctly but names an unknown or inactive user is refused — asserted by
`test_a_valid_token_for_an_unknown_user_is_refused`.

**No refresh tokens.** They exist to keep access tokens short-lived without annoying
users, and introduce a revocation problem of their own. The honest trade-off for this
project is one 8-hour token and a re-login.

### Username enumeration

Unknown username, wrong password and deactivated account all return the identical 401 with
the identical message. Parametrised test:
`test_bad_credentials_all_return_the_same_401`.

## Authorisation

Three roles ([`app/models/user.py`](backend/app/models/user.py)):

| Role | Read | Write |
| --- | --- | --- |
| `AUDITOR` | Everything | Nothing |
| `ISMS_MANAGER` | Everything | The registers |
| `ADMIN` | Everything | The registers, plus user administration |

### Enforcement points

**Two, and only two**, so they are easy to audit
([`app/main.py`](backend/app/main.py), [`app/api/deps.py`](backend/app/api/deps.py)):

1. `current_user` — every route outside `/health` and `/auth` requires a valid token.
2. `require_write` — mutating HTTP methods additionally require `ISMS_MANAGER` or `ADMIN`.

Both are applied **at the router level**, not per-endpoint:

```python
for router in _protected:
    app.include_router(router, dependencies=[Depends(require_write)])
```

A per-endpoint decorator is a rule you can forget to apply to the next endpoint you add.
Router-level application means a new endpoint is protected by default and you would have
to work to expose it.

**Read access is not open.** An ISMS holds the map of an organisation's weaknesses — the
risks it has accepted, the controls that failed testing, the gaps with dates attached. A
read-only auditor role is only meaningful if unauthenticated reads are refused. A
parametrised test walks all sixteen register endpoints and asserts 401 without a token.

Authorisation is checked **before** payload validation: an auditor sending a malformed
write receives 403, not 422 (`test_a_write_refusal_happens_before_validation`).

## Input validation

**Every request body is a Pydantic model.** Unknown fields are ignored, types are coerced
or rejected, and constrained fields are bounded at the schema — for example
`residual_likelihood: int = Field(ge=1, le=5)`. A malformed body never reaches business
logic.

**Business rules are enforced server-side, not in the UI.** The UI can be bypassed; the
API cannot. Roughly two dozen rules return 422 with the offending field named — for
example, a residual score below inherent with no creditable control, an SoA inclusion
justification that cites the standard rather than a driver, a control test with no
sampling rationale, a risk acceptance with no expiry date.

**Critical invariants are also database `CHECK` constraints**, so they hold regardless of
write path — including someone connecting with `psql`. Examples: `residual_justification`
non-empty, an excluded SoA control cannot be `IMPLEMENTED`, a deficient control design
cannot carry an `EFFECTIVE` operating rating, a BIA recovery objective cannot exceed the
maximum tolerable outage, a closed nonconformity must record an effectiveness check.

## SQL injection

**All database access is through SQLAlchemy ORM constructs**, which parameterise values.
There is no string-interpolated SQL anywhere in the application. The one place raw SQL
appears is the liveness probe, `db.execute(text("SELECT 1"))`, which takes no input.

User-supplied filter values reach the database as bound parameters — for example the SoA
search:

```python
stmt = stmt.where(func.lower(SoAEntry.control_ref).like(needle))
```

`needle` is a bound parameter, not concatenated text.

## File uploads

**There are none.** The evidence register stores a `file_reference` string recording where
an artifact lives; no file is accepted, stored or served by the application. This is
stated rather than described as a control, because an upload path that does not exist
cannot be validated — and inventing one would be the more dangerous choice.

If uploads were added, the requirements would be: allowlist by content type *and* magic
bytes rather than extension, a hard size cap enforced before buffering, storage outside
the web root under a generated name, serving through an authenticated handler with
`Content-Disposition: attachment` and `X-Content-Type-Options: nosniff`, and antivirus
scanning before the file becomes retrievable.

## CORS

Explicit origin allowlist, no wildcard
([`app/core/config.py`](backend/app/core/config.py)):

```python
cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
```

Methods are enumerated rather than `*`, and allowed headers are limited to
`Authorization` and `Content-Type`. `allow_credentials=True` is set, which is why the
origin list must never become a wildcard — the browser refuses that combination, and
relying on the browser to catch a server misconfiguration is not a control.

## Secrets

**Everything sensitive comes from the environment**, through a single typed settings
object. Nothing is hard-coded, and `.env` is git-ignored with a committed `.env.example`
showing the shape.

`JWT_SECRET` ships with a **published placeholder** so the demo starts with no
configuration. This is a deliberate demo affordance, not an oversight, and the application
logs a warning at startup if the default is still in use outside development:

```python
if settings.jwt_secret_is_default and settings.environment != "development":
    logger.warning("JWT_SECRET is still the built-in development default. ...")
```

Database credentials in `docker-compose.yml` are likewise demo values.

## Transport

The application serves plain HTTP. TLS is expected to terminate at a reverse proxy or load
balancer in front of it, which is the normal arrangement for a containerised service. No
HSTS or secure-cookie handling exists in the app because it issues no cookies — the token
lives in `sessionStorage` and travels in an `Authorization` header.

`sessionStorage` rather than `localStorage` is deliberate: the token dies with the browser
tab rather than persisting on a shared machine. It remains readable by JavaScript, which
matters — see the XSS entry under known gaps.

## Audit logging

**Application logging is request-level only** (uvicorn access logs). There is no record of
*who* changed *what*.

Every record in the domain model carries `created_at` and `updated_at`, and the ISMS
records themselves carry authorship — `tester`, `reviewed_by`, `approved_by`,
`identified_by`, `assessed_by`. So the ISMS content is attributable. The *application's own
audit trail* is not, and for a real GRC tool that would be a significant omission: an
auditor would reasonably ask who lowered a residual score and when.

---

## Known gaps

Stated plainly. This is a portfolio project; the point is knowing what is missing, not
pretending it is complete.

| Gap | Consequence | Why it is absent |
| --- | --- | --- |
| **No rate limiting** | `/auth/token` can be brute-forced. bcrypt cost 12 slows it but does not stop it. | Phase 1 explicitly removed rate-limiting middleware as scope. Would be the first thing added. |
| **No account lockout** | Same. No backoff after repeated failures. | Out of scope. |
| **No password reset or rotation** | Passwords are set at seed time only. No expiry, no complexity policy, no history. | No mail path in a demo. |
| **No MFA on this application** | Ironic given RISK-004. Single factor only. | Out of scope. |
| **No audit log of user actions** | Cannot answer "who changed this residual score?". | The most significant gap for a tool of this kind. |
| **No security headers middleware** | No CSP, `X-Frame-Options`, `Referrer-Policy` or HSTS. | Expected at the proxy; not implemented. |
| **XSS exposure is untested** | React escapes by default and no `dangerouslySetInnerHTML` is used, but the token is JS-readable, so a successful XSS would yield it. | No CSP, no `HttpOnly` cookie alternative. |
| **No CSRF protection** | Not currently exploitable — auth is a bearer header, not a cookie, so a cross-site form cannot authenticate. Would become necessary the moment cookies were introduced. | By design of the token transport. |
| **Demo credentials are published** | Anyone who reaches a deployed instance can sign in. | Deliberate: fictional data, and a demo nobody can enter is not a demo. |
| **`JWT_SECRET` default is public** | Tokens are forgeable against an unconfigured instance. | Deliberate demo affordance, with a startup warning. |
| **No dependency scanning in CI** | There is no CI. | Out of scope. |
| **`docker compose up` is unverified** | The compose file and Dockerfiles are written but were never executed — Docker Desktop crashes on the author's machine. | Stated in the README rather than glossed. |
| **No multi-tenancy** | One organisation, no data isolation. | Not in scope for a single-company ISMS demo. |
| **No backups or retention on the app's own data** | The tool that tracks FinFlow's backup control has no backup story of its own. | Demo. |

### If this were going to production

In order: rate limiting and lockout on `/auth`, an audit log of every mutation with actor
and before/after values, security headers with a real CSP, `JWT_SECRET` supplied from a
secret manager, MFA, dependency and container scanning in CI, and TLS enforced with HSTS.

## Reporting a vulnerability

This is a portfolio project with no users and no production deployment. If you find
something wrong, open an issue on the repository — there is no private disclosure process
because there is nothing to disclose against.
