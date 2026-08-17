# Risk methodology

> **Sample / Portfolio Assessment.** FinFlow Technologies is a fictional company.
> No certification body or audit firm has assessed any of this. Every score below is
> illustrative.

## The assessment chain

Every risk on the register is produced by walking the same chain. Nothing enters the
register another way, and each step is a stored field rather than reasoning that
happened once in someone's head.

```
Asset → Threat → Vulnerability → Likelihood ─┐
                                             ├→ Inherent risk
                                    Impact ──┘
      → Controls (with an effectiveness basis)
      → Residual risk (likelihood and impact scored independently)
      → Appetite comparison (by band, per category)
      → Treatment decision
```

### RISK-004, walked

| Step | Value |
| --- | --- |
| **Asset** | AWS production account (eu-west-1) and all customer data within it |
| **Threat** | Credential theft through phishing or endpoint compromise, then privilege use |
| **Vulnerability** | MFA enforcement on privileged roles is incomplete; legacy paths bypass the Okta sign-on policy |
| **Likelihood** | 4 — phishing against a fully remote workforce is routine, and six accounts need only a password |
| **Impact** | 5 — a privileged compromise reaches the entire production estate |
| **Inherent risk** | 4 × 5 = **20, Critical** |
| **Controls** | AC-002 (tested with exceptions), AC-003 (design only), OP-002 and AC-004 (tested effective) |
| **Residual** | 3 × 5 = **15, High** — likelihood moves, impact does not |
| **Appetite** | Cybersecurity ceiling is Medium → **above appetite** |
| **Treatment** | Mitigate. REM-001, Head of Engineering, due 2026-10-31 |

The interesting line is the residual. Impact stays at 5 because **no access control can
reduce it** — MFA changes who gets in, not what they reach once inside. Likelihood moves
only from 4 to 3 because AC-002 was tested at 60% coverage, so partial coverage earns
partial credit. Neither of those judgments is expressible as a percentage applied to a
single number, which is the whole argument of the next section.

## Vocabulary

Terms that get used loosely and mean specific things here.

**Inherent risk** — the exposure before any control is considered. Not "worst case", and
not "what would happen if every control failed at once": it is the risk the business
would carry if it had simply never built the control.

**Residual risk** — the exposure that remains after the controls that actually operate.
Scored directly, never derived. *Example:* RISK-004 inherent 20, residual 15.

**Risk appetite** — the level of exposure the business has decided in advance it is
willing to carry, set per category and approved by the person who answers for the
consequence. **Risk tolerance** is the variation around that which is acceptable in a
specific case before someone must act. Appetite is a standing position; tolerance is how
much a single instance may deviate from it. GRCShield models appetite explicitly and
handles tolerance through the acceptance register — a formal, expiring exception *is* a
tolerated deviation, with a name attached to it.

**Design effectiveness** — if this control operated exactly as written, would it achieve
its objective? *Example:* DP-005 masks the primary application database and nothing else,
so as designed it cannot protect the analytics warehouse. Design: **deficient**.

**Operating effectiveness** — did it actually run, over a period, as designed? A control
can be perfectly designed and simply not happen. These are separate fields because they
fail differently and are fixed by different work: a design deficiency needs the control
redesigned, an operating deficiency needs it enforced.

**The four treatment options**, each with a real example from the register:

| | What it means | Example |
| --- | --- | --- |
| **Mitigate** | Reduce likelihood or impact by doing something | RISK-004 — enforce MFA on the remaining privileged accounts |
| **Transfer** | Move the consequence to someone else, usually by contract or insurance | RISK-013 — fraud liability sits with the payment service provider |
| **Accept** | Carry it deliberately, with an expiry and a named approver | RISK-007 — single-region operation, accepted by the CEO to 2027-06-30 |
| **Avoid** | Stop doing the thing that creates the risk | Not used in this register — worth saying so rather than inventing one |

Transfer is the one most often misused. It moves the *financial* consequence, not the
accountability: RISK-010's justification says so explicitly, because FinFlow remains
controller for data a vendor loses.

## Standards this follows

| Standard | Used for |
| --- | --- |
| ISO/IEC 27001:2022 | Clause 6.1.2 risk assessment, Clause 6.1.3 risk treatment |
| ISO/IEC 27005 | Risk identification, analysis and evaluation within an ISMS |
| NIST SP 800-30 Rev. 1 | Likelihood × impact analysis and the risk determination step |
| ISO 31000 | Governance framing: appetite, ownership, treatment decisions |
| AICPA SOC 2 TSC | Secondary mapping target only — not independently assessed |

## The scale

Likelihood and impact are each scored 1–5, giving a score of 1–25 on a 5×5 matrix.

| Band | Score |
| --- | --- |
| Low | 1–4 |
| Medium | 5–9 |
| High | 10–16 |
| Critical | 17–25 |

Every achievable product of two values in 1–5 falls into exactly one band; this is
asserted in `backend/tests/test_risk_scoring.py`.

## Why residual is scored independently

A very common shortcut computes:

```
residual = inherent × (1 − control_effectiveness)
```

GRCShield does not do this. The model is wrong for three reasons.

**It collapses two dimensions into one.** Controls do not reduce "risk" — they reduce
*likelihood* or *impact*, and usually only one of them. MFA makes credential compromise
less likely and does nothing to the blast radius once an attacker is inside. A backup
does nothing to likelihood and everything to impact. A single score multiplied by a
single percentage cannot express that difference, so it silently misstates which
dimension was actually treated.

RISK-004 is the worked example. Inherent is 4 × 5 = 20 (Critical). Residual is 3 × 5 =
15 (High). **Impact does not move at all** — a privileged compromise reaches the whole
production estate regardless of how the attacker got there. No arithmetic model
producing a single output number could represent that.

**A single "effectiveness percentage" is not measurable.** Nobody can defend the
difference between a control that is 70% effective and one that is 75% effective. That
invented number then drives what the board sees.

**It makes residual risk non-falsifiable.** If residual is derived, an analyst can never
disagree with it and an auditor can never challenge it. Scoring residual directly forces
a human to commit to a position and write down why.

So: the analyst sets `residual_likelihood` and `residual_impact` directly, and must
supply a `residual_justification` naming which control moved which dimension. The API
rejects an empty justification with 422. The system computes bands and compares against
appetite; it does not compute the judgment.

## Control effectiveness basis

Each risk-to-control link records **how much is actually known** about the control. This
is evidence provenance, not a quality score — it answers the first question an auditor
asks, which is "on what basis do you claim this works?"

| Basis | Meaning | May be credited? |
| --- | --- | --- |
| `NOT_TESTED` | No evidence gathered | **No** |
| `DESIGN_ONLY` | Design assessed, operation not tested | Yes, weakly |
| `TESTED_EFFECTIVE` | Tested over a period, operates as designed | Yes |
| `TESTED_WITH_EXCEPTIONS` | Operates, but with exceptions | Yes, partially |
| `TESTED_INEFFECTIVE` | Tested and found not to operate | **No** |

### Untested controls earn no credit

A control that has never been tested provides no assurance, only intent. Crediting it
with a residual reduction converts an assumption into a number and then reports that
number as fact.

The rule is enforced server-side, not merely displayed as a warning: if a proposed
residual score is below inherent and no linked control may be credited, the API returns
422. Scoring residual *at* the inherent level is always allowed — the rule blocks
unearned reductions, not honest ones.

RISK-019 is the worked example. Both linked controls are `NOT_TESTED`, so residual (9)
equals inherent (9), and the register says so rather than quietly claiming improvement.

### One deliberate extension

The brief for this phase requires `NOT_TESTED` to be non-crediting. GRCShield also
treats `TESTED_INEFFECTIVE` as non-crediting, on the same reasoning taken one step
further: a control tested and found to have failed provides *less* assurance than one
never tested, because the failure is now a known fact rather than an open question.
Crediting it would be indefensible in an audit.

This is a judgment call beyond the literal requirement. It lives in one named constant,
`NON_CREDITING_BASES` in `backend/app/services/risk_scoring.py`, and can be narrowed to
`NOT_TESTED` alone by editing that set.

### The basis must be supported by the control library

From Phase 4, a risk-control link may not claim a *tested* basis for a control the
control library records as never tested. A link claiming more assurance than the
control-level rollup supports is flagged rather than blocked — see
[TESTING.md](TESTING.md#optimistic-bases-surfaced-not-blocked).

## Risk appetite is per category

A single organisation-wide appetite says the business tolerates the same exposure to a
privacy breach as to a laptop running an old OS. It does not, and pretending otherwise
makes the appetite line meaningless.

| Category | Ceiling | Approved by |
| --- | --- | --- |
| Cybersecurity | Medium | Chief Technology Officer |
| Data Privacy | **Low** | Data Protection Officer |
| Third-Party | Medium | Chief Operating Officer |
| Operational | Medium | Chief Operating Officer |
| Financial | **Low** | Chief Financial Officer |
| Legal | Medium | Head of Legal & Compliance |
| Compliance | **Low** | Head of Legal & Compliance |
| Business Continuity | **High** | Chief Executive Officer |
| Technology | Medium | Chief Technology Officer |

Two things to notice. Business Continuity carries the *highest* appetite deliberately —
FinFlow's recovery objectives are measured in hours, not the minutes an incumbent bank
commits to, and buying that down means multi-region spend the company has chosen not to
make. And **no approver is the security function**: security advises on risk, the
business accepts it.

A missing threshold returns `null`, not `false`. An undefined appetite is an unanswered
governance question, and rendering it as "within appetite" would answer it in the
reassuring direction.

## Comparison is by band, not score

A residual score of 10 (High) breaches a Medium ceiling; 9 (Medium) does not, despite
being one point away. This is intentional — bands are the unit the business agreed to,
and reintroducing point precision at the comparison step would smuggle back the false
accuracy the bands exist to remove.

## Current state

Five of the twenty residual justifications are deliberately unwritten, marked
`TODO AUTHOR:BENNY`: RISK-002, RISK-007, RISK-011, RISK-014 and RISK-018. They are the
author's to write and are flagged in both the API and the UI rather than filled with
plausible-sounding text.

**Seven** risks currently sit above their category appetite: RISK-002, RISK-004,
RISK-008, RISK-009, RISK-010, RISK-018 and RISK-019.

**Two of those seven arrived the same way**, and both trace to a single control test.

**RISK-008** previously claimed a reduction to residual 4, on the basis that DP-005 masked
the records support staff see. TEST-008 found the support replica holding roughly 12,000
unmasked customer records. DP-005 was rated `TESTED_INEFFECTIVE`, the credit was
withdrawn, and the residual moved to 8 — above the Data Privacy ceiling of Low.

**RISK-018** was re-scored for the same reason, and it is the more interesting of the two.
Its threat statement covers two modes: deliberate misuse by an authorised engineer, and
curiosity-driven browsing. DP-005 was the only control addressing the second mode — if raw
data is not visible by default, idle browsing returns nothing. What remains either detects
after the fact (OP-001 logging) or manages access the engineer legitimately holds (AC-003,
AC-004).

The reduction previously claimed there rested on deterrence: people who know they are
logged are less likely to misuse access deliberately. That argument is defensible in
general, and it was rejected here for consistency — **this register does not credit what it
cannot evidence**, which is the same principle that refuses credit to untested controls.
Deterrence is unmeasurable, and crediting it would be the exact move rejected in
[ADR-002](DECISIONS.md#adr-002--untested-controls-earn-no-residual-reduction).

So residual returned to inherent at 12, and RISK-018 crossed the Operational ceiling of
Medium. The register now demands a treatment decision or a signed, expiring acceptance,
where before it said "within appetite, nothing to do" about a risk whose only preventive
control was broken.

See [TESTING.md](TESTING.md) for the full cascade.

## Limitations

Read this section before drawing any conclusion from anything above it.

**FinFlow Technologies does not exist.** It is a fictional company invented for a
portfolio project. There is no product, no merchant, no AWS account, no data.

**No audit has been performed.** No certification body, audit firm or supervisory
authority has assessed this ISMS, and none has been engaged. The internal audit records
under Clause 9.2, the control test workpapers, the management review minutes and the
nonconformities are all written artefacts illustrating what those records look like —
they document activity that did not happen.

**Every rating is illustrative.** Likelihood and impact scores, control effectiveness
ratings, appetite ceilings, exception approvals and DPIA outcomes are all judgments made
to populate a realistic register. They are internally consistent and defensible as
reasoning; they are not measurements of anything.

**The financial figures are invented.** The business impact analysis quotes hourly and
weekly loss figures. They are plausible orders of magnitude for a company of this
described size, and nothing more.

**Some judgments are deliberately unmade.** Roughly 25 fields carry the literal marker
`TODO AUTHOR:BENNY`: five residual justifications, eight SoA inclusion justifications,
four sampling rationales, and the decision records in
[DECISIONS.md](DECISIONS.md). These are left blank on purpose rather than filled with
plausible text, because a justification the author cannot defend in conversation is worse
than an obvious gap. Both the API and the UI flag them.

**The tooling is a demonstration, not a product.** There is no multi-tenancy, no audit
log of user actions, no evidence file storage, no rate limiting, and the demo credentials
are published. See [SECURITY.md](../SECURITY.md) for the full list of known gaps.

**What is real**: the ISO/IEC 27001:2022 Annex A control identifiers and titles, the SOC 2
Trust Services Criteria references, the clause numbers cited throughout, and the
methodology reasoning. Those were the point of the exercise.
