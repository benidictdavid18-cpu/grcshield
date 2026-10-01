# Supplier oversight

**Sample / Portfolio Assessment** — fictional FinFlow Technologies.

The supplier register connects a supplied service to an accountable owner, review
date and existing control. It records information access, contractual terms, shared
responsibilities, exit arrangements and a retained agreement attachment where supplied.
Dependencies reference other suppliers; self-links and dependency cycles are refused.

Every edit returns the supplier to draft. A signed review preserves the exact supplier
revision assessed, the actor, evidence and conclusion. Criticality and contract terms
must be authored before review. An action-required or exit decision needs an owner and
deadline; completion needs dated evidence. A new review never overwrites an old one.
The sample AWS record derives only its service from the existing estate. Criticality,
contract terms and accountability remain author tasks, not inferred approvals.

Routes are `/suppliers`, `/{ref}/reviews` and `/{ref}/reviews/{id}/complete`.
The required review date is enforced by the schema and database; stale writes and
incomplete decisions receive field-specific 422 responses. Evidence references do not
assert that a missing attachment was inspected. G14 links applicable obligations to
supplier counterparties separately.
