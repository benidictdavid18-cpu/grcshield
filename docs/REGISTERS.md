# Judgment registers: acceptance, privacy and continuity

> **Sample / Portfolio Assessment.** FinFlow Technologies is a fictional company.
> No certification body or audit firm has assessed any of this. Every record is
> illustrative.

Four registers, one theme. Each records a judgment somebody made, with the thing that
makes the judgment reviewable attached to it — an expiry date, a safeguard, a tolerance
figure. Without that attachment each becomes a document that looks like governance and
functions as filing.

## Asset register

Twelve assets. It exists because RoPA entries, DPIAs and business impact analyses all
need something concrete to point at. "Customer data" is not an asset; **AST-001**, the
production cluster in eu-west-1, is.

**AST-007** (analytics warehouse) and **AST-008** (support tooling) are the two stores
TEST-008 found holding unmasked customer records. They appear in the asset register, in
ROPA-003 and ROPA-004, and in DPIA-001 — the same failure surfaces in four places
because they are the same records.

## Risk acceptance

> **Risk acceptance is a business decision, not a security decision.**

Two rules, both enforced with 422 and a database constraint:

**1. An acceptance must expire.** One without an end date is a permanent decision
disguised as a temporary one — the conditions that made it reasonable will change and
nobody will revisit it. `expiry_date` is `NOT NULL`.

**2. The approver must be the risk owner**, or a named escalation approver (the CEO), and
**never the security function**. Security advises on risk; the person who answers for
the consequence decides to carry it. An acceptance signed by the people who raised the
risk is not an acceptance. Roles containing "security", "CISO", "InfoSec" or "compliance
analyst" are rejected outright.

A `review_trigger` is also mandatory: record what would force a revisit *before* the
expiry. Time is the backstop, not the only trigger.

### The four records

| | Risk | State | Note |
| --- | --- | --- | --- |
| EXC-001 | RISK-003 — single PSP | **Expiring in 21 days** | COO, the risk owner |
| EXC-002 | RISK-007 — single region | Approved to 2027-06-30 | CEO; the decision that sets BC appetite at High |
| EXC-003 | RISK-010 — vendor breach | **Expired 46 days ago** | Not renewed; the exposure is now uncovered |
| EXC-004 | RISK-004 — privileged MFA | **Rejected** | Refused at MR-2026-H1 |

EXC-004 is the one worth reading. The Head of Engineering requested a time-boxed
acceptance of the privileged MFA gap; the CTO refused it at management review, on the
record: accepting a known privileged access gap while seeking certification is not
defensible to an auditor, and the compensating controls are detective only, so they
shorten the incident rather than prevent it. **A register that only records approvals is
a record of agreement, not of decisions.**

### The number nobody asks for

The summary reports `uncovered_breaches`: risks above their category appetite with **no
live acceptance covering them**. Currently that is all seven — RISK-002, 004, 008, 009,
010, 018 and 019. EXC-003 expired and EXC-004 was refused, so nothing live covers any of
them.

An exposure carried without a decision is worse than a documented acceptance, because
nobody has agreed to it. Most acceptance registers cannot answer this question at all,
since they only know about the exceptions somebody bothered to raise.

## GDPR Article 30 — Record of Processing Activities

Six processing activities. Article 30(1) fields are all present; three dependencies are
enforced rather than trusted:

- **A transfer outside the EEA requires a Chapter V safeguard.** A transfer with no
  recorded mechanism is an unlawful transfer with paperwork attached. The reverse is
  also rejected: a safeguard recorded with no transfer means one of the two fields is
  wrong.
- **A retention period is required** — Article 30(1)(f) asks for envisaged time limits,
  and "as long as necessary" is not a time limit.
- **Legitimate interests requires the balancing test.** Article 6(1)(f) is the only basis
  that depends on an assessment; relying on it without recording that assessment leaves
  the basis unevidenced.

ROPA-003 (support ticket handling) is the only third-country transfer: FinFlow support
staff in India, under Standard Contractual Clauses with a completed transfer impact
assessment.

### A record that admits its own weakness

ROPA-003 lists **DP-005** among its Article 30(1)(g) security measures, and DP-005 is
currently rated `INEFFECTIVE` after TEST-008. The API returns `credited: false` on that
control and the UI marks it, because a processing record claiming a protection that is
not working should say so. The legitimate-interests assessment on ROPA-003 says the same
thing in prose: the minimisation the balance depends on is not currently operating.

## GDPR Article 35 — Data Protection Impact Assessments

Two assessments, both with the DPO consulted (Article 35(2), enforced).

**DPIA-001 is the phase's most interesting record.** It was originally assessed as
`MEDIUM` residual with an outcome of "proceed with measures", on the basis that DP-005
masking would keep raw transaction data out of routine support workflows. TEST-008 found
the support replica holding roughly 12,000 unmasked records — the measure the assessment
depended on was not operating.

The residual rating was raised to `HIGH`. **Article 36(1) then forced the outcome to
change with it**: where a DPIA indicates high residual risk after mitigation, the
controller must consult the supervisory authority before processing. FinFlow cannot
decide alone to continue at that level.

That dependency is enforced — an API call recording `HIGH` residual with a `PROCEED`
outcome and no consultation returns 422, and there is a matching `CHECK` constraint. The
seed loader refused my first draft of DPIA-001 for exactly this reason, which is how the
record ended up correct.

DPIA-002 shows the other useful outcome: per-user behavioural profiling was **removed
from scope** rather than mitigated, because it would have supported no decision that
account-level analysis could not. The DPO's recorded advice is that a purpose which
cannot be explained to the data subject in a sentence is usually one that should not
proceed.

## Business impact analysis

Five processes. The numbers are the point:

| | Process | RTO | RPO | MTPD | Headroom | 24h impact |
| --- | --- | --- | --- | --- | --- | --- |
| BIA-001 | Payment transaction processing | 2h | 15m | 4h | 2h | £96,000 |
| BIA-002 | Merchant settlement and payouts | 4h | 15m | 24h | 20h | £18,000 |
| BIA-003 | Merchant onboarding | 24h | 4h | 72h | 48h | £2,400 |
| BIA-004 | Customer support | 8h | 24h | 48h | 40h | £900 |
| BIA-005 | Financial reporting | 48h | 24h | 120h | 72h | — |

**MTPD is what the business can survive; RTO and RPO are what recovery is planned to
achieve.** If RTO exceeds MTPD the plan fails on the day it is written — recovery
completes after the point the business could bear the outage. That relationship is
enforced at the API and by a `CHECK` constraint, and `recovery_headroom_hours` reports
the slack.

### The gap a BIA exists to find

BIA-001's two-hour RTO is achievable for the failure modes FinFlow has engineered for:
single-zone loss is covered by OP-006, and database corruption by OP-005 (TEST-012
completed a restore in 47 minutes). It is **not** achievable for the loss of the whole
eu-west-1 region — which is precisely the scenario formally accepted under EXC-002.

That is not an oversight. It is the consequence of an explicit, approved business
decision, and the BIA records it so the decision is visible against the recovery target
it undercuts. EXC-002's review trigger names the same tension from the other direction.
Whoever renews that acceptance should be looking at BIA-001 while they do it.
