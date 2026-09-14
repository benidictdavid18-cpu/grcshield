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
- **Passwords over 72 bytes are refused**, at hash time and at verify time. bcrypt reads
  the first 72 bytes and silently ignores the rest — checked against the installed
  package: a 73-byte password verifies against a 72-byte hash — so a longer password
  would be stored and checked as something shorter than the user typed.
  `test_a_password_longer_than_72_bytes_never_verifies` holds the line.

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
the identical message (`test_bad_credentials_all_return_the_same_401`) — **and in the
same time**. An unknown username used to short-circuit before bcrypt ran, which made the
401 uniform in body and distinguishable by clock. The unknown-user path now spends one
comparison against a fixed dummy hash (`burn_a_verification`), so both paths cost one
bcrypt. `test_an_unknown_username_costs_a_bcrypt_comparison` asserts the call; a coarse
timing test asserts the two paths are within a factor of two of each other.

### Failed-login throttling

`/auth/token` counts **failures** per (client address, username) inside a sliding window —
ten in sixty seconds by default, `AUTH_FAILURE_LIMIT` and `AUTH_FAILURE_WINDOW_SECONDS` —
and answers `429` with a `Retry-After` once the limit is reached. A successful login
clears the count. The correct password is refused too while the window is open; a limit
that lifts for the right guess is not a limit.

Keyed on the pair, not either half: by address alone, one attacker behind a NAT locks out
everyone behind it; by username alone, an attacker can lock a victim out on purpose. The
tracker is in-process, so it resets on restart and is per-worker under a multi-process
server — stated under Known gaps. ([`app/core/rate_limit.py`](backend/app/core/rate_limit.py))

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
secure-cookie handling exists in the app because it issues no cookies — the token lives
in `sessionStorage` and travels in an `Authorization` header.

### Response headers

Every API response carries `Content-Security-Policy: default-src 'none'; frame-ancestors
'none'`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy:
no-referrer` and `Cache-Control: no-store`
([`app/core/headers.py`](backend/app/core/headers.py)). A JSON body has nothing to load,
so the strictest policy is the right one; the interactive documentation at `/docs` and
`/redoc` gets a policy that allows exactly the CDN it loads from.
`Strict-Transport-Security` is added only when `ENVIRONMENT` is not `development` —
over plain HTTP it is meaningless, and from a local demo it would pin the developer's
browser to HTTPS on localhost for a year.

These headers cover the API. The single-page application has its own, set by the nginx
container that serves it ([`frontend/nginx.conf`](frontend/nginx.conf)):
`script-src 'self'` with no inline scripts, `frame-ancestors 'none'`, `base-uri 'self'`,
`form-action 'self'`. In development Vite serves the page without them.

`sessionStorage` rather than `localStorage` is deliberate: the token dies with the browser
tab rather than persisting on a shared machine. It remains readable by JavaScript, which
matters — see the XSS entry under known gaps.

## Audit logging

**Every mutation through the API writes an event to `audit_events`**: who (username and
role), when, which record (by business reference — RISK-004, A.8.5, TEST-013), the
changed fields before and after as JSON, and a one-sentence summary. The trail answers
the question an auditor asks first when a number on the register has moved: *who lowered
this residual score, when, and from what?*

Properties that make it worth trusting:

- **Same transaction as the change.** `services/audit_trail.record_change` adds the event
  to the session; the route commits both together. A `422` that rolls the change back
  rolls the event back with it. `test_a_refused_write_leaves_no_event` asserts this.
- **A cascade is recorded as what it is.** Recording a workpaper with exceptions creates a
  finding, a remediation item, and re-rates the control. The trail carries one event for
  the test naming what it raised, and a second for the control's rating change pointing
  back at the test that implied it.
- **Append-only by construction.** The only endpoint under `/audit-events` is a filtered
  `GET`, and `test_no_endpoint_can_edit_or_remove_an_event` walks the route table to keep
  it that way. The read-only auditor role can read the trail — that is who it is for.
- **Actor stored as text**, not a foreign key, so the trail stays readable after the
  account is deactivated. Same reasoning as the AI interaction log.
- **A no-op edit is not an event.** Re-submitting an SoA entry with the same values
  records nothing; a trail full of "changed nothing" entries hides the ones that matter.

What it does not do: nothing at the database level stops a DBA from editing the table.
Tamper-evidence (hash chaining, or shipping events to a write-once store) is the next
step for a production deployment and is listed under Known gaps.

Application logging otherwise remains request-level (uvicorn access logs). The ISMS
content records carry their own authorship — `tester`, `reviewed_by`, `approved_by`,
`identified_by`, `assessed_by` — independent of the application trail.

---

## The AI assistant

An optional local assistant (Ollama). It is treated as an external dependency and as an
untrusted output source, even though it runs on the same machine.

**Data leaving the machine: none.** Inference is local. That is the reason Ollama was
chosen over a hosted API — an ISMS is a catalogue of an organisation's weaknesses, and
sending it to a third party would be a processing activity needing a lawful basis, a
RoPA entry, a transfer assessment and a supplier review.

**What reaches the model.** Context is assembled per task from named fields, never by
dumping records. `test_context_never_carries_a_credential` renders every context builder
and asserts the result contains no password hash, no signing key, no database URL and no
demo password — checked against the real values, not against field names, so it fails if
a future builder reaches a user row by any route.

**Prompt injection.** Record content is free text somebody typed. It is fenced, labelled,
and preceded by a system prompt stating that instructions inside a fence are never
followed; a record cannot close its own fence. No filter tries to detect attack phrasing,
because "ignore all previous instructions" is legitimate content for a risk *about*
prompt injection and a filter would corrupt the record while missing the next phrasing.

**No user-supplied prompts.** The system message is assembled from constants. Request
schemas use `extra="forbid"`, so a `system_prompt` field is a `422` rather than a field
quietly ignored. The one free-text field is a bounded question, framed in the user
message as a question rather than an instruction.

**Untrusted output.** Responses are constrained to a JSON schema at generation and
validated against it again on return; malformed output is a `502`, never a `500` and
never a half-parsed suggestion rendered like a whole one. Claims of compliance,
certification, verification or a test verdict are flagged to the analyst and logged.

**No authority.** The assistant cannot write to any register. See ADR-009 in
[docs/DECISIONS.md](docs/DECISIONS.md) for the three independent enforcement points and
the reasoning.

**What the log stores, and why it stores so little.** Who, when, which feature, which
record, which model, what happened, sizes, and a truncated SHA-256 digest of the
response. No prompt text and no response text: every prompt is built from records this
database already holds under their own access control, and a second copy in a log table
would add exposure without adding assurance.

**Ollama has no authentication of its own.** `OLLAMA_BASE_URL` must stay on loopback or a
private network; the application logs a warning at start-up if it does not. Exposing an
Ollama instance to the internet publishes an unauthenticated inference endpoint.

**Gap: no rate limiting on the assistant endpoints.** Request size is bounded and the
model server is local, so the exposure is a slow endpoint rather than a bill — but it
would be the first thing to add before this ran anywhere shared.

---

## Known gaps

Stated plainly. This is a portfolio project; the point is knowing what is missing, not
pretending it is complete.

| Gap | Consequence | Why it is absent |
| --- | --- | --- |
| **Login throttling is in-process** | The failure counter resets on restart and is per-worker under a multi-process server, so a determined attacker gets N guesses per worker per window. | The limit exists and is tested. A shared store (Redis) is the production step. |
| **No account lockout** | Same. No backoff after repeated failures. | Out of scope. |
| **No password reset or rotation** | Passwords are set at seed time only. No expiry, no complexity policy, no history. | No mail path in a demo. |
| **No MFA on this application** | Ironic given RISK-004. Single factor only. | Out of scope. |
| **Audit trail is not tamper-evident** | A database administrator could edit or delete `audit_events` rows and nothing would notice. | The trail itself exists (see Audit logging). Hash chaining or a write-once sink is the production step. |
| **XSS exposure is untested** | React escapes by default and no `dangerouslySetInnerHTML` is used, but the token is JS-readable, so a successful XSS would yield it. | The nginx container sets a CSP on the page (`script-src 'self'`, no inline scripts), which blocks the injected-script form of XSS; the Vite dev server sets none. No `HttpOnly` cookie alternative. |
| **No CSRF protection** | Not currently exploitable — auth is a bearer header, not a cookie, so a cross-site form cannot authenticate. Would become necessary the moment cookies were introduced. | By design of the token transport. |
| **Demo credentials are published** | Anyone who reaches a deployed instance can sign in. | Deliberate: fictional data, and a demo nobody can enter is not a demo. |
| **`JWT_SECRET` default is public** | Tokens are forgeable against an unconfigured instance. | Deliberate demo affordance, with a startup warning. |
| **Dependency audit is advisory** | `pip-audit` and `npm audit` run on every push but do not fail the build. | Pinned versions accumulate advisories faster than a portfolio project bumps them; a red build nobody can act on trains people to ignore red builds. The report is in the CI log. |
| **`docker compose up` is verified only in CI** | The compose job builds and starts the stack on a clean runner and runs the smoke test against PostgreSQL. It has never run on the author's machine, where Docker Desktop crashes. | The runner is the more honest environment anyway: no cached images, no local state. |
| **No multi-tenancy** | One organisation, no data isolation. | Not in scope for a single-company ISMS demo. |
| **No backups or retention on the app's own data** | The tool that tracks FinFlow's backup control has no backup story of its own. | Demo. |

### Containers

The base compose file is production-shaped: the API runs as an unprivileged user, is
not published on the host, and is reached only through the nginx container; PostgreSQL
is not published at all; the frontend is a static bundle, not a dev server. The dev
override (`docker-compose.override.yml`, applied automatically by `docker compose up`)
adds the bind mounts and published ports, which is why they are in a file whose name
says what they are for. `docker compose -f docker-compose.yml` is the deployable shape.

### If this were going to production

In order: a shared store for login throttling plus account-level lockout,
tamper-evidence for the audit trail, a CSP on the web server that serves the SPA, `JWT_SECRET` supplied from a
secret manager, MFA, dependency and container scanning in CI, and TLS enforced with HSTS.

## Reporting a vulnerability

This is a portfolio project with no users and no production deployment. If you find
something wrong, open an issue on the repository — there is no private disclosure process
because there is nothing to disclose against.
