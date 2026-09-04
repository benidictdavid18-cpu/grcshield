# Decision records

> **Sample / Portfolio Assessment.** FinFlow Technologies is a fictional company.
> No certification body or audit firm has assessed any of this.

Nine decisions that shaped this project, recorded in the form an architecture decision
record takes: what the situation was, what was chosen, what else was on the table, and
what it cost.

Each record closes with a section headed **In my own words**, which answers the
question that record is most likely to be challenged on. Those sections exist because an
argument you have not written in your own words is an argument you cannot defend when
someone pushes back on it — and every decision here has a version of itself that sounds
reasonable and is wrong.

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

### In my own words

I started with the arithmetic. It was obvious, everyone does it, and it broke on the
fourth risk I wrote.

RISK-004 is compromise of a privileged AWS account. MFA is enforced on 60% of privileged
accounts, so under the percentage model I had a control that was 60% effective and a
residual of 20 × 0.4 = 8. That number said the risk had dropped from Critical to Medium.
But an attacker who phishes one of the six uncovered accounts reaches the entire
production estate and every customer record in it. The consequence had not moved at all.
The only thing MFA changed was how likely it was that someone got in.

That is when I understood that a single percentage cannot express a two-dimensional
judgment. Likelihood 4 to 3, impact unchanged at 5, residual 15. No multiplier produces
that, because a multiplier acts on the product and cannot act on one factor.

**Would I still do it at 200 risks?** Yes, and I would expect to be argued with. The
honest cost is that twenty defensible justifications took real work and two hundred would
take a team. What I would not do is switch to arithmetic to make the volume manageable,
because the volume is not the problem the arithmetic solves — it hides the problem. What
I would add is a review cadence proportionate to band, so that Critical and High risks
get a written justification every cycle and Low ones get one on change. Scaling the
process is a different question from scaling the maths.

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

### In my own words

The challenge is fair and it comes up every time: *the control obviously works, I just
have not tested it yet — are you really going to make my register look worse over
paperwork?*

Two answers, and the second matters more.

The first is that "obviously works" is a prediction, and the ones that turn out to be
wrong are exactly the ones nobody thought worth testing. DP-005 is the example sitting
in this repository. Production data is masked before use in non-production — it was
designed, it was documented, it ran nightly, and it obviously worked. TEST-008 examined
all eleven non-production stores and found two of them holding around 12,000 unmasked
customer records, because the masking job had never covered the analytics warehouse or
the support tooling. Nobody was lying. The control worked perfectly, on the environments
it had been written for, and the world had grown two more.

The second is about what the number is for. A residual score is not a description of how
secure I feel; it is a claim I am asking someone else to rely on. The CTO uses it to
decide where money goes. An auditor uses it to decide whether the ISMS is credible. If I
credit an untested control, I have converted my confidence into their evidence, and they
have no way to tell the difference.

So the register lets you score residual *at* inherent and explain yourself. That is
always permitted. What it refuses is a lower number with nothing behind it. RISK-019 sits
at its inherent level with both controls untested, and the honest reading of that row is
"we have not checked", which is a true statement and a useful one.

There is a cost and I will not pretend otherwise: the register looks worse than the
organisation probably is. I would rather be wrong in that direction.

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

### In my own words

*Who actually sets appetite at a 40-person company?* Realistically: three or four people
in a room, once, and then nobody revisits it. Pretending otherwise would be theatre.

What I think the honest version looks like is that appetite is not really *set* at this
size — it is **discovered and then written down**. The business already behaves as though
it has an appetite. FinFlow runs in one AWS region with no warm standby, which is a
statement about how much continuity risk it will carry, made by whoever signed off the
architecture. The register's job is to name that position, attach the person who owns the
consequence, and put a date on it, so it becomes reviewable instead of ambient.

That is why the approver is per category rather than a single sign-off. The person who
answers for a payment outage is not the person who answers for a personal data breach,
and asking one executive to hold both positions produces a number nobody feels
accountable for. Business Continuity carries the highest appetite in this register, and
the reason is legible: EXC-002 records the CEO accepting single-region operation to
2027-06-30, funded and dated. Data Privacy carries the lowest because the DPO would not
sign anything else.

The rule I care most about here is the one about who cannot approve. Security advises on
risk; it does not get to accept it. A seed check fails the build if any appetite approver
is the security function, because an appetite the security team set for itself is not a
business decision, it is a preference.

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

### In my own words

EXC-004 is the record I would open first, because it is the only one in the register
where the answer was no.

The Head of Engineering requested a time-boxed acceptance of the privileged MFA gap —
RISK-004, the six accounts on legacy password-only paths. The request was reasonable on
its face: remediation was already open, the fix had a date, and an acceptance would have
stopped the risk sitting above appetite in the meantime.

The CTO refused it at management review, and the reasoning is recorded. Accepting a known
privileged access gap while actively seeking certification is not a position you can
defend to an auditor — it reads as knowing about the hole and choosing to keep it. And
the compensating controls named in the request are detective: OP-001 logging and OP-002
monitoring tell you an incident happened and shorten it. They do not stop the credential
working.

What makes this the record worth talking about is that most acceptance registers cannot
hold it. They are built to record approvals, so a refusal has nowhere to live and simply
does not appear — which means the register describes a company that agreed to everything
it was asked. **A register that only records approvals is a record of agreement, not of
decisions.**

The consequence is visible on the dashboard and it is uncomfortable. Because EXC-004 was
refused and EXC-003 expired, all seven risks above appetite currently have no live
acceptance covering them. That number is worse than a register full of tidy approvals,
and it is the truer one: an exposure nobody has agreed to carry is worse than a
documented acceptance, not better.

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

### In my own words

*Why not just do SOC 2 as well — every enterprise buyer asks for it.*

Because "as well" is doing a lot of work in that sentence. SOC 2 is not a second checklist
you tick alongside the first; it is an attestation over a period, performed by a CPA firm,
against criteria you have selected and described. The expensive part is not the controls,
which overlap heavily with Annex A. It is the evidence discipline: a Type II report covers
six to twelve months of operation, so every control has to have been operating, and
provably operating, for the whole window.

FinFlow currently tests 31.4% of its control library within frequency. Committing to a
second framework at that level of maturity would not produce two certifications; it would
produce two half-finished programmes and an auditor in each one asking why the evidence
stops.

So SOC 2 is mapped *from* ISO rather than assessed separately — 61 criteria, 127 typed
mappings, marked equivalent, partial or supporting. That is worth real money to a sales
conversation: it answers "how far are you from SOC 2" with a mapped gap list instead of a
shrug, and it means the work already done counts toward the second framework when the
company decides to do it.

The honest limitation, and I would say it before being asked: a mapping is not an
assessment. Nothing in this application claims FinFlow meets a Trust Services Criterion.
It claims the ISO control that would satisfy it exists and what state it is in, which is
the most a mapping can honestly say.

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

### In my own words

**Who approves it.** The SoA is approved by the ISMS manager and signed off at management
review, and the record carries `approved_by`, `approved_date` and a version. That matters
because the SoA is not a working document — it is a statement the organisation makes,
versioned, that an auditor reads first and holds you to. A document everyone can edit and
nobody signed is a spreadsheet.

**What happens to an applicable-but-not-implemented control.** It becomes a gap, and the
system will not let it be anything else. An entry that is applicable and not fully
implemented must carry at least one remediation item with an owner and a due date, or the
write is refused with a 422. Both fields are NOT NULL, so the rule cannot be satisfied
with an empty promise.

That is the rule I would defend hardest here, because the alternative is the failure mode
every weak SoA has. Marking a control applicable is easy and costs nothing. Marking it
*not implemented* is honest. Doing both and then leaving the row alone is how a control
stays open for two years while the document continues to assert it is in scope — the
organisation has written down that it needs the control and taken no position on when it
will have it.

There are 29 such gaps in this SoA and every one has a name and a date against it. The
uncomfortable consequence is a remediation register with real overdue items in it, which
is the point: the gap is not the problem, the untracked gap is.

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

### In my own words

This is the walkthrough I would give, because it is the only part of the project where
you can watch a single fact move through six modules and change the answer in all of
them.

TEST-008 tested DP-005, production data masking, across all eleven non-production stores.
Two of them — the analytics warehouse and the support tooling — held unmasked customer
records, roughly 12,000 of them. The test concluded FAIL.

Then everything downstream moved on its own:

- **The control library.** DP-005 was rated design-deficient, not just
  operating-ineffective. The masking job runs perfectly on the database it covers; the
  problem is that it was never written to cover the other two. That distinction decides
  the remediation — you cannot fix a scope gap by making the job more reliable.
- **The risk register.** RISK-008 lost the reduction it had been carrying, because the
  control it leaned on may no longer be credited.
- **RISK-018** went back to its inherent level entirely, since DP-005 was the only linked
  control addressing curiosity-driven browsing.
- **The SoA.** A.8.11 went from implemented to a gap.
- **The GDPR records.** ROPA-003 lists DP-005 among its Article 30(1)(g) security
  measures, and the API now returns `credited: false` on it. DPIA-001 was reassessed from
  medium to high residual — and Article 36(1) then forced the outcome to change with it,
  because a DPIA showing high residual risk after mitigation requires consulting the
  supervisory authority before proceeding.
- **The dashboard.** KRI-003 fell from 66.7% to 65.5%. It had risen for five straight
  months. A stored metric would have kept climbing.

The line I would end on: **one test result, and the number on the board went down.** That
is what "the modules are connected" actually means, and it is the difference between a
system that enforces a methodology and a set of forms that happen to sit in the same
database.

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

### In my own words

*Why not just link each risk-control row to the specific test that supports it?*

Because that is the right answer and I did not build it. I want to say that plainly rather
than construct a principle around a scope decision.

It would work like this: RISK-001 links to AC-002 on the basis of TEST-002, which tested
workforce MFA and passed clean. RISK-004 links to the same control on the basis of
TEST-003, which tested the privileged population and found 40% uncovered. Same control,
two populations, two genuinely different levels of assurance — and with the test attached
there is no ambiguity to flag, because the evidence for each claim is named.

What stopped me was that it needs a schema change, a join, and a decision about what
happens when a link's test is superseded or withdrawn, to solve a problem the optimism
flag already makes visible. Two links are flagged today, RISK-001/AC-002 and
RISK-015/AC-002, and both turn out to be legitimate population-scoping judgments. The flag
put the question in front of a human and the human answered it.

The reason I flag rather than block is separate and I do stand behind it. Blocking would
force the analyst to record a *weaker* basis than their evidence supports, and a register
that systematically understates assurance is not more honest than one that overstates it
— it is just wrong in the flattering-to-nobody direction. Claiming a test that never
happened is different, and that is refused outright.

If this were going further, linking the test is the first thing I would build.

---

## ADR-009 — The assistant advises; it cannot decide

**Status:** Accepted · **Affects:** the whole AI layer

### Context

A GRC tool with a language model in it has one interesting question and it is not
"which model". It is: what happens when the model is wrong, and confident, and the
person reading it is tired at 5pm on a Friday.

The failure that matters is not a bad suggestion. It is a suggestion that reaches a
register without a person having agreed to it — an AI-drafted finding that becomes the
finding, a suggested control that becomes an applicability decision, a proposed score
that becomes the residual. Every one of those would be indistinguishable, in the
database, from a judgment somebody made and could defend.

### Decision

The assistant reads records and returns text beside them. It writes to exactly one
table, `ai_interactions`, which is an activity log and not part of the management system.

Enforced in three independent places, deliberately not in the prompt:

1. **The response schema has no field capable of carrying a decision.** No likelihood,
   impact, score, band, conclusion, design or operating effectiveness, severity, status,
   approval, owner or date. The assistant has no vocabulary for a GRC decision.
   `test_no_ai_response_model_can_express_a_grc_decision` walks every field of every
   response model and fails the build if one appears.
2. **There is no code path to a register write.**
   `test_the_assistant_changes_no_grc_record` calls all seven endpoints and compares
   eight register endpoints byte for byte before and after.
3. **Output guardrails run over the model's own words.** A claim of compliance,
   certification, verification or a test verdict is flagged to the analyst and recorded
   in the log — flagged, not censored, on the same reasoning that surfaces an optimistic
   effectiveness basis rather than blocking it. Visible beats silent.

### Alternatives considered

1. **Let the AI pre-fill fields the analyst then edits.** Rejected, and this is the
   real decision. A pre-filled field is accepted far more often than it is edited; that
   is the entire commercial argument for autofill. Applied to a residual justification
   it produces a register full of text nobody wrote and nobody can defend — which is the
   exact failure ADR-001 exists to prevent. The assistant returns a draft the analyst
   has to move across deliberately.
2. **Ask the model, in the prompt, not to make decisions.** Rejected as the *only*
   control. A prompt is a request. It belongs in the system, and it is there, but a
   request is not an enforcement point.
3. **A hosted model API.** Rejected on the grounds this project would apply to any other
   supplier. An ISMS is a catalogue of an organisation's weaknesses; sending it to a
   third party is a processing activity needing a lawful basis, a RoPA entry, a transfer
   assessment and a supplier review. Local inference removes the question instead of
   answering it.
4. **Store the prompt and response in the log.** Rejected. Every prompt is assembled
   from records this database already holds under their own access control, and a second
   copy in a log table adds exposure without adding assurance. A truncated response
   digest ties a kept suggestion back to its interaction without retaining either text.

### Consequence

The assistant is less immediately impressive than one that fills the form in. That is
the trade, and it is the right way round for this application: the value here was never
the text, it was that every number in the register has a person behind it.

It also changed what the feature is for. The first version was a writer — draft this,
summarise that — and a writer that cannot decide anything feels close to pointless, which
is a fair criticism and was made. The answer was to use it as a **reviewer** instead. The
consistency sweep reads every record that leans on one control and reports where they
disagree; TEST-008 rated DP-005 ineffective while ROPA-003 still names it as a security
measure, and no validation rule generalises that because the rule would have to be
written once per pair of record types.

Reviewing is the better fit for three reasons. It is what a language model is genuinely
good at, where drafting is a commodity. A wrong flag costs thirty seconds, where a wrong
draft that gets accepted costs a defensible register. And "cannot decide" stops being a
limitation: a reviewer's job *is* to raise the question and leave it open.

Two costs worth stating. The AI router is mounted on `current_user` rather than
`require_write`, because `require_write` decides what is a mutation by HTTP method and
these POSTs mutate nothing — a departure from a rule this project otherwise applies
uniformly. And the whole feature depends on a model good enough to be useful: control
mapping asks a model to select from 93 Annex A controls, and a 3B model does it
inconsistently.

### In my own words

*So what does it actually add, if it cannot do anything?*

The first version deserved that question. It drafted risk statements and summarised
records, and a drafting assistant that cannot decide anything is close to a text box with
extra steps. Every tool has one.

The answer is that I was using it for the wrong job. **It is a reviewer, not a writer.**

Here is the case it is for. TEST-008 rated DP-005 ineffective. ROPA-003 — the GDPR
processing record for support ticket handling — still lists DP-005 among its Article
30(1)(g) security measures. Those two records cannot both be describing the world. And
the second one is not an internal note: a RoPA entry is a statement about how personal
data is protected, and it currently names a protection that is not operating.

No validation rule catches that. I could write one for this exact pair, and then another
for tests against BIA recovery assumptions, and another for findings against SoA
implementation status — a rule per pair of record types, forever, and the contradictions
that matter are the ones nobody predicted. Reading a dozen records written by different
people at different times and noticing that two of them have drifted apart is
comprehension work. It is the thing a language model is genuinely good at and the thing a
rule engine genuinely cannot do.

And "it cannot decide" stops being a limitation the moment you use it this way. A reviewer
is *supposed* to raise the question and leave it open. The sweep reports which records
disagree and what it would ask; which one is right — and often neither is, because the
world moved and only one got updated — is mine to settle.

The economics are also the right way round. A wrong flag costs me thirty seconds of
reading. A wrong draft that someone accepts costs me a register I cannot defend.
