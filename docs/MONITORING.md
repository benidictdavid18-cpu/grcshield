# Monitoring and retained evaluations

**Sample / Portfolio Assessment** — fictional FinFlow Technologies.

Measurement plans supplement existing KRIs with collection/evaluation ownership,
population, method, source, frequency and next collection date. An observation names
its actual period, source query or collection procedure, population and evidence.
It freezes both the plan and the KRI thresholds. Later plan edits cannot change the
band or basis of an earlier observation. Null remains NO_DATA, never zero.

An observation has one retained evaluation; a red result requires an open remediation.
Seeded historical chart values stay explicitly sample-authored. No observations are
backfilled to make a trend appear complete. Plans remain author tasks until their
collection basis has been confirmed.

Authenticated residual changes retain a structured risk snapshot, including the
control links and proof IDs, in the same transaction as the existing audit event.
The original risk validator and scoring engine remain unchanged.

Routes live below `/monitoring`: plans, observations/evaluate and risks/{ref}/history.
