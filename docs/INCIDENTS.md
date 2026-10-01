# Events and incidents

**Sample / Portfolio Assessment** — fictional FinFlow Technologies.

An event report records an observation, its source and dates, response owner and a
real risk/control pair. A linked finding must concern that control. EVT-001 carries
the observation already documented in TEST-008 and FIND-003; it does not turn a
failed test into a declared incident, a severity assessment or a reportable breach.
Those judgments remain `TODO AUTHOR:BENNY` until an analyst records them.

`/incidents` supports reporting and append-only timeline entries. Triage records
dismissal or incident classification, severity, owner and the notification decision.
Containment precedes recovery; closure needs lessons and evidence. Closed or dismissed
events require an explicit reopening decision. Revision checks refuse stale decisions;
earlier decisions and their snapshots remain retrievable after reopening.

Evidence custody entries refer to actual retained G06 attachments, verify the digest,
and retain the version/hash and custody note. Register-only evidence can support a
closure reference but does not assert that a missing source artifact was inspected.
The platform records communication decisions; it sends no external notification.
No incident transition changes a residual risk score or a control rating.
