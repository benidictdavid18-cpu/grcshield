# Decision records

> **Sample / Portfolio Assessment.** FinFlow Technologies is a fictional company.
> No certification body or audit firm has assessed any of this.

Eight decisions that shaped this project, recorded in the form an architecture decision
record takes: what the situation was, what was chosen, what else was on the table, and
what it cost.

**Every record below is marked `TODO AUTHOR:BENNY — expand in my own words`.** The
reasoning is captured so nothing is lost; the writing is deliberately left to be redone
by the author. An argument you have not written in your own words is an argument you
cannot defend when someone pushes back on it.

---

## ADR-001 — Residual risk is scored independently, not derived

**Status:** Accepted · **Affects:** the whole risk engine

### Context

The common shortcut is `residual = inherent × (1 − control_effectiveness)`. It is
appealing because it needs one number per control and produces a number per risk with no
further judgment. Most spreadsheet risk registers work this way.

### Decision

The analyst sets `residual_likelihood` and `residual_impact` directly and supplies a
written justification naming which control moved which dimension. There is deliberately
no control-effectiveness percentage field anywhere in the schema to derive from.

### Alternatives considered

1. **Derive residual from a single effectiveness percentage.** Rejected: it collapses two
   dimensions into one. Controls reduce likelihood *or* impact, rarely both. MFA makes
   compromise less likely and does nothing to the blast radius; a backup does the reverse.
2. **Derive it, then allow manual override.** Rejected: an override on a derived number
   invites people to accept the default, and the register ends up recording the arithmetic
   for most rows and judgment for a few, with no way to tell which is which.
3. **Score residual directly but make the justification optional.** Rejected: an
   unjustified number is indistinguishable from a guess.

### Consequence

More work per risk — every row needs a paragraph. In exchange, residual risk becomes
falsifiable: an auditor can disagree with a specific claim. RISK-004 demonstrates why it
matters — inherent 4×5, residual 3×5, impact unmoved. No single percentage produces that.

The cost shows up in the seed data: five justifications are unwritten because writing
twenty defensible ones is genuinely hard.

> **TODO AUTHOR:BENNY — expand in my own words.**
> Worth adding: the moment you realised the arithmetic model was wrong, and whether you
> would still choose this on a register of 200 risks rather than 20.

---

## ADR-002 — Untested controls earn no residual reduction

**Status:** Accepted · **Affects:** risk scoring, the Phase 2/Phase 4 boundary

### Context

Risk registers routinely credit controls that exist on paper. A control that has been
designed, documented and never tested is an intention. Crediting it converts an
assumption into a number, and the number is then reported as fact.

### Decision

`control_effectiveness_basis` on every risk-control link records how much is actually
known: `NOT_TESTED`, `DESIGN_ONLY`, `TESTED_EFFECTIVE`, `TESTED_WITH_EXCEPTIONS`,
`TESTED_INEFFECTIVE`. If a proposed residual is below inherent and no linked control may
be credited, the API refuses the write with 422. Scoring residual *at* inherent is always
permitted.

### Alternatives considered

1. **Warn in the UI, allow the write.** Rejected: a warning nobody has to clear is a
   warning nobody reads.
2. **Bar only `NOT_TESTED`**, as the original brief specified. Extended to include
   `TESTED_INEFFECTIVE`: a control tested and found to have failed provides *less*
   assurance than one never tested, because the failure is a known fact rather than an
   open question.
3. **Weight the reduction by basis** — say, half credit for `DESIGN_ONLY`. Rejected: that
   reintroduces exactly the invented arithmetic ADR-001 removed.

### Consequence

RISK-019 sits at its inherent level with both controls untested, and the register says so
instead of quietly claiming improvement. The extension to `TESTED_INEFFECTIVE` is a
judgment beyond the brief; it lives in one named constant, `NON_CREDITING_BASES`, and can
be narrowed back in a one-line edit.

> **TODO AUTHOR:BENNY — expand in my own words.**
> The interview question here is "what if the control obviously works and you just
> haven't got round to testing it?" Have an answer.

---

## ADR-003 — Risk appetite is set per category, not once

**Status:** Accepted · **Affects:** appetite thresholds, every breach calculation

### Context

Most tools carry one organisation-wide appetite line, usually expressed as a score
threshold. That says the business tolerates the same exposure to a privacy breach as to a
laptop running an old OS.

### Decision

`risk_appetite_thresholds` holds a `max_acceptable_band` and an approver role for each of
the nine categories. Comparison is by **band**, not score. A missing threshold returns
`null`, not `false`.

### Alternatives considered

1. **One global threshold.** Rejected as above.
2. **Per-risk appetite.** Rejected: appetite is a standing position the business takes
   about a *class* of exposure. Setting it per risk makes it indistinguishable from the
   residual score itself and removes the tension that makes a breach meaningful.
3. **Compare by score rather than band.** Rejected: a residual of 10 breaching a Medium
   ceiling while 9 does not looks arbitrary, but bands are the unit the business actually
   agreed to. Reintroducing point precision at the comparison step smuggles back the false
   accuracy the bands exist to remove.

### Consequence

Business Continuity carries the *highest* appetite in the register — hour-scale recovery
objectives, not the minutes an incumbent bank commits to — and that is a deliberate,
funded decision recorded in EXC-002. Data Privacy carries the lowest. No approver is the
security function, and a seed check fails the build if one ever is.

> **TODO AUTHOR:BENNY — expand in my own words.**
> Be ready for "who actually sets appetite at a 40-person company, realistically?"

---

## ADR-004 — Every risk acceptance expires

**Status:** Accepted · **Affects:** the acceptance register

### Context

Accepted risks are where registers go to die. An acceptance recorded once, with no end
date, becomes a permanent decision nobody revisits, and the conditions that made it
reasonable change silently.

### Decision

`expiry_date` is `NOT NULL`. A `review_trigger` is also mandatory — what would force a
revisit *before* the expiry. The approver must be the risk owner or a named escalation
approver, and never the security function. The dashboard reports expired and
expiring-within-30-days.

### Alternatives considered

1. **Optional expiry with a review reminder.** Rejected: optional means absent.
2. **A default expiry the system fills in.** Rejected: a date nobody chose is a date
   nobody owns.
3. **Let the security team approve acceptances.** Rejected outright, and enforced against
   — security advises on risk, the business decides to carry it. An acceptance signed by
   the people who raised the risk is not an acceptance.

### Consequence

The register carries something most do not: **risks above appetite with no live acceptance
covering them**. Currently seven of seven, because EXC-003 expired and EXC-004 was
refused.
An exposure carried without a decision is worse than a documented acceptance — nobody has
agreed to it — and most tools cannot answer the question at all.

> **TODO AUTHOR:BENNY — expand in my own words.**
> EXC-004 is the record to talk about: the acceptance the CTO refused, and why.

---

## ADR-005 — NIST CSF 2.0 and GDPR were descoped as scored frameworks

**Status:** Accepted · **Affects:** framework registry, the whole shape of the project

### Context

The original scope had four frameworks. Four frameworks at 15% depth each demonstrates
less than one done properly, and a portfolio project is judged on depth.

### Decision

ISO/IEC 27001:2022 is primary and fully assessed. SOC 2 is secondary, reached by mapping
*from* ISO rather than assessed independently. NIST CSF 2.0 and GDPR are registered in a
`ROADMAP` state with the reasoning visible in the UI, and carry **no control catalogue at
all** so nothing can render a progress bar against controls nobody has assessed.

### Alternatives considered

1. **Keep all four.** Rejected: breadth without assurance.
2. **Drop NIST and GDPR entirely.** Rejected: silently dropping a framework looks like an
   oversight. Registering them as not-yet-assessed, with a stated reason, is a scope
   decision rather than a gap.
3. **Score GDPR article by article.** Rejected specifically: GDPR is a legal obligation,
   not a control framework, and "87% GDPR compliant" is not a defensible statement. Two
   operational artefacts are built as real modules instead — the Article 30 RoPA and
   Article 35 DPIAs — and legal obligations enter the ISMS through A.5.31 and A.5.34.

### Consequence

One visible, deliberate gap: **A.5.34 maps to no SOC 2 criterion**, because FinFlow does
not elect the Privacy Trust Services category. It is left visible and asserted in a test
rather than filled with a loose mapping.

> **TODO AUTHOR:BENNY — expand in my own words.**
> "Why not just do SOC 2 as well, everyone asks for it" is a likely challenge.

---

## ADR-006 — The SoA is driven by risk treatment, not by walking Annex A

**Status:** Accepted · **Affects:** Statement of Applicability, all 93 justifications

### Context

There are two ways to produce a Statement of Applicability. Walk Annex A top to bottom and
decide for each control whether it applies — fast, and it produces justifications that
read "required by ISO 27001". Or start from the risk assessment and let treatment
decisions determine which controls are necessary — slower, and it produces justifications
that name a driver.

Clause 6.1.3 asks for the second: controls are *determined* by risk treatment, and Annex A
is then used as a completeness check.

### Decision

Every applicable control's `justification_inclusion` must cite a driver — a linked risk, or
a legal, regulatory or contractual obligation. Circular justifications are **rejected by
pattern**: "required by ISO 27001", "Annex A requires it", "mandated by the standard",
"best practice", "required for certification" all return 422. An inclusion with no linked
risk and no obligation keyword is also refused.

### Alternatives considered

1. **Free-text justification, reviewed by a human.** Rejected: the reviewer is the same
   person under the same deadline, and filler passes review.
2. **Require a linked risk always.** Rejected: some controls are genuinely driven by law or
   contract rather than a register entry. A.5.32 (intellectual property) is the worked
   example — open-source licence terms are the driver, not a risk.
3. **Generate the SoA from the risk-control links automatically.** Rejected: it would
   produce inclusions but not exclusions, and the exclusions are where the judgment is.

### Consequence

Nine exclusions, each naming **where the risk went** rather than merely that the control
does not apply — transferred to AWS under shared responsibility, or redirected to A.6.7,
A.8.3, A.8.16, A.8.24. Six A.7 controls are *kept*, because a remote workforce relocates
physical risk into homes and repair shops rather than removing it. Excluding all fourteen
is the standard remote-first mistake.

> **TODO AUTHOR:BENNY — expand in my own words.**
> "Who approves the SoA, and what happens to an applicable-but-not-implemented control?"
> is on your own prep list. Answer it here.

---

## ADR-007 — A deficient design caps operating effectiveness

**Status:** Accepted · **Affects:** control library, control testing

### Context

Design and operating effectiveness answer different questions and are usually collapsed
into one "effectiveness" rating. Collapsing them destroys the distinction that decides
what to do next: a design deficiency needs the control redesigned, an operating deficiency
needs it enforced. Different work, different owners, different cost.

### Decision

Two independent fields. Operating effectiveness may not be `EFFECTIVE` while design is
`DEFICIENT` — if the control as designed does not achieve the objective, operating exactly
as designed does not achieve it either. Enforced by a 422, a database `CHECK`, and a
refusal to load seed data that violates it.

### Alternatives considered

1. **One combined rating.** Rejected as above.
2. **Bar all operating ratings when design is deficient.** Rejected: a badly-scoped control
   can still run reliably within its scope, and `EFFECTIVE_WITH_EXCEPTIONS` says that
   accurately. The ceiling is a cap, not a ban.
3. **Warn only.** Rejected, same reasoning as ADR-002.

### Consequence

DP-005 is the worked example: the masking job runs every night without failure and covers
only the primary database. Perfect operation, wrong scope. Rating it `EFFECTIVE` would have
hidden a design problem behind an operations metric.

This decision produced the project's most useful cascade. TEST-008 rated DP-005
ineffective, which withdrew a credit RISK-008 was claiming, which pushed that risk above
appetite, which downgraded A.8.11 to a gap, which raised DPIA-001's residual to High —
which triggered an Article 36 consultation obligation. Phase 3's numbers changed because
Phase 4 found something. That is the system working.

> **TODO AUTHOR:BENNY — expand in my own words.**
> This cascade is the strongest thing in the project to walk someone through.

---

## ADR-008 — Optimistic risk bases are surfaced, not blocked

**Status:** Accepted · **Affects:** the Phase 2 / Phase 4 consistency check

### Context

Once controls have tested effectiveness ratings, a risk-control link can claim more
assurance than the control library supports. Two rules were possible: refuse the claim, or
show it.

### Decision

**Hard rule:** a link may not claim a *tested* basis for a control the library records as
never tested. That is fabrication and is refused.

**Soft rule:** a link claiming *more* than the control-level rollup supports is flagged in
the API and the UI, not blocked.

### Alternatives considered

1. **Block both.** Rejected: it would force analysts to record a weaker basis than the
   evidence supports. AC-002 was tested twice against different populations — workforce
   MFA passed clean, privileged MFA found 40% uncovered. RISK-001 is customer account
   takeover, which the privileged exception does not touch.
2. **Flag both.** Rejected: claiming a test that never happened is not a matter of opinion.
3. **Link each risk-control row to a specific test.** Considered seriously, and the most
   correct answer. Rejected for scope: it adds a join and a schema change to solve a
   problem the flag makes visible.

### Consequence

Two flags currently: `RISK-001/AC-002` and `RISK-015/AC-002`. Both are legitimate
population-scoping judgments. Blocking would have forced understatement; hiding would have
let a real overstatement pass. Showing it puts the question in front of a human.

> **TODO AUTHOR:BENNY — expand in my own words.**
> If asked "why not just link the test?", the honest answer is scope — say so.
