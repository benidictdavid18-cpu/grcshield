# Objectives and planned ISMS changes

**Sample / Portfolio Assessment** — fictional FinFlow Technologies.

A KRI describes a condition. An objective adds a leadership commitment: target,
accountable owner, resources, date, measurement definition and the context it serves.
The planning register keeps these separate. Draft objectives may have unresolved
targets and dates; approval cannot. Approval requires reviewed source context, an
explicit measurable target, a future target date and current CEO account authority.
The exact approved commitment and context are retained as a snapshot.

Observations retain their value, observation date, evidence, actor and written
evaluation. A second observation adds history instead of replacing the first. EVALUATED
means a person recorded the result; it does not automatically assert that the objective
was achieved. Observations cannot be dated in the future. Approved targets are changed
by preparing a new commitment, not silently rewriting the old one.

Planned ISMS changes share ownership and resource controls but require an impact
assessment and rollback plan instead of a numeric target. Implementation is recorded
with date and evidence before evaluation. Evaluation of a change cannot precede its
implementation. Cancellation retains its reason and requires management authority.

Endpoints: GET/PUT `/isms/plans/{ref}`; GET `/isms/plans`; POST
`/isms/plans/{ref}/approve`, `/implement`, `/cancel`; GET/POST
`/isms/plans/{ref}/evaluations`. These plans concern the management system; the treatment
register separately governs risk-specific delivery milestones.

OBJ-001 references KRI-001's existing measurement definition but leaves a new objective's
target, due date and resources to the author. CHG-001 leaves change impact, ownership and
rollback decisions as explicit author tasks. DOC-RISK-SCALE is a controlled draft asking
for consistent assignment guidance for the existing 1–5 likelihood/impact scale. It
does not change the methodology, engine, thresholds or independent residual scoring.
