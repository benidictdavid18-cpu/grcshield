# Statement of Applicability

> **Sample / Portfolio Assessment.** FinFlow Technologies is a fictional company.
> No certification body or audit firm has assessed any of this.

Required by **ISO/IEC 27001:2022 Clause 6.1.3 d)**. The SoA is the document a
certification auditor opens first, because it is where the organisation commits, in
writing, to which Annex A controls apply and why.

## Current state

| | |
| --- | --- |
| Entries | 93 — one per Annex A control, always |
| Applicable | 84 |
| Excluded | 9 |
| Implemented | 55 |
| Partially implemented | 20 |
| Not implemented | 9 |
| **Implemented** | **65.5% of applicable controls** |
| Gaps | 29 |
| Version | 1.0, approved by the Chief Executive Officer on 2026-05-15 |

**Percent implemented is calculated over applicable controls, not all 93.** Counting
excluded controls as unimplemented understates readiness; counting them as implemented
overstates it. Neither is true — they are simply not in scope.

## Who approves it

Top management, not the security function. ISO/IEC 27001:2022 Clause 5.1 places
accountability for the ISMS with leadership, and the SoA records what leadership has
accepted. In GRCShield that is the Chief Executive Officer, and every entry carries
`approved_by`, `approved_date` and `version`.

## The three rules, enforced server-side

Each returns **422** with the offending field named. The whole entry is revalidated
after any change, not only the fields supplied, so an edit cannot leave an entry
internally inconsistent.

### 1. Applicable requires a justification that names a driver

Clause 6.1.3 d) asks why a control is *necessary*. Two failure modes are rejected:

**Circular justifications.** "Required by ISO 27001" explains nothing about FinFlow —
it is the single most common filler in a weak SoA. Variants like "Annex A requires it",
"mandated by the standard", "best practice" and "required for certification" are all
rejected by pattern.

**Justifications with no driver.** An inclusion justification must either link at least
one risk, or reference a legal, regulatory or contractual obligation. A.5.32
(Intellectual property rights) is the worked example of the second route: open-source
licence terms and customer contractual warranties are the driver, not a risk register
entry.

### 2. Excluded requires an exclusion justification, and forces NOT_IMPLEMENTED

A control declared out of scope cannot simultaneously be implemented. Flipping
applicability to false without restating the status sets it to `NOT_IMPLEMENTED`
automatically rather than rejecting the request — the rule is a rule, not a trap.

There is also a database `CHECK` constraint, so the invariant holds regardless of write
path.

### 3. A gap requires remediation with an owner and a due date

Applicable and not fully implemented is a **gap**. Every gap must link at least one
remediation item that is not cancelled. `owner` and `due_date` are `NOT NULL` on
`remediation_items` by design — a remediation item without someone accountable and a
date is a wish, and the rule would otherwise be satisfiable by an empty promise.

All 29 current gaps satisfy this, and the seed loader runs the same validator the API
uses. Seed data that would be rejected on a write cannot be loaded, so the SoA cannot
ship already breaking its own rules.

## The traceability chain

The reason the SoA is worth building rather than writing in a spreadsheet:

```
Risk → Treatment decision → Internal control → SoA entry
     → Evidence → Test result → Gap → Remediation → Residual risk
```

**A.8.5 (Secure authentication)** is the worked example end to end:

| Step | Value |
| --- | --- |
| Risk | RISK-004 — privileged AWS compromise, residual 15 (High) |
| Treatment | Mitigate |
| Internal control | AC-002 — MFA enforced via Okta |
| SoA entry | A.8.5, applicable, partially implemented |
| Evidence | EV-002 — MFA enrolment report showing **60% privileged coverage** |
| Test result | TEST-003 — full population of 15, 6 exceptions, Pass with exceptions |
| Gap | 6 of 15 privileged accounts on legacy password-only paths |
| Remediation | REM-001, Head of Engineering, due 2026-10-31 |
| Residual risk | 15 (High) vs Cybersecurity ceiling of Medium — **above appetite** |

The chain is complete as of Phase 4. TEST-003 also raised FIND-001 and NC-001, so the
same weakness is traceable from the workpaper through to the corrective action recorded
under Clause 10.2 — see [TESTING.md](TESTING.md).

**One entry moved because of testing.** A.8.11 (Data masking) was Implemented until
TEST-008 found unmasked customer data in two non-production stores; it is now a gap
carrying REM-017. That is why the counts above differ from Phase 3's.

## Exclusions: where the risk went

Nine controls are excluded, matching the Phase 1 scope decision exactly (the seed check
fails if they ever diverge). Each justification names a **destination** for the risk,
not merely an absence:

| Control | Where the risk went |
| --- | --- |
| A.7.1, A.7.2, A.7.11 | Transferred to AWS under the shared responsibility model; assured via SOC 2 Type II, reviewed annually under TP-001 and TP-002 |
| A.7.3 | Retained and managed through A.6.7 (Remote working) and A.7.9 (Assets off-premises) |
| A.7.4 | Replaced by logical monitoring under A.8.16 |
| A.7.5 | AWS responsibility; availability consequence retained under A.8.14 and RISK-007, accepted at CEO level |
| A.7.6 | Enforced logically through A.8.3 |
| A.7.12 | Retained and addressed by A.8.24 (cryptography) |
| A.8.30 | No outsourced development exists; third-party *code* risk retained under A.5.21 and A.8.28 as RISK-011 |

Six A.7 controls are **kept** — A.7.7, A.7.8, A.7.9, A.7.10, A.7.13, A.7.14 — because a
remote workforce relocates physical risk into homes and repair shops rather than
removing it. Excluding all fourteen is the standard remote-first mistake.

## Assurance quality signals

The overview reports four things most SoA tools do not, because each is a way a
green-looking SoA can still be hollow:

- **Implemented without evidence** (currently 0). An implemented control with no
  artifact is an assertion, not a control.
- **Expired evidence** (currently 3). EV-023, the AWS SOC 2 Type II report, has expired
  — which means eight of the nine exclusion justifications are *temporarily
  unsupported*. That is stated in the entries rather than hidden.
- **Overdue remediation** (currently 2 — REM-006 and REM-017).
- **Justifications outstanding** (currently 8).

## Outstanding for the author

Eight inclusion justifications are deliberately unwritten, marked `TODO AUTHOR:BENNY`
with a one-line hint about what must be decided:

**A.5.7, A.5.15, A.5.23, A.6.3, A.8.5, A.8.12, A.8.16, A.8.28**

Two of them are the hard ones. A.5.23 carries the weight of all nine A.7 exclusions —
it has to state what FinFlow retains under shared responsibility and what it does not.
A.8.12 asks whether DLP is proportionate for a 40-person company at all, or whether
A.8.3 and A.8.11 already carry the load; arguing it is disproportionate is a legitimate
answer if it is argued.

## Report

`GET /soa/report.pdf` renders the **SoA + Gap Analysis Report**: overview, assurance
quality signals, coverage by theme, all 93 entries with gaps and exclusions shaded, and
a gap analysis table with owners and due dates. The portfolio disclaimer is stamped on
every page.
