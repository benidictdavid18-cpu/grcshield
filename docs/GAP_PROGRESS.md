# Phase 3 implementation progress

**Sample / Portfolio Assessment** — fictional FinFlow Technologies.

The ranked assessment in GAP_ASSESSMENT.md remains the Phase 2 snapshot. This file
tracks subsequent implementation, including remaining author work and verification.

| Gap | State | Evidence and remaining work |
|---|---|---|
| G01 | Implemented; author proof tasks remain | Migration 0010; workpaper bindings, dispositions, runtime reassessment queue; nine new tests. Claims with no workpaper remain visibly MISSING with an author hint. UI workflow integration follows in Phase 4. |
| G02 | Implemented; authority assignment required | Migration 0011; verified decisions and history, expiring authority, pending/imported coverage refusal; eight new tests. No business authority invented for demo accounts. |
| G03 | Implemented | Migration 0012; one-time bootstrap, preservation on upgrade/restart, explicit local reapplication with reason and operator trail; six new tests. |
| G04 | Implemented; context judgments remain draft | Migration 0013; context and party/process records, review lifecycle, frozen scope snapshots; seven new tests. Seed owners, relevance and scope boundaries carry explicit author hints. |
| G05 | Implemented; sample policy content remains an author task | Migration 0014; retained text revisions, approvals, publication/supersession, download integrity and acknowledgements; eight new tests. |
| G06 | Implemented; original artifacts must be supplied | Migration 0015; bounded artifact storage, authenticated retrieval, digest verification, access scope, retention/hold and purge trail; eleven new tests. No invented seed files. |
| G07 | Implemented; source release awaits author review | Migration 0016; immutable 93-control snapshots, authorized sign-off, diff, evidence-limitations acknowledgement and draft-aware UI/PDF; eight new tests. |
| G08 | Implemented; sample commitments await author agreement | Migration 0017; resources, milestones/dependencies, business approval, evidence-backed closure and database-enforced review deadlines; eight new tests. |
| G09 | Implemented; targets and change decisions await author input | Migration 0018; objectives and planned ISMS changes, reviewed context, resources, leadership approval, evidence-backed implementation and retained evaluations; seven new tests. Seed targets remain unset and risk-scale guidance remains a draft. |
| G10 | Implemented locally; programme judgments await author input | Migration 0019; maintained audit programmes, frozen audit/review completion, structured review inputs, tracked actions and retained corrective-effectiveness checks; eight tests pass. Verified with 499 backend tests and static seed checks; new G10 files pass lint. |
| G11–G21 | Open | Proceed in ranked order. |
| G22 | Phase 4 | In progress: user requested limited Phase 3 wrap-up and priority on the interface. |

Baseline: 419 backend tests and eight frontend tests. G01: 428 backend passed;
G02: 436 backend passed; G03: 442 backend passed; G04: 449; G05: 457; G06: 468; G07: 476; G08: 484; G09: 491. Frontend tests and typecheck pass after the acceptance display
change. Full build, live smoke with AI available/unavailable, browser verification and
final inventory remain Phase 5/6 work; they have not been claimed complete.

The original risk engine and existing validators have not been rewritten. New rules
live in separate focused services. No real audit or certification outcome is asserted.

## Recovered checkpoint — 2026-09-22

Recovered the working repository at C:\proj\grc after the Codex reinstall. The
previous chat was not recovered. HEAD is eefebce (G09); the existing uncommitted
G10 implementation was preserved and its six new Python modules/test file were
formatted and their imports sorted.

Verification: 493 backend tests passed on the full run; six tests encountered a
Windows temporary-directory permission error during setup. Rerunning the migration
module, the affected treatment migration test and the assurance tests with a writable
workspace basetemp passed all 17 selected tests. Thus all 499 collected backend tests
have passed across these runs. Static seed checks and lint on the six new G10 Python
files pass. Repository-wide lint remains failing outside those files; it must be
resolved before claiming CI is green. Live smoke, frontend integration and final
browser verification remain pending as described above.

Next checkpoint: review the G10 diff and remaining integration lint, then proceed to
G11 (incident and event register) in the ranked assessment. Do not invent author
judgments or claim sample records have real audit evidence.


Git commits remain blocked by index.lock access denial, including after explicit permission grants. No successful commit or push is claimed.

## Scope adjustment  -  2026-09-28

At the author's request, keep the Phase 3 wrap-up small and proceed to Phase 4.
G19-G21 are partial, not closed. No backup recovery or production readiness claim is made.
