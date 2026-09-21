# Evidence attachments

**Sample / Portfolio Assessment** — fictional FinFlow Technologies.

An evidence reference can now hold actual, versioned artifacts. Upload requires the
existing evidence reference, an explicit source and retention decision, and a new
version. The original bytes, SHA-256 digest, size, uploader and upload date are retained
in one database transaction. Database storage deliberately keeps these bounded sample
artifacts atomic with their metadata and inside the database backup boundary.

The file limit is 8 MiB. The API bounds the actual request stream at 12 MiB before
parsing base64 JSON, including chunked requests; the proxy has the matching envelope
limit. Supported types are PDF, PNG, JPEG, UTF-8 text/CSV and JSON. Binary signatures
must match the declared type, text must decode, and JSON must parse. These checks are
format checks, not an antivirus attestation. Filenames cannot contain paths or control
characters and are never used as filesystem locations. Downloads are authenticated,
forced attachments, carry the portfolio header and verify the retained digest.

REGISTER_READERS permits the existing authenticated reader roles. MAINTAINERS hides
both attachment metadata and bytes from read-only accounts. Uploading an artifact
makes no judgment about the control's effectiveness or whether the artifact is adequate
for a particular assessment; the test and its reviewer still supply that basis.

Retention cannot end before upload. An administrator can extend it or change legal
hold with an authored reason. Purge requires administrator authority, elapsed retention,
no legal hold and a reason. The database enforces the local purge/date/hold invariants.
Purge removes bytes while retaining metadata, checksum and the accountable audit event.
It does not erase historical workpapers or recreate expired evidence as current proof.

Endpoints: GET/POST `/evidence/{ref}/attachments`; GET
`/evidence-attachments/{id}/download`; PATCH `/evidence-attachments/{id}/retention`;
POST `/evidence-attachments/{id}/purge`. Upload JSON uses `content_base64`, `filename`,
`content_type`, `version`, `source`, `access_scope`, `retention_until`, `retention_reason`
and `legal_hold`. Listing never includes the binary payload.

No original source binaries were supplied in the sample repository. Attachment seeding
therefore intentionally adds zero rows. Existing path strings remain visible references,
not fabricated files or claims that evidence was retrieved. The author supplies actual
sample artifacts when available. Document revisions can link the evidence metadata;
the same evidence attachment endpoint retrieves its artifacts.
