# Maintained operational registers

**Sample / Portfolio Assessment** — fictional FinFlow Technologies.

Assets, RoPA, DPIA and BIA records now accept proposed revisions. A proposal stores
the previous record and does not change the live register. Review checks that the
source is unchanged, rejects unresolved author judgments, requires evidence and
applies the existing privacy/continuity validators. Reviewed revisions remain
retrievable. A newer competing proposal cannot silently overwrite a reviewed change.

Relationships use real foreign keys, including stable risk-to-asset links. Changed
records create owned reassessment tasks for linked risks; asset changes also include
risks linked through dependent processing activities and continuity assessments.
Resolving a task needs an authored note and evidence. No update lowers a risk score.

Operational evidence coverage names the source system, actual period, control,
evidence record, owner and review date. It connects external access reviews, change
records, vulnerability work and other operational sources without rebuilding those
systems. A reference does not manufacture a missing file or an effectiveness rating.

Continuity exercises retain measured recovery and data-loss times, the exact BIA
targets used, source evidence and follow-up. The target comparison is arithmetic;
its consequence remains an analyst decision. The supplied seed has one draft BIA
proposal and no invented exercises or operational proof.

Routes live below `/operations`: schemas, registers, revisions/review, reassessments,
coverage and exercises. Existing read APIs and exports continue to read the same
underlying registers after approved revisions are applied.
