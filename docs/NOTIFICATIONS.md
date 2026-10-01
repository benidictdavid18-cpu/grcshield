# Due-date and threshold reminders

**Sample / Portfolio Assessment** — fictional FinFlow Technologies.

The application runs an in-app notification scan every five minutes. Risk reviews,
acceptance expiry, open remediation, supplier/context/document reviews, evidence expiry,
measurement collection and unevaluated red observations feed a durable outbox.
Each condition/reference/date has one deduplication key. Repeated scans do not flood
the recipient. Attempts and failures remain visible; a later scan retries delivery.

Maintainers map an accountable owner label to an active maintainer account. There is
no default mapping to the demo account. Unassigned reminders remain visibly pending
in the outbox. Unacknowledged reminders more than seven days overdue are marked for
escalation and routed to the explicitly configured `ISMS escalation` recipient where
available. Otherwise the existing owner remains responsible and the escalation is
still visible. Only the assigned recipient can acknowledge delivery.

Acknowledgement changes no risk, acceptance or remediation decision. All delivery is
in-app; no email or third-party channel is configured or contacted. Multi-worker
deduplication is enforced by the database; a concurrent scan transaction may retry on
the next cycle. `/notifications/run` provides a manual retry, `/routing` sets ownership,
and `/outbox` exposes undelivered work. `MAINTENANCE_ENABLED=false` disables scheduling.
