"""Evidence register.

Each artifact carries a validity window rather than only a collection date. Three
entries are deliberately expired as of the assessment date (2026-08-15) so the
freshness metric has something real to report: EV-008, EV-023 and EV-030.
"""

from datetime import date
from typing import NamedTuple


class EvidenceSpec(NamedTuple):
    ref: str
    title: str
    description: str
    evidence_type: str
    source_system: str
    collected_by: str
    collected_date: date
    valid_from: date
    valid_until: date
    control_ref: str | None
    file_reference: str | None


EVIDENCE: list[EvidenceSpec] = [
    EvidenceSpec(
        "EV-001", "Okta global sign-on policy export",
        "JSON export of the Okta sign-on policy showing the second-factor requirement "
        "applied to every application in the org.",
        "CONFIG_EXPORT", "Okta", "Head of Engineering",
        date(2026, 6, 1), date(2026, 6, 1), date(2026, 12, 1),
        "AC-002", "evidence/2026-06/okta-signon-policy.json",
    ),
    EvidenceSpec(
        "EV-002", "MFA enrolment report for privileged accounts",
        "Okta report listing privileged role holders and their enrolled factors. Shows "
        "60% coverage: 9 of 15 privileged accounts have a phishing-resistant factor "
        "enrolled, with 6 still on password-only legacy paths.",
        "REPORT", "Okta", "Head of Engineering",
        date(2026, 7, 15), date(2026, 7, 15), date(2027, 1, 15),
        "AC-002", "evidence/2026-07/privileged-mfa-coverage.csv",
    ),
    EvidenceSpec(
        "EV-003", "AWS IAM Identity Center permission set export",
        "Permission sets and session duration configuration for privileged roles.",
        "CONFIG_EXPORT", "AWS IAM Identity Center", "Head of Engineering",
        date(2026, 6, 10), date(2026, 6, 10), date(2026, 12, 10),
        "AC-003", "evidence/2026-06/aws-permission-sets.json",
    ),
    EvidenceSpec(
        "EV-004", "Q2 2026 user access review attestation",
        "Signed attestations from application owners confirming entitlement review "
        "completion, with the revocation list and closure dates.",
        "ATTESTATION", "Confluence", "Head of Engineering",
        date(2026, 7, 3), date(2026, 7, 3), date(2026, 10, 3),
        "AC-004", "evidence/2026-07/q2-access-review.pdf",
    ),
    EvidenceSpec(
        "EV-005", "Okta lifecycle workflow configuration",
        "Provisioning and deprovisioning workflow definitions triggered by HR system "
        "events, including same-day session revocation on termination.",
        "CONFIG_EXPORT", "Okta", "Head of People",
        date(2026, 5, 20), date(2026, 5, 20), date(2026, 11, 20),
        "AC-005", "evidence/2026-05/okta-lifecycle.json",
    ),
    EvidenceSpec(
        "EV-006", "GitHub team and repository permission export",
        "Export of team-to-repository permission assignments across all organisation "
        "repositories.",
        "CONFIG_EXPORT", "GitHub", "Head of Engineering",
        date(2026, 6, 22), date(2026, 6, 22), date(2026, 12, 22),
        "AC-006", "evidence/2026-06/github-permissions.csv",
    ),
    EvidenceSpec(
        "EV-007", "KMS key policy and encryption configuration export",
        "Customer-managed key policies plus RDS, S3 and EBS encryption settings for the "
        "production account.",
        "CONFIG_EXPORT", "AWS", "Head of Engineering",
        date(2026, 6, 5), date(2026, 6, 5), date(2026, 12, 5),
        "DP-001", "evidence/2026-06/kms-and-encryption.json",
    ),
    EvidenceSpec(
        "EV-008", "TLS configuration scan report",
        "External scan of public endpoints confirming TLS 1.2 minimum and weak cipher "
        "removal. EXPIRED — the scan predates the current load balancer configuration.",
        "REPORT", "SSL Labs", "Head of Engineering",
        date(2025, 9, 1), date(2025, 9, 1), date(2026, 3, 1),
        "DP-002", "evidence/2025-09/tls-scan.pdf",
    ),
    EvidenceSpec(
        "EV-009", "Information classification policy v2.1",
        "Approved policy defining the Public, Internal, Confidential and Restricted "
        "tiers with handling requirements for each.",
        "POLICY", "Confluence", "Head of Legal & Compliance",
        date(2026, 4, 30), date(2026, 4, 30), date(2027, 4, 30),
        "DP-003", "evidence/2026-04/classification-policy-v2.1.pdf",
    ),
    EvidenceSpec(
        "EV-010", "Retention schedule and deletion job logs",
        "Retention periods per data category, plus 90 days of scheduled deletion job "
        "output showing successful execution.",
        "LOG_EXTRACT", "AWS CloudWatch", "Head of Legal & Compliance",
        date(2026, 7, 1), date(2026, 7, 1), date(2027, 1, 1),
        "DP-004", "evidence/2026-07/retention-and-deletion.zip",
    ),
    EvidenceSpec(
        "EV-011", "Non-production data masking configuration",
        "Seed job configuration and a sample extract confirming non-production "
        "environments carry synthetic or masked records only.",
        "CONFIG_EXPORT", "GitHub", "Head of Engineering",
        date(2026, 6, 18), date(2026, 6, 18), date(2026, 12, 18),
        "DP-005", "evidence/2026-06/masking-config.json",
    ),
    EvidenceSpec(
        "EV-012", "CloudWatch log group retention export",
        "Log group configuration across the production and logging accounts confirming "
        "12-month retention and restricted access.",
        "CONFIG_EXPORT", "AWS CloudWatch", "Head of Engineering",
        date(2026, 6, 12), date(2026, 6, 12), date(2026, 12, 12),
        "OP-001", "evidence/2026-06/log-retention.json",
    ),
    EvidenceSpec(
        "EV-013", "GuardDuty findings and alert routing configuration",
        "Detector configuration, severity-to-rotation routing rules, and 90 days of "
        "finding triage records with response times.",
        "CONFIG_EXPORT", "AWS GuardDuty", "Head of Engineering",
        date(2026, 7, 8), date(2026, 7, 8), date(2027, 1, 8),
        "OP-002", "evidence/2026-07/guardduty-and-routing.json",
    ),
    EvidenceSpec(
        "EV-014", "Container image scan results",
        "Scan output for all production images over the preceding 30 days, showing the "
        "promotion gate rejecting images with critical findings.",
        "REPORT", "Amazon ECR", "Head of Engineering",
        date(2026, 7, 20), date(2026, 7, 20), date(2026, 10, 20),
        "OP-003", "evidence/2026-07/image-scans.json",
    ),
    EvidenceSpec(
        "EV-015", "Patch compliance report by severity",
        "Remediation timing against the 7/30/90-day SLA. Critical and high are within "
        "SLA; medium shows a 12% breach rate.",
        "REPORT", "AWS Systems Manager", "Head of Engineering",
        date(2026, 7, 12), date(2026, 7, 12), date(2026, 10, 12),
        "OP-004", "evidence/2026-07/patch-compliance.csv",
    ),
    EvidenceSpec(
        "EV-016", "Backup configuration and restore test record",
        "RDS automated backup and PITR settings, cross-region copy configuration, and "
        "the record of the June 2026 restore exercise with timings.",
        "REPORT", "AWS Backup", "Head of Engineering",
        date(2026, 6, 28), date(2026, 6, 28), date(2026, 12, 28),
        "OP-005", "evidence/2026-06/backup-and-restore-test.pdf",
    ),
    EvidenceSpec(
        "EV-017", "Multi-AZ architecture diagram and RDS configuration",
        "Current architecture diagram plus RDS multi-AZ and failover configuration "
        "export for production.",
        "CONFIG_EXPORT", "AWS", "Head of Engineering",
        date(2026, 5, 15), date(2026, 5, 15), date(2026, 11, 15),
        "OP-006", "evidence/2026-05/multi-az.json",
    ),
    EvidenceSpec(
        "EV-018", "MDM compliance report for the macOS fleet",
        "Device compliance status covering disk encryption, screen lock, OS version and "
        "EDR agent health across all issued laptops.",
        "REPORT", "Jamf", "Head of Engineering",
        date(2026, 7, 25), date(2026, 7, 25), date(2026, 10, 25),
        "OP-007", "evidence/2026-07/mdm-compliance.csv",
    ),
    EvidenceSpec(
        "EV-019", "Branch protection settings export",
        "Branch protection rules for production repositories showing required reviews "
        "and required status checks.",
        "CONFIG_EXPORT", "GitHub", "Head of Engineering",
        date(2026, 6, 22), date(2026, 6, 22), date(2026, 12, 22),
        "CM-001", "evidence/2026-06/branch-protection.json",
    ),
    EvidenceSpec(
        "EV-020", "AWS Organizations account structure export",
        "Organisation unit and account layout showing development, staging and "
        "production isolation, with SCP definitions.",
        "CONFIG_EXPORT", "AWS Organizations", "Head of Engineering",
        date(2026, 5, 8), date(2026, 5, 8), date(2026, 11, 8),
        "CM-002", "evidence/2026-05/aws-org-structure.json",
    ),
    EvidenceSpec(
        "EV-021", "SAST pipeline configuration and recent run history",
        "Pipeline definition plus the last 20 runs showing high-severity findings "
        "blocking merge or carrying a recorded waiver.",
        "REPORT", "GitHub Actions", "Head of Engineering",
        date(2026, 7, 6), date(2026, 7, 6), date(2027, 1, 6),
        "CM-003", "evidence/2026-07/sast-runs.json",
    ),
    EvidenceSpec(
        "EV-022", "Vendor security review file — payment service provider",
        "Completed security review covering certifications, data location, "
        "subprocessors and breach notification terms.",
        "REPORT", "Confluence", "Head of Legal & Compliance",
        date(2026, 3, 18), date(2026, 3, 18), date(2027, 3, 18),
        "TP-001", "evidence/2026-03/psp-security-review.pdf",
    ),
    EvidenceSpec(
        "EV-023", "AWS SOC 2 Type II report FY2025",
        "Provider assurance report relied upon for the excluded physical controls. "
        "EXPIRED — the FY2026 report has been requested but not yet obtained, which "
        "leaves the A.7 exclusion justifications temporarily unsupported.",
        "CERTIFICATE", "AWS Artifact", "Head of Legal & Compliance",
        date(2025, 5, 1), date(2025, 5, 1), date(2026, 5, 1),
        "TP-002", "evidence/2025-05/aws-soc2-type2-fy2025.pdf",
    ),
    EvidenceSpec(
        "EV-024", "Standard supplier agreement template with security schedule",
        "Contract template showing confidentiality, security obligations, breach "
        "notification timeframes and Article 28 processor terms.",
        "POLICY", "Confluence", "Head of Legal & Compliance",
        date(2026, 2, 12), date(2026, 2, 12), date(2027, 2, 12),
        "TP-003", "evidence/2026-02/supplier-agreement-template.pdf",
    ),
    EvidenceSpec(
        "EV-025", "Background screening completion log",
        "Screening completion record for all hires in the preceding 12 months, with "
        "start dates and verification categories.",
        "REPORT", "BambooHR", "Head of People",
        date(2026, 7, 2), date(2026, 7, 2), date(2027, 1, 2),
        "HR-001", "evidence/2026-07/screening-log.csv",
    ),
    EvidenceSpec(
        "EV-026", "Security awareness training completion report",
        "Completion rates for onboarding and annual refresher training, currently 94% "
        "with the outstanding 6% escalated to line managers.",
        "REPORT", "KnowBe4", "Head of People",
        date(2026, 7, 17), date(2026, 7, 17), date(2027, 1, 17),
        "HR-002", "evidence/2026-07/training-completion.csv",
    ),
    EvidenceSpec(
        "EV-027", "Confidentiality agreement completion record",
        "Signed confidentiality terms for all employees and contractors with system "
        "access, matched against the current headcount.",
        "ATTESTATION", "DocuSign", "Head of People",
        date(2026, 6, 15), date(2026, 6, 15), date(2026, 12, 15),
        "HR-003", "evidence/2026-06/nda-completion.csv",
    ),
    EvidenceSpec(
        "EV-028", "Incident response plan v1.3",
        "Approved plan defining severity levels, the incident commander role, "
        "communication paths and GDPR Article 33 notification timeframes.",
        "POLICY", "Confluence", "Head of Engineering",
        date(2026, 5, 29), date(2026, 5, 29), date(2027, 5, 29),
        "IR-001", "evidence/2026-05/incident-response-plan-v1.3.pdf",
    ),
    EvidenceSpec(
        "EV-029", "Information security policy set v3.0",
        "Full policy set approved by leadership on 30 April 2026 and published to all "
        "staff, with the acknowledgement record.",
        "POLICY", "Confluence", "Head of Legal & Compliance",
        date(2026, 4, 30), date(2026, 4, 30), date(2027, 4, 30),
        "GV-001", "evidence/2026-04/policy-set-v3.0.pdf",
    ),
    EvidenceSpec(
        "EV-031", "Post-incident review records",
        "Blameless post-mortems for the two severity 2 incidents in the period, with root "
        "cause analysis and corrective actions tracked to closure.",
        "REPORT", "Confluence", "Head of Engineering",
        date(2026, 6, 26), date(2026, 6, 26), date(2027, 6, 26),
        "IR-002", "evidence/2026-06/post-incident-reviews.pdf",
    ),
    EvidenceSpec(
        "EV-030", "Business continuity plan v0.9 (draft)",
        "Draft continuity plan covering loss of a cloud region and loss of key "
        "personnel. EXPIRED and still in draft — no exercise has been run against it, "
        "which is why BC-001 is assessed on design only.",
        "POLICY", "Confluence", "Chief Operating Officer",
        date(2026, 1, 8), date(2026, 1, 8), date(2026, 7, 1),
        "BC-001", "evidence/2026-01/bcp-v0.9-draft.pdf",
    ),
]
