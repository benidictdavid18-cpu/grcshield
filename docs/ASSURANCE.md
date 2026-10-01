# Maintained assurance workflows

**Sample / Portfolio Assessment** — fictional FinFlow Technologies.

An audit date is not an audit programme. The programme now records its owner,
risk-based coverage, frequency, methods, reporting responsibilities and review date.
Maintained audits link to that programme and retain scope, criteria, objectives,
independence and actual execution dates. Completion requires authored conclusions and
a real evidence reference. The completed snapshot includes the programme as it stood
at that decision, so a later programme edit cannot rewrite the audit's basis.

Management review has ten structured input categories covering previous actions,
context and party changes, nonconformities and corrective actions, monitoring, audit
results, objectives, feedback, risk assessment and treatment, and improvement
opportunities. Each input records what was considered and either a real evidence
reference or an explicit explanation for having no separate evidence. Completion
requires every category, meeting decisions and current CEO business authority.
An evidence reference identifies a register record; it does not claim that a missing
source attachment has been inspected.

Agreed actions carry owners and due dates and may link an existing finding. Their
completion needs dated evidence and an authored note. The action may finish after
the meeting or audit; completing it does not alter the original meeting snapshot.
When no action is agreed, the review's authored actions field must explain that
judgment. The software does not invent a finding or a corrective action merely
because an audit has finished.

Nonconformities distinguish correction, root cause and corrective action. An
explicit effectiveness verification records its date, evidence, assessor, result and
the exact corrective-action record assessed. Effective verification closes the
record; an ineffective verification reopens corrective work. Earlier checks remain
available. An absent root cause, absent action or target, nonexistent evidence,
future check or check predating the latest retained verification is refused.

The new tables enforce real foreign keys, date order for programmes, unique input
categories and completion evidence/signature fields. Services enforce lifecycle,
authority, input coverage and cross-record date rules with field-specific 422
responses (missing business authority is 403). This does not assert independent
assurance merely because the assessor supplied an independence statement.

The supplied historical audits, reviews and nonconformities retain their original
content. They have not been retroactively signed, converted to maintained cycles or
assigned invented effectiveness evidence. A new maintained cycle uses a new
reference. AP-001 proposes a calendar-year programme with explicit author tasks for
coverage, frequency and responsibility; those tasks block audit completion.

Routes live below `/isms/assurance`: programmes, audits, reviews, cycles and their
inputs/actions, action completion, nonconformity maintenance and verification
history. Existing `/isms` read routes and exports include newly created audit,
review and nonconformity records. No external notifications are sent by these writes.
