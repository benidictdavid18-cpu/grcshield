# Controlled documents

**Sample / Portfolio Assessment** — fictional FinFlow Technologies.

A policy title is not a policy. This register holds the content and retains the exact
revision an authenticated author approved. A document has an owner, classification,
review date, distribution audience/channel and, for an external document, its source.
All reads require authentication and only the existing write roles can maintain the
register. Classification records handling expectations; it does not silently override
the application's established auditor read access.

Each revision contains retrievable text, a SHA-256 content digest, change note and
attributable author. An approval records its actor, date and note. Publication is a
separate action and refuses unapproved or overdue documents. Publishing a replacement
marks the prior publication superseded without changing its content. A partial unique
index permits only one published revision per document. Withdrawal requires a reason;
old content remains retrievable. No endpoint edits retained revision content.

Acknowledgements record the actual signed-in account and the published revision, once
per account. They establish receipt, not competence or agreement with every statement.
The download checks content integrity and carries the portfolio disclaimer. External
sources are recorded without automatic retrieval of untrusted URLs.

Endpoints: GET `/documents`; PUT `/documents/{ref}`; GET/POST
`/documents/{ref}/revisions`; POST `/document-revisions/{id}/approve`, `/publish` or
`/withdraw` with an authored note; GET `/document-revisions/{id}/download`; GET/POST
`/document-revisions/{id}/acknowledgements`.

The sample DOC-001 points to EV-029. EV-029 describes a policy set v3.0 but does not
contain its actual text. The seeded revision is therefore source-pending and DRAFT,
with explicit author hints for content, author and distribution. Its review date and
owner come from EV-029. No historical signature or missing policy text is invented.
Attachment storage is the separate G06 change; these text revisions already provide a
retrievable controlled record independently of that storage layer.
