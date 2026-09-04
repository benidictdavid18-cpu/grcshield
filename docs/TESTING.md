# Control testing and the ISMS clause records

> **Sample / Portfolio Assessment.** FinFlow Technologies is a fictional company.
> No certification body or audit firm has assessed any of this. No audit was performed;
> every workpaper below is illustrative.

## Why effectiveness is two fields

An auditor asks two separate questions about every control, in this order:

1. **Design** — if this control operated exactly as written, would it achieve the
   objective?
2. **Operating** — did it actually run, over a period, as designed?

Collapsing them into one "effectiveness" rating destroys the distinction that decides
what to do next. A design deficiency needs the control **redesigned**; an operating
deficiency needs it **enforced**. Different work, different owners, different cost.

**DP-005 is the worked example.** The masking job runs every night without failure — and
covers only the primary application database. It was never pointed at the analytics
warehouse or the support replica, both of which held real customer records. Perfect
operation, wrong scope. That is a design deficiency, and no amount of reliable execution
fixes it.

### The rule

> Operating effectiveness may not be `EFFECTIVE` while design effectiveness is
> `DEFICIENT`.

If the control as designed does not achieve the objective, then operating exactly as
designed does not achieve it either. The ceiling is `EFFECTIVE_WITH_EXCEPTIONS`.

Enforced three ways: a 422 on the API, a `CHECK` constraint in migration 0004, and a
refusal to load seed data that violates it.

| Design | Operating |
| --- | --- |
| `NOT_ASSESSED` | `NOT_TESTED` |
| `EFFECTIVE` | `EFFECTIVE` |
| `DEFICIENT` | `EFFECTIVE_WITH_EXCEPTIONS` |
| | `INEFFECTIVE` |

## Workpapers

Twelve tests: **8 PASS, 3 PASS_WITH_EXCEPTIONS, 1 FAIL**, covering 11 of 35 controls
(31%). The remaining controls are rated from configuration review and monitoring rather
than sample testing — which is what a risk-based audit programme actually looks like at
this headcount, and is stated rather than disguised.

Every workpaper records objective, procedure, population, sample, **sampling rationale**,
results, exceptions, conclusion and reviewer.

### Sampling rules, enforced

- Sample size cannot exceed the population.
- `FULL_POPULATION` means sample size equals population size.
- **A sampling rationale is mandatory.** "How did you choose the sample?" is the first
  question an auditor asks, and a sample without an answer is an opinion.
- Exceptions and conclusions must agree in both directions: exceptions with a clean
  `PASS` is rejected, and `PASS_WITH_EXCEPTIONS` with zero exceptions is rejected.
- Exceptions must be described, not merely counted.
- **The reviewer cannot be the tester.** A workpaper reviewed by its own author has not
  been reviewed, and preparer/reviewer segregation is one of the few segregation controls
  a 40-person company can still operate.

Every sampling rationale is written. Four were held back until last — **TEST-003,
TEST-005, TEST-008 and TEST-011** — because each defends a choice rather than describing
one.

TEST-011 is the uncomfortable one. The sample was weighted toward critical and high
severity, and all three exceptions turned out to be in medium, the band deliberately
under-sampled. The rationale argues the weighting was still right, and then concedes what
follows from it: the test can say the tightest SLAs hold, and it cannot estimate the
medium exception rate at all. Three exceptions in 24 sampled from 403 supports no
projection. The honest next step is a separate test, not a re-reading of this one.

## The cascade

A conclusion of `FAIL` or `PASS_WITH_EXCEPTIONS` **auto-creates** a draft audit finding
and a remediation item linked back to the test. There is no field to opt out. A test that
found something and reported nothing is worse than no test.

The finding is created as **DRAFT** deliberately: the system observed a fact, but whether
it is a finding worth raising, and at what severity, is a human judgment.

### TEST-008, end to end

This is the phase's most useful result, because it changed numbers in two earlier phases:

```
TEST-008 (DP-005, FAIL, 2 of 11 non-production stores hold real customer data)
  → DP-005 rated design DEFICIENT / operating INEFFECTIVE
  → FIND-003 (HIGH) → REM-017, Head of Engineering, due 2026-10-30
  → NC-002 raised under Clause 10.2
  → RISK-008's DP-005 basis drops to TESTED_INEFFECTIVE and earns no credit
  → RISK-008 residual 4 → 8, crossing the Data Privacy ceiling of Low
  → A.8.11 downgraded from Implemented to a gap
```

Phase 3 reported 56 implemented controls, 28 gaps and 5 risks above appetite. After
testing: **55 implemented, 29 gaps, 6 above appetite.** Those numbers moved because
testing found something, which is the entire point of testing. The change is asserted in
`test_a_failed_test_propagates_to_the_risk_register_and_the_soa`.

## Optimistic bases, surfaced not blocked

A risk-control link **may not** claim a tested basis for a control the library records as
never tested — that is a hard rule.

A link claiming *more* assurance than the control-level rollup supports is **flagged, not
blocked**. Two exist: `RISK-001/AC-002` and `RISK-015/AC-002`, both recording
`TESTED_EFFECTIVE` while AC-002 sits at `EFFECTIVE_WITH_EXCEPTIONS` overall.

That is legitimate here. AC-002 was tested twice against different populations: TEST-002
covered workforce MFA and passed clean; TEST-003 covered privileged accounts and found
40% uncovered. RISK-001 is customer account takeover — the privileged exception does not
touch it. Blocking this would force analysts to record a weaker basis than the evidence
supports; hiding it would let a real overstatement pass. So it is shown.

## ISO clause records

| Clause | Record | Count |
| --- | --- | --- |
| 9.2 | Internal audit programme | 3 (1 complete, 1 in progress, 1 planned) |
| 9.3 | Management review | 2 |
| 10.2 | Nonconformity and corrective action | 3 (1 closed) |

**Clause 9.2 — independence.** Every audit records how independence was achieved, because
at forty people it often cannot be. AUD-003 is explicitly assigned to an external
consultant "because no internal person is independent of the ISMS as a whole." A seed
check fails if an independence note is under 25 words.

**Clause 9.3 — inputs.** Both reviews enumerate the Clause 9.3.2 inputs (a) through (f)
explicitly, and a seed check fails if any marker is missing. MR-2026-H1 records a real
decision: RISK-003 accepted, RISK-004 **rejected** for acceptance, with the CTO's reason
recorded — accepting a privileged access gap while seeking certification is not
defensible.

**Clause 10.2 — correction vs corrective action.** These are separate fields on purpose.
A *correction* fixes the instance; *corrective action* eliminates the cause so it does not
recur. NC-002 shows both: the support replica was rebuilt from masked data (correction),
and a masking-scope check was added to environment provisioning so the gap cannot reappear
with the next environment (corrective action).

A nonconformity **cannot be closed without an effectiveness check result** — Clause 10.2
d) requires a review of whether the action worked. Enforced by a `CHECK` constraint and by
the seed loader.

## Reports

`GET /isms/records.pdf` exports the clause records. It is deliberately **not** in the
report registry: the three reports each support a named decision for a named audience,
and this is a records bundle. Adding it would put a fourth entry in a report set that was
cut to three on purpose.
