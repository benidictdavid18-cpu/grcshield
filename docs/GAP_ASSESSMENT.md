# GRCShield — Phase 2 gap assessment

**Sample / Portfolio Assessment** — fictional FinFlow Technologies. This is a platform capability assessment, not a certification decision or a report of a real audit.

Assessment date: 21 September 2026. Repository baseline: `581bacd`. Seed business date: 4 September 2026. Dates in the sample are assessed against that business date; running the application later can legitimately change expiry totals.

## Basis and priority

The platform has a coherent risk methodology and useful traceability. It can record 93 Annex A applicability decisions, independent inherent/residual scores, controls, workpapers, evidence metadata, remediation, expiring exceptions, and sample ISMS/privacy/continuity records. It does not yet provide a complete maintained management-system record.

This assessment distinguishes a missing capability from a missing organizational practice. ISO does not require a particular software register. A controlled external record can answer an audit question if its ownership, approval, currency and retrieval are demonstrable. An IMPLEMENTED sample row is an assertion, not independent proof of operation. Conversely, an excluded Annex A control is not automatically a deficiency. Clauses 4–10 and the risk-based selection of necessary controls must be considered together.

Priority is an engineering and audit-readiness judgment, not an invented major/minor nonconformity grade:

- **P0:** unreliable claims or foundational management-system evidence. Resolve before relying on the application as the assessment record.
- **P1:** operation, evaluation and improvement cannot be demonstrated through a maintained lifecycle.
- **P2:** sustainability, timeliness and platform resilience.
- **P3:** usability improvements that belong in Phase 4.

The ranked order below is the proposed implementation order. G01 comes first as ADR-008 requires. An auditor reviewing foundational documentation would normally ask about G04–G07 before sampling individual control operations; that does not make the integrity defects G01–G03 safe to defer. Actual audit findings depend on the evidence maintained outside this application.

The standards reference is [ISO/IEC 27001:2022](https://www.iso.org/standard/27001). The assessment also accounts for [Amendment 1:2024](https://www.nen.nl/media/PDF/ISO_IEC_27001_2022_Amd_1_2024_ed.3_-_id.88435_Publication_PDF_en_.pdf): context needs a climate-relevance determination, and interested-party requirements may include climate considerations. No relevance conclusion has been invented for FinFlow.

## Ranked gaps

### 1. G01 — Test-specific proof and controlled reassessment (P0; known gap, extended)

**References:** 6.1.2, 6.1.3, 8.2, 8.3, 9.1; A.5.35, A.5.36.

**Present limitation:** `RiskControl` stores an effectiveness basis and note without a `ControlTest` reference. ADR-008 already identifies this. A runtime failed test changes the control rating and opens a draft finding/remediation, but the authored TEST-008 cascade to risk, SoA, DPIA and nonconformity is seed data. The cascade test reads that snapshot; it does not prove the write path propagates reassessment. A later submission can overwrite a control rating even when its test date is older or its population differs.

**Auditor question:** Which test, population and period support this risk's claimed benefit, and what happened to dependent decisions when that test failed?

**Fix:** Link test-backed risk-control claims to a same-control test, retain the assessed population/period, and record supersession explicitly. Preserve legitimate differing bases for different populations. A new adverse result should create owned reassessment work and flag stale claims, not invent a new residual score, SoA decision or DPIA judgment. Require explicit resolution with supporting evidence. Keep DESIGN_ONLY distinct from NOT_TESTED under the existing methodology. Add mutation-based cascade and out-of-order test regression tests.

**Evidence:** `backend/app/models/risk.py`, `backend/app/api/routes/testing.py`, `backend/app/seed/run_seed.py`, `backend/tests/test_testing_api.py`, ADR-008.

### 2. G02 — Acceptance coverage and attributable approvals (P0; additional)

**References:** 6.1.3 f), 5.3, 8.3; A.5.2, A.5.3.

**Present limitation:** Acceptance summaries count PENDING records as coverage; a pending record can also acquire the derived EXPIRING_SOON state. The create schema accepts a status and named approver role, but that role is not bound to the authenticated decision maker. There is no complete approve/reject/renew/withdraw lifecycle. A role string is not proof of risk-owner approval.

**Auditor question:** Who actually accepted this residual risk, with what authority, and why does an unapproved request appear to cover it?

**Fix:** Distinguish workflow status from time-to-expiry. Only an approved, currently valid, properly authorized decision counts as acceptance. Add attributable decision transitions, decision notes, approved-on/expiry invariants and renewal history. Preserve the existing expiring-acceptance principle. Test pending-near-expiry, expired, rejected and unauthorized approval paths.

**Evidence:** `backend/app/api/routes/privacy.py` coverage/live summaries; `backend/app/services/executive.py`; `backend/app/schemas/privacy.py`; exception constraints in migration 0005.

### 3. G03 — Preserve edited records across restart (P0; additional)

**References:** 7.5.3, 8.1; A.5.33, A.8.32.

**Present limitation:** `backend/entrypoint.sh` runs the seed loader on startup and describes restart as a no-op. `seed_risks` unconditionally copies sample fields into existing risks and reconciles their links. Consequently, a repeated seed can restore authored values over edited ones. Mathematical idempotence is not preservation of user changes.

**Auditor question:** Can a service restart change the assessment I approved, without a corresponding decision and audit record?

**Fix:** Separate immutable catalogue bootstrap, one-time sample initialization, and an explicitly requested sample reset. Normal startup must preserve business records. Prove edit → seed/startup → read retains the edited value and audit history. Do not silently discard existing user records during migration.

**Evidence:** `backend/entrypoint.sh`, `backend/app/seed/run_seed.py:seed_risks`.

### 4. G04 — Context, interested parties and maintained scope (P0; known)

**References:** 4.1–4.4; related 6.1.1 and A.5.31.

**Present limitation:** `docs/SCOPE.md` states the fictional operating boundary, but there is no maintained issue/party/requirement register or approved scope revision linked to those inputs.

**Auditor question:** Which internal/external issues and relevant parties shaped this boundary, which requirements are addressed by the ISMS, and when were those decisions reviewed?

**Fix:** Context issues, interested parties and requirements with owner, source, relevance decision and review date; link them to scope revisions, risks and obligations. Record the climate-relevance determination without presuming the outcome. Link the ISMS processes and their owners so scope is more than a prose boundary.

### 5. G05 — Controlled policy and document lifecycle (P0; known)

**References:** 5.1–5.3, 7.5.1–7.5.3; A.5.1, A.5.2, A.5.33, A.5.37.

**Present limitation:** Policies and responsibilities appear in narrative and evidence references. There is no controlled document record with retrievable revision, author/reviewer/approver, publication, distribution and supersession.

**Auditor question:** Show the authorized security policy in force on the assessment date, how personnel obtained it, and the approved revision history.

**Fix:** Document identity separate from immutable revisions; owner, classification, review date, approval/publication states, external-document source and access rules. Tie responsibilities and policy communication to the applicable revision. Preserve obsolete revisions for their required retention period. A document upload alone does not close this gap.

### 6. G06 — Retrievable, protected evidence (P0; known)

**References:** 7.5.3, 9.1; A.5.28, A.5.33, A.8.3.

**Present limitation:** Evidence has validity dates and a file-reference string, but no stored/retrievable artifact. Thus the platform can describe a workpaper attachment without presenting it.

**Auditor question:** Open the exact artifact used for this conclusion and establish its origin, period, integrity and authorized access.

**Fix:** Versioned attachments with authenticated download, safe storage identifiers, size/type validation, checksum, uploader/time, source, retention and restricted access. Support controlled external repositories with verified retrieval where appropriate. Distinguish expired evidence from invalid historical evidence: expired evidence can support a past assessment, but current reliance needs a reviewer decision. Do not create fabricated proof files to fill the sample.

### 7. G07 — SoA releases and approval history (P0; known, extended)

**References:** 6.1.3 d), 7.5.2–7.5.3; A.5.35, A.5.36.

**Present limitation:** Mutable rows carry version/approver fields, but edits do not create an immutable approved release or a new approval. Overview metadata is taken from a row. The framework catalogue's separate scope flags can diverge from edited applicability decisions.

**Auditor question:** Which exact SoA did management approve, what changed since then, and which decision controls downstream crosswalk scope?

**Fix:** Draft revision → reviewed release with authenticated sign-off, frozen entries, change rationale and diff. Material edits produce a draft, not an apparently still-approved release. Derive downstream scope from the chosen authoritative SoA release. Check missing required evidence or unresolved gaps explicitly; a COMPLETED remediation must not masquerade as active treatment for a still-open implementation gap.

### 8. G08 — Approved treatment plans and milestones (P0; known)

**References:** 6.1.3 e)–f), 8.3.

**Present limitation:** Risks have treatment decisions/summaries and remediation tasks, but no coherent plan with owner approval, milestones, resources, dependencies, evidence and progress.

**Auditor question:** What work will bring this risk to its target position, by when, with whose approval and resources, and how will completion be evaluated?

**Fix:** Versioned risk treatment plans and dated milestones linked to real controls/remediation; resources, dependencies, accountable owners, approval and completion evidence. Enforce the requested milestone-versus-risk-review date rule. Keep plan approval distinct from acceptance of residual risk; completion must not automatically lower the score.

### 9. G09 — Objectives, resources and planned ISMS changes (P1; additional)

**References:** 5.1, 6.1.1, 6.2, 6.3, 7.1.

**Present limitation:** KRIs measure selected conditions, and reviews describe decisions, but there is no owned objective with target, measures, resources, completion horizon and evaluation; no controlled ISMS change plan.

**Auditor question:** What are your information-security objectives, who delivers them, how are results evaluated, and how are significant ISMS changes planned?

**Fix:** Objective and change records tied to context, risks and review actions. Record baseline/target/measure, responsibility, resources, timescale, evaluation and approval. Preserve the current scoring model. Methodology documentation gives numerical bands but needs author-confirmed guidance for assigning likelihood/impact levels consistently; record that guidance as a governed document, not a rewritten engine.

### 10. G10 — Audit, management-review and corrective-action lifecycles (P1; additional)

**References:** 9.2.1–9.2.2, 9.3.1–9.3.3, 10.1–10.2; A.5.35, A.5.36.

**Present limitation:** Sample audits, reviews and nonconformities exist, with useful seed validation, but their API is read-only. Review inputs/actions are largely text. The platform cannot maintain an audit programme through planning, evidence, findings and follow-up, or manage review decisions and verified closure.

**Auditor question:** Show risk-based audit coverage, auditor independence, all review inputs, assigned decisions, and evidence that corrective action worked rather than merely being marked complete.

**Fix:** Write lifecycles for programmes/audits, meetings/inputs/decisions/actions and nonconformities. Capture independence, criteria, scope, owner, deadline, correction/root cause/action, effectiveness verification and closure authority. Reopen ineffective actions. Build on current records and validators; do not automatically equate every control-test finding to a management-system nonconformity.

### 11. G11 — Incident and event register (P1; known)

**References:** A.5.24–A.5.28, A.6.8; 8.1, 10.2 where applicable.

**Present limitation:** Control findings are not security events. There is no event triage, incident timeline, response decisions, evidence custody or lessons-learned lifecycle.

**Auditor question:** Show how a reported event became an incident, who responded, how evidence was protected, and what changed afterward.

**Fix:** Events and incidents with classification/decision history, response ownership and chronology, real risk/control links, finding links where supported, communications decisions, evidence and closure/lessons. Enforce the user's required linked control. Record severity and notification judgments as author decisions when facts do not settle them; do not infer a legally reportable breach from a control failure.

### 12. G12 — Supplier and cloud-service oversight (P1; known)

**References:** A.5.19–A.5.23; 8.1.

**Present limitation:** Vendor-review controls and sample evidence exist without a register of suppliers, supplied services, agreements or review outcomes.

**Auditor question:** Which suppliers handle information or support critical services, what security obligations apply, and which reviews or material changes require action?

**Fix:** Suppliers/services with accountable owner, author-assessed criticality, information access, contract/security terms, dependencies, review date/results and exit/change actions. Link AWS and other suppliers only where the existing sample supports them. Reject missing required review dates; connect assurance documents through G06 and obligations through G14.

### 13. G13 — Competence, awareness and communications (P1; known competence gap, extended)

**References:** 7.2–7.4; A.6.1–A.6.8 as applicable, especially A.6.3.

**Present limitation:** People controls and evidence descriptions cannot establish each relevant role's required competence, development action and evaluated outcome. There is no structured awareness acknowledgement or communications plan.

**Auditor question:** How did you establish competence for assigned security duties, evaluate training effectiveness, and communicate policies and responsibilities?

**Fix:** Role requirements and appropriately minimized personnel/role records, training/experience evidence, effectiveness evaluation, review dates, awareness acknowledgements tied to policy versions, and planned communication audience/owner/timing. Attendance is not automatically competence. Protect sensitive personnel information.

### 14. G14 — Applicable obligations and compliance evaluations (P1; additional)

**References:** 4.2, 6.1.1; A.5.31, A.5.32, A.5.34.

**Present limitation:** Privacy records and SOC 2 crosswalks provide useful context but do not form an inventory of applicable legal, regulatory and contractual obligations with sources, owners and evaluations.

**Auditor question:** What obligations apply to this scope, who decided that, and where is the current evidence of evaluation and action?

**Fix:** Source/version/jurisdiction or contractual counterparty, author-approved applicability, accountable owner, review date, linked controls and evaluation/action history. Do not manufacture legal advice, GDPR compliance percentages, or an independent SOC 2 attestation workflow.

### 15. G15 — Maintained operational records and external evidence coverage (P1; additional)

**References:** 8.1–8.3; A.5.9–A.5.18, A.5.29–A.5.30, A.5.34; relevant A.6, A.7 and A.8 controls in the appendix.

**Present limitation:** Assets, RoPA, DPIA and BIA are valuable sample registers but expose read-only lifecycles. Risk asset linkage is text. Generic control descriptions do not establish current access-review, restoration exercise, vulnerability, change, physical or development-security evidence for each applicable control.

**Auditor question:** Can you maintain the scoped assets and processing activities, trace a changed service to its assessments, and retrieve the actual operational record behind this implementation claim?

**Fix:** Governed create/update/review paths for existing registers, stable asset/service links, retained assessment revisions and owned reassessments after changes. Record continuity exercises and restore-test outcomes against BIA targets. Use controlled evidence links to existing operational systems for the remaining control families; do not rebuild IAM, HR, a SIEM or a vulnerability scanner inside GRCShield. The Annex A appendix identifies every sample assertion requiring that evidential trace.

### 16. G16 — Defined monitoring and historical evaluation (P1; additional)

**References:** 9.1, 9.3.2, 10.1; A.5.36.

**Present limitation:** Live KRIs and authored historical points exist, but they do not establish a complete measurement/evaluation process with retained population, source, owner and resulting decisions. Mutable risk rows plus generic audit events are not a structured assessment history.

**Auditor question:** What exactly was measured, using which population and criteria, by whom and when, and what decision followed a breach?

**Fix:** Measurement definitions, collection/evaluation owners and schedule, reproducible dated observations and evaluations linked to actions. Retain risk-assessment snapshots and decision provenance. Historical values must be observed or clearly sample-authored, never generated retrospectively to make a chart look complete.

### 17. G17 — Due-date and threshold notifications (P2; known)

**References:** 7.4, 8.1, 9.1; supports A.5.22 and A.5.24 rather than satisfying them by itself.

**Present limitation:** Overdue reviews, expiring exceptions and KRI breaches are visible only when someone opens the application.

**Auditor question:** How do responsible people learn that action is due, and how do you know a critical reminder was handled?

**Fix:** Durable notification/outbox jobs with deduplication, recipient ownership, delivery attempts, acknowledgement and escalation. In-app notification first; external delivery only through configured, authorized channels. Automated email is not itself an ISO requirement. Never renew acceptance or close an action because a reminder was sent.

### 18. G18 — AI rate limits and retention (P2; known)

**References:** 7.5.3; A.5.33, A.8.6, A.8.15.

**Present limitation:** AI endpoints have no rate limit and interaction metadata has no pruning lifecycle. Advisory separation is already a strength and must remain intact.

**Auditor question:** How are resource consumption and retained interaction records bounded, and which retention rule governs them?

**Fix:** Configurable per-user/resource limits and concurrency ceilings, explicit retention policy and scheduled pruning with observable results. Keep audit-worthy security events distinct from short-lived interaction diagnostics. Inspect error-log content as part of implementation to ensure response fragments cannot defeat metadata-only logging. Mock Ollama in tests; prove refusal and outage handling without granting AI a register-write path.

### 19. G19 — Constraint parity, atomic references and complete change records (P2; additional)

**References:** 7.5.3, 8.1; A.5.33, A.8.15, A.8.26, A.8.29.

**Present limitation:** Some CHECK constraints exist only in migrations while ordinary tests create model metadata directly. Metadata comparison alone does not prove all CHECK constraints are equivalent. Reference generation using current maximum plus one can race. Some audit payloads capture only a subset of the created decision/workpaper.

**Auditor question:** Can invalid or simultaneous writes produce unreliable records, and can a changed decision be reconstructed?

**Fix:** Test invalid writes against the migrated database, with a real PostgreSQL integration lane where that deployment is supported; database-safe reference allocation and transactional retries; complete relevant decision deltas with access controls and retention. Use immutable revision records where generic deltas are insufficient. Do not claim DBA-proof tamper resistance from a read-only API.

### 20. G20 — Backup, recovery and deployment safeguards for the platform (P2; additional)

**References:** A.5.29, A.5.30, A.8.3, A.8.5, A.8.13; 7.5.3.

**Present limitation:** The security documentation does not provide an application-data backup/retention and tested restore lifecycle. Published demo credentials and development defaults require a deliberate deployment boundary.

**Auditor question:** Can you restore the assessment records and their attachments, and are production access and secrets governed?

**Fix:** Document and test consistent database/attachment backup and restore, retention, access and failure reporting. Refuse insecure development defaults in an explicitly non-development deployment. Keep the fictional local demo usable; do not mistake this platform hardening task for evidence that every FinFlow control operates.

### 21. G21 — Authorship and documentation consistency (P2; additional)

**References:** 7.5.2, 7.5.3; supports 6.1.2 and 9.1.

**Present limitation:** Documentation contains stale counts and claims: older risk/appetite totals, an obsolete statement about no audit trail, physical-exclusion count differences, and old outstanding-author text. Runtime finding creation assigns severity and a default owner/deadline; draft status alone does not identify every generated judgment as unapproved authorship. Automatic remediation creation also omits an explicit raised date.

**Auditor question:** Which description is current, and which judgments were authored, mechanically proposed or approved?

**Fix:** Reconcile docs with executable checks; show derivation and approval state for proposals. Insert literal `TODO AUTHOR:BENNY` plus a specific hint wherever surrounding evidence cannot settle a severity, owner, deadline, rationale or decision. Preserve approved sample judgments already supported by the authored story. Record required dates explicitly. Every new compliance record and export retains the portfolio label.

### 22. G22 — Navigable, accessible operational UI (P3; Phase 4)

**References:** Enables use of 7.4, 7.5 and 9.1; these interface features are not standalone ISO certification requirements.

**Present limitation:** Registers lack consistent sort/columns/keyboard/URL state; reference drawers and forms vary; the chain is not the requested interactive graph; trends lack the requested bands and heatmap; themes, narrow layouts and drawer accessibility need verification and work.

**Auditor/user question:** Can I follow a claim to its basis and outstanding action without losing context, including by keyboard or on a narrow screen?

**Fix:** Implement the Phase 4 design brief after the underlying record lifecycles stabilize: shared live tables/reference drawers, interactive risk/test cascade, six-month charts using available dated observations, heatmap, reversible optimistic updates with conflict/error recovery, complete loading/empty/error states, light/dark and keyboard/mobile checks. Keep AI collapsed and advisory. Do not use visual polish to hide unresolved record states.

## Coverage of management-system clauses

This table indexes the assessment; it is not a declaration of conformity.

| Clause | Existing capability | Remaining gaps |
|---|---|---|
| 4.1, 4.2 | Scope narrative and sample operating context | G04, G14: maintained issues, parties, obligations and climate relevance |
| 4.3, 4.4 | Written boundary and connected GRC modules | G04, G05: governed scope revisions and process responsibilities |
| 5.1–5.3 | Named roles, policy references and sample review/approval text | G02, G05, G09, G10: attributable leadership decisions, resources and communication |
| 6.1.1 | Risk register and governance narrative | G04, G09, G14: context-driven ISMS risks/opportunities and actions |
| 6.1.2 | Fixed bands, independent residual judgments, appetite by category | G01, G09, G16: proof, author-approved assignment guidance and assessment history |
| 6.1.3 | Treatment choices, complete Annex A catalogue, SoA, exceptions | G01, G02, G07, G08: approved choices and sustained traceability |
| 6.2 | KRIs and review prose | G09: objective plans and result evaluation |
| 6.3 | Change/audit trail elements | G09: planned ISMS change lifecycle |
| 7.1 | Roles and task owners | G08, G09: committed resources and dependencies |
| 7.2–7.4 | People-control narratives and reports | G05, G13, G17: competence, awareness, communications and delivery |
| 7.5.1–7.5.3 | Docs, evidence metadata, exports and audit trail | G03, G05–G07, G18–G21: controlled, retrievable, retained records |
| 8.1 | Seed/service rules and selected write paths | G03, G10–G15, G19: maintained operations and effective change control |
| 8.2 | Current risk assessments and review dates | G01, G15, G16: reassessment triggers and retained results |
| 8.3 | Remediation and treatment summary | G02, G08: approved treatment execution and results |
| 9.1 | KRI computations, trend samples and control workpapers | G01, G06, G16: reproducible measurements and evaluation decisions |
| 9.2.1–9.2.2 | Three sample audits | G10: programme, independence, execution and follow-up |
| 9.3.1–9.3.3 | Two sample management reviews | G10: complete inputs, decisions, resources and tracked actions |
| 10.1 | Findings/remediation and improvement narrative | G09, G10, G16: evaluated improvement over time |
| 10.2 | Three sample nonconformities and closure-related seed checks | G10: maintained correction, cause, action and effectiveness verification |

## Implementation boundaries and acceptance evidence

All G01–G22 remain **open**. This phase changes documentation only. No compliance decision, seed judgment, schema or runtime behavior has been altered.

Each subsequent gap should be a reviewable commit with the business reason, models/migration/seed where needed, a new focused rule service, routes/schemas, regression tests, seed/smoke coverage and matching documentation. New local invariants belong in both API validation and database constraints where expressible. Cross-record rules need transactional service enforcement and appropriate database mechanisms; a portable row CHECK cannot inspect another record's review date.

The existing risk engine, methodology and validators remain protected by the user instruction. Add focused services and call-site enforcement around them. Do not silently rewrite an existing validator to make a new test pass. Fixes must preserve independent residual scoring, no credit for untested controls, expiring acceptance, the deficient-design cap and advisory-only AI.

Author decisions needed during implementation include context relevance, competence requirements, objective targets/resources, supplier criticality, incident severity, document/SoA approvals, treatment commitments and retention periods. Where the sample does not settle them, the affected record must carry the required author marker and a one-line hint. This assessment has not created speculative compliance records or assigned their judgments.

Verified Phase 1 baseline: backend **419 passed** (one dependency deprecation warning), frontend **8 passed**, typecheck clean, seed checks passing. Migration tests are included in the backend suite. The final live smoke/AI up-and-down/browser/build verification belongs to Phase 5; none is claimed here.

## Annex A — all 93 sample entries

The following inventory is generated from the repository's authored catalogue and SoA seed, not from a live database or an external audit. Linked evidence counts represent metadata references, not downloadable artifacts. A linked internal control is not necessarily tested. All rows share G01/G06/G07/G15 where relevant: establish current proof, retrieve it, preserve the approved applicability decision and maintain the operational record. Exclusions need retained scope rationale and review, not automatic implementation. Titles below are the existing repository's labels.

Specific family work: A.5.1–A.5.3 and A.5.37 → G05; A.5.19–A.5.23 → G12; A.5.24–A.5.28 and A.6.8 → G11; A.5.29–A.5.30 → G15/G20; A.5.31–A.5.34 → G14/G05/G15 as relevant; A.5.35–A.5.36 → G01/G10; A.6.3 → G13. Other people, physical and technological controls require their applicable operational evidence through G15/G06, rather than an invented new product module for each control.

'Excluded' is an applicability decision, not an implementation status. The assessment does not re-decide any of the nine exclusions.

| Control | Repository title | Sample SoA state | Internal control links | Evidence references |
|---|---|---|---:|---:|
| A.5.1 | Policies for information security | IMPLEMENTED | 1 | 1 |
| A.5.2 | Information security roles and responsibilities | IMPLEMENTED | 1 | 1 |
| A.5.3 | Segregation of duties | PARTIALLY_IMPLEMENTED | 1 | 1 |
| A.5.4 | Management responsibilities | IMPLEMENTED | 2 | 1 |
| A.5.5 | Contact with authorities | NOT_IMPLEMENTED | 0 | 0 |
| A.5.6 | Contact with special interest groups | NOT_IMPLEMENTED | 0 | 0 |
| A.5.7 | Threat intelligence | NOT_IMPLEMENTED | 0 | 0 |
| A.5.8 | Information security in project management | PARTIALLY_IMPLEMENTED | 1 | 1 |
| A.5.9 | Inventory of information and other associated assets | PARTIALLY_IMPLEMENTED | 1 | 1 |
| A.5.10 | Acceptable use of information and other associated assets | IMPLEMENTED | 1 | 1 |
| A.5.11 | Return of assets | IMPLEMENTED | 1 | 1 |
| A.5.12 | Classification of information | IMPLEMENTED | 1 | 1 |
| A.5.13 | Labelling of information | NOT_IMPLEMENTED | 1 | 1 |
| A.5.14 | Information transfer | IMPLEMENTED | 2 | 1 |
| A.5.15 | Access control | PARTIALLY_IMPLEMENTED | 2 | 1 |
| A.5.16 | Identity management | IMPLEMENTED | 2 | 2 |
| A.5.17 | Authentication information | IMPLEMENTED | 2 | 1 |
| A.5.18 | Access rights | IMPLEMENTED | 2 | 1 |
| A.5.19 | Information security in supplier relationships | IMPLEMENTED | 1 | 1 |
| A.5.20 | Addressing information security within supplier agreements | IMPLEMENTED | 1 | 1 |
| A.5.21 | Managing information security in the ICT supply chain | PARTIALLY_IMPLEMENTED | 2 | 0 |
| A.5.22 | Monitoring, review and change management of supplier services | IMPLEMENTED | 1 | 1 |
| A.5.23 | Information security for use of cloud services | IMPLEMENTED | 2 | 2 |
| A.5.24 | Information security incident management planning and preparation | IMPLEMENTED | 1 | 1 |
| A.5.25 | Assessment and decision on information security events | IMPLEMENTED | 1 | 1 |
| A.5.26 | Response to information security incidents | IMPLEMENTED | 1 | 1 |
| A.5.27 | Learning from information security incidents | IMPLEMENTED | 1 | 1 |
| A.5.28 | Collection of evidence | PARTIALLY_IMPLEMENTED | 1 | 1 |
| A.5.29 | Information security during disruption | PARTIALLY_IMPLEMENTED | 1 | 1 |
| A.5.30 | ICT readiness for business continuity | PARTIALLY_IMPLEMENTED | 3 | 2 |
| A.5.31 | Legal, statutory, regulatory and contractual requirements | PARTIALLY_IMPLEMENTED | 1 | 0 |
| A.5.32 | Intellectual property rights | IMPLEMENTED | 2 | 1 |
| A.5.33 | Protection of records | IMPLEMENTED | 1 | 1 |
| A.5.34 | Privacy and protection of PII | PARTIALLY_IMPLEMENTED | 2 | 2 |
| A.5.35 | Independent review of information security | NOT_IMPLEMENTED | 0 | 0 |
| A.5.36 | Compliance with policies, rules and standards for information security | PARTIALLY_IMPLEMENTED | 1 | 1 |
| A.5.37 | Documented operating procedures | IMPLEMENTED | 2 | 2 |
| A.6.1 | Screening | IMPLEMENTED | 1 | 1 |
| A.6.2 | Terms and conditions of employment | IMPLEMENTED | 1 | 1 |
| A.6.3 | Information security awareness, education and training | IMPLEMENTED | 1 | 1 |
| A.6.4 | Disciplinary process | IMPLEMENTED | 2 | 1 |
| A.6.5 | Responsibilities after termination or change of employment | IMPLEMENTED | 2 | 2 |
| A.6.6 | Confidentiality or non-disclosure agreements | IMPLEMENTED | 2 | 2 |
| A.6.7 | Remote working | IMPLEMENTED | 2 | 1 |
| A.6.8 | Information security event reporting | IMPLEMENTED | 2 | 2 |
| A.7.1 | Physical security perimeters | EXCLUDED | 0 | 1 |
| A.7.2 | Physical entry | EXCLUDED | 0 | 1 |
| A.7.3 | Securing offices, rooms and facilities | EXCLUDED | 0 | 0 |
| A.7.4 | Physical security monitoring | EXCLUDED | 0 | 0 |
| A.7.5 | Protecting against physical and environmental threats | EXCLUDED | 0 | 1 |
| A.7.6 | Working in secure areas | EXCLUDED | 0 | 0 |
| A.7.7 | Clear desk and clear screen | IMPLEMENTED | 2 | 1 |
| A.7.8 | Equipment siting and protection | IMPLEMENTED | 1 | 1 |
| A.7.9 | Security of assets off-premises | IMPLEMENTED | 1 | 1 |
| A.7.10 | Storage media | PARTIALLY_IMPLEMENTED | 2 | 1 |
| A.7.11 | Supporting utilities | EXCLUDED | 0 | 1 |
| A.7.12 | Cabling security | EXCLUDED | 0 | 0 |
| A.7.13 | Equipment maintenance | NOT_IMPLEMENTED | 0 | 0 |
| A.7.14 | Secure disposal or re-use of equipment | IMPLEMENTED | 2 | 2 |
| A.8.1 | User endpoint devices | IMPLEMENTED | 1 | 1 |
| A.8.2 | Privileged access rights | PARTIALLY_IMPLEMENTED | 1 | 1 |
| A.8.3 | Information access restriction | IMPLEMENTED | 2 | 2 |
| A.8.4 | Access to source code | IMPLEMENTED | 2 | 2 |
| A.8.5 | Secure authentication | PARTIALLY_IMPLEMENTED | 1 | 2 |
| A.8.6 | Capacity management | PARTIALLY_IMPLEMENTED | 1 | 1 |
| A.8.7 | Protection against malware | IMPLEMENTED | 1 | 1 |
| A.8.8 | Management of technical vulnerabilities | IMPLEMENTED | 3 | 2 |
| A.8.9 | Configuration management | IMPLEMENTED | 1 | 1 |
| A.8.10 | Information deletion | PARTIALLY_IMPLEMENTED | 1 | 1 |
| A.8.11 | Data masking | PARTIALLY_IMPLEMENTED | 1 | 1 |
| A.8.12 | Data leakage prevention | NOT_IMPLEMENTED | 0 | 0 |
| A.8.13 | Information backup | IMPLEMENTED | 1 | 1 |
| A.8.14 | Redundancy of information processing facilities | IMPLEMENTED | 1 | 1 |
| A.8.15 | Logging | IMPLEMENTED | 1 | 1 |
| A.8.16 | Monitoring activities | IMPLEMENTED | 1 | 1 |
| A.8.17 | Clock synchronization | IMPLEMENTED | 1 | 1 |
| A.8.18 | Use of privileged utility programs | IMPLEMENTED | 1 | 1 |
| A.8.19 | Installation of software on operational systems | PARTIALLY_IMPLEMENTED | 2 | 1 |
| A.8.20 | Networks security | IMPLEMENTED | 2 | 1 |
| A.8.21 | Security of network services | IMPLEMENTED | 2 | 1 |
| A.8.22 | Segregation of networks | IMPLEMENTED | 1 | 1 |
| A.8.23 | Web filtering | NOT_IMPLEMENTED | 0 | 0 |
| A.8.24 | Use of cryptography | IMPLEMENTED | 2 | 1 |
| A.8.25 | Secure development life cycle | IMPLEMENTED | 2 | 2 |
| A.8.26 | Application security requirements | IMPLEMENTED | 2 | 1 |
| A.8.27 | Secure system architecture and engineering principles | IMPLEMENTED | 2 | 1 |
| A.8.28 | Secure coding | IMPLEMENTED | 2 | 2 |
| A.8.29 | Security testing in development and acceptance | PARTIALLY_IMPLEMENTED | 2 | 2 |
| A.8.30 | Outsourced development | EXCLUDED | 0 | 0 |
| A.8.31 | Separation of development, test and production environments | IMPLEMENTED | 1 | 1 |
| A.8.32 | Change management | IMPLEMENTED | 2 | 2 |
| A.8.33 | Test information | PARTIALLY_IMPLEMENTED | 1 | 1 |
| A.8.34 | Protection of information systems during audit testing | NOT_IMPLEMENTED | 0 | 0 |

Inventory check: 37 organizational + 8 people + 14 physical + 34 technological = 93. Sample states: EXCLUDED: 9, IMPLEMENTED: 55, NOT_IMPLEMENTED: 9, PARTIALLY_IMPLEMENTED: 20.
