# Record integrity and concurrency

**Sample / Portfolio Assessment** — fictional FinFlow Technologies.

TEST, FIND, REM, EXC and AI references use a database counter in the write transaction.
First use derives the high-water mark from existing authored references, inserts with
ON CONFLICT, then atomically increments with UPDATE RETURNING. Concurrent writers no
longer select the same maximum-plus-one reference. Failed transactions roll back both
allocation and record. Sample reapplication does not reset counters.

Named checks originally declared only in migrations are also applied to model metadata.
A test compares their names and normalized SQL against the actual migrated database,
and deliberately attempts an impossible BIA insert. The PostgreSQL integration lane
uses a disposable schema and runs the real migration chain, rather than treating
offline SQL rendering as proof of deployment.

Control-test audit events retain the complete submitted workpaper and persisted fields;
acceptance creation retains rationale, compensating controls and review triggers.
The append-only API does not imply DBA-proof tamper resistance. Evidence and personnel
access restrictions remain separate from broadly readable operational decisions.
