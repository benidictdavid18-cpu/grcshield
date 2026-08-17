# Indicators, the executive view, and access control

> **Sample / Portfolio Assessment.** FinFlow Technologies is a fictional company.
> No certification body or audit firm has assessed any of this.

## Key risk indicators

Seven indicators. Each is a **definition** plus a **series of measurements**, kept apart
on purpose: the definition says what is counted and what good looks like, the series
records what was actually observed. A dashboard number with no definition behind it is
decoration, and a definition with no history is an opinion.

| | Indicator | Now | Target | Band |
| --- | --- | --- | --- | --- |
| KRI-001 | Privileged accounts with MFA enforced | 60% | ≥ 100% | **Red** |
| KRI-002 | Mean time to remediate Critical/High findings | 105 days | ≤ 30 days | **Red** |
| KRI-003 | Applicable Annex A controls implemented | 65.5% | ≥ 95% | **Red** |
| KRI-004 | Controls tested within required frequency | 31.4% | ≥ 80% | **Red** |
| KRI-005 | Risks above category appetite | 7 | 0 | **Red** |
| KRI-006 | Evidence within validity period | 90.3% | ≥ 95% | Amber |
| KRI-007 | Acceptances past expiry | 1 | 0 | Amber |

That is an uncomfortable board pack, and it is meant to be. A pre-certification ISMS at
a 40-person company genuinely looks like this; a dashboard showing green everywhere
would be the thing worth doubting.

### History is recorded, the current figure is computed

The five monthly points behind each indicator are **recorded observations**. The current
period is **computed live from the registers on every request**, so the dashboard cannot
drift away from the data behind it. Three of them are asserted against their own source
in the test suite — KRI-003 must equal the SoA overview, KRI-005 the risk register
summary, KRI-007 the acceptance register.

The most useful consequence: **KRI-003 goes backwards in the current period.** It rose
for five months and then fell from 66.7% to 65.5%, because TEST-008 downgraded A.8.11
from implemented to a gap. A stored metric would have kept climbing.

### Thresholds carry a direction

"Green above 95" and "green below 14" are both normal and one comparison operator cannot
serve both, so each definition stores `direction` alongside its thresholds. The same
applies to trend: a falling mean-time-to-remediate is an improvement, a falling
implementation percentage is not.

### NO_DATA is not zero

A metric with an empty population is **not measured**, which is a different statement
from zero and looks identical on most dashboards. `value` is nullable and renders as
"not measured".

KRI-002 shows the honest handling of a related problem. The brief asks for mean time to
remediate *Critical* findings; FinFlow has recorded no Critical priority items to date.
Rather than render an empty chart, High is included in the population and **the
substitution is stated in the formula description** where anyone recomputing the number
will read it.

## Executive summary

Written for someone who does not know what Annex A is and should not have to. Three
rules, all enforced by a test:

- **No control identifiers in the prose.** "A.8.5" means nothing to a board member.
- **No band names used as nouns.** "High" is jargon; "one of the five most serious" is
  not. `test_the_executive_summary_is_written_for_a_non_technical_reader` fails the build
  if "Annex A", "residual", "SoA", "inherent" or "KRI" appears in board-facing text.
- **Every recommendation names the owner and what it buys.**

It reports the *same numbers* as the rest of the application — asserted against the SoA
overview and the risk summary — for a different audience, not a different set of facts.

The metric worth noticing is **risks carried without a decision**: exposures above
appetite with no live acceptance covering them. Currently seven of seven. An exposure carried
without a decision is worse than a documented acceptance, because nobody has agreed to
it, and most tools cannot answer the question at all.

## Reports

All three are now implemented and render as PDF:

| Report | Audience | Endpoint |
| --- | --- | --- |
| Risk Register | Risk owners, management review | `/reports/risk-register.pdf` |
| SoA + Gap Analysis | Certification auditor, ISMS manager | `/soa/report.pdf` |
| Executive Summary | Founders, board | `/reports/executive-summary.pdf` |

The ISMS records export (`/isms/records.pdf`) is deliberately *not* in the registry — it
is a records bundle, not a report supporting a decision, and the set was cut to three on
purpose.

## Authentication and access control

Read access is **not open**. An ISMS holds the map of an organisation's weaknesses: the
risks it has accepted, the controls that failed testing, the gaps with dates attached. A
read-only auditor role only means something if unauthenticated reads are refused.

**Passwords**: bcrypt, cost 12, used directly rather than through passlib — passlib is
effectively unmaintained and its bcrypt backend breaks against bcrypt 4.x. A test asserts
every stored hash starts with `$2b$12$` and contains no plaintext.

**Tokens**: HS256 JWTs, 8-hour expiry, issuer-checked. Symmetric signing is right while
one service both issues and verifies; asymmetric buys nothing until a second service must
verify without being able to issue. No refresh tokens — they exist to keep access tokens
short-lived without annoying users, and add a revocation problem of their own. The honest
trade-off here is one 8-hour token and a re-login.

**The role is re-read from the database on every request**, not trusted from the token,
so a deactivation or role change takes effect immediately rather than at token expiry.

**Enforcement points — two, and only two**, applied at router level rather than
per-endpoint, because a per-endpoint decorator is a rule you can forget to apply to the
next endpoint you add:

- `current_user` — every route outside `/health` and `/auth` requires a valid token.
- `require_write` — mutating methods additionally require `ISMS_MANAGER` or `ADMIN`.

**Username enumeration**: unknown username, wrong password and deactivated account all
return the same 401 with the same message.

### Demo accounts

Published deliberately in the README. Fictional credentials for a fictional company's
fictional data; treating them as secrets would be theatre.

| Username | Password | Role |
| --- | --- | --- |
| `auditor` | `auditor-demo-2026` | Read everything, change nothing |
| `isms.manager` | `manager-demo-2026` | Read and maintain the registers |

A parametrised test walks every register endpoint and asserts the auditor gets 200 on
reads and **403 on every write path**, and that the refusal happens before payload
validation — 403, not 422.

## Smoke test

`scripts/smoke_test.py` runs 54 checks against a live instance and exits non-zero on the
first failure, so it is usable as a deployment gate. It verifies the service is seeded,
that unauthenticated and forged-token reads are refused, that read-only really is
read-only, and then walks the **RISK-004 chain end to end across all six phases**:

```
RISK-004  inherent 4x5=20 Critical, residual 3x5=15 High, impact unmoved
  → AC-002, basis tested-with-exceptions → Annex A A.8.5
  → SoA entry A.8.5, applicable, a gap
  → EV-002 evidence showing 60% privileged coverage
  → TEST-003, full population of 15, 6 exceptions, pass with exceptions
  → FIND-001 → remediation with an owner and a due date
  → EXC-004, the acceptance that was refused
  → NC-001, correction and corrective action recorded separately
  → KRI-001 computes 60%, red against target
  → all three reports render
```

```bash
python scripts/smoke_test.py --base-url http://localhost:8000
```
