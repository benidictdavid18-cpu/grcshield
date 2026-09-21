# Risk treatment plans

**Sample / Portfolio Assessment** — fictional FinFlow Technologies.

A treatment decision needs a delivery plan. Plans name the risk, controls, accountable
owner, resources and rationale, with milestones and optional links to existing
remediation. A plan's review deadline comes from the risk's actual next review. The API
refuses later milestones with a field-level 422. A composite foreign key and CHECK
constraint enforce each milestone's deadline; migrated SQLite and PostgreSQL triggers
also prevent a plan extending beyond risk review or a risk review moving before an
active plan. Historical completed/cancelled plans retain their original commitments.

Drafts can be revised using their current revision. Milestones can depend on another
milestone in the same plan; cycles, reversed dates and completion before the dependency
are refused. Approval requires current risk-owner or CEO account authority, resolved
author hints, committed resources and at least one milestone. The approval preserves a
snapshot. Approved commitments are revised by making a new plan rather than rewriting
the approved one.

Milestone completion requires a real evidence reference and authored evaluation. Plan
closure additionally requires all milestones complete and the business owner's
verification. Delivery does not automatically lower residual risk, accept risk, close
linked remediation or declare a control effective. Those remain separate decisions.
Cancellation retains the reason and prior commitments.

Endpoints: GET `/treatment-plans` and `/treatment-plans/{ref}`; PUT
`/treatment-plans/{ref}` and `/treatment-plans/{ref}/milestones/{milestone_ref}`;
POST `/treatment-plans/{ref}/approve`, `/close`, `/cancel`; POST
`/treatment-milestones/{id}/complete`.

The sample draft TPL-004-DRAFT links RISK-004, AC-002 and REM-001. RISK-004 is reviewed
on 28 September while REM-001's delivery falls in October. The draft retains an author
hint to reconcile that conflict; it does not invent an earlier completed MFA rollout.
Resources and milestone agreement remain explicitly unfinished. The next-review date
is used as the planning checkpoint, not as a fabricated delivery commitment.

Cross-record trigger tests execute against the migrated database. Ordinary metadata-
created SQLite fixtures exercise service rules and local constraints; PostgreSQL DDL
is rendered by the migration suite, with live PostgreSQL verification still required
before a production deployment.
