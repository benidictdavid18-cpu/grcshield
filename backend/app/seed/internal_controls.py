"""FinFlow's internal control library.

These are controls FinFlow operates, not catalogue entries from a standard. Each one
names a real mechanism and a role that answers for it, because a control nobody owns
cannot be tested and a control with no mechanism cannot produce evidence.

``annex_a_refs`` records which Annex A control(s) each one helps satisfy. The mapping
runs internal -> Annex A, matching the direction of the Statement of Applicability:
FinFlow decides what it does, then shows how that meets the standard.
"""

from typing import NamedTuple


class InternalControl(NamedTuple):
    control_id: str
    title: str
    description: str
    family: str
    owner_role: str
    annex_a_refs: tuple[str, ...]


# Design and operating effectiveness, assessed separately.
#
# Twelve of these controls carry a formal workpaper in ``control_tests``; the rest are
# rated from review and monitoring rather than sample testing, which is what a
# risk-based audit programme actually looks like at this size. Where a workpaper
# exists, the operating rating must agree with the most recent conclusion — enforced by
# the seed loader.
#
# DP-005 is the one design deficiency: masking is scoped to the primary application
# database only, so as designed it does not protect analytics or support environments.
# No amount of reliable nightly execution fixes that.
EFFECTIVENESS: dict[str, tuple[str, str, str | None]] = {
    "AC-001": ("EFFECTIVE", "EFFECTIVE", None),
    "AC-002": (
        "EFFECTIVE", "EFFECTIVE_WITH_EXCEPTIONS",
        "Workforce MFA tested clean (TEST-002). Privileged account coverage tested at 60% "
        "(TEST-003), so the control-level rating carries the exception.",
    ),
    "AC-003": (
        "EFFECTIVE", "EFFECTIVE_WITH_EXCEPTIONS",
        "Elevation works as designed, but two legacy standing-access paths remain outside it.",
    ),
    "AC-004": ("EFFECTIVE", "EFFECTIVE", None),
    "AC-005": ("EFFECTIVE", "EFFECTIVE", None),
    "AC-006": ("EFFECTIVE", "EFFECTIVE", "Rated from configuration review; no sample test performed."),
    "DP-001": ("EFFECTIVE", "EFFECTIVE", None),
    "DP-002": (
        "EFFECTIVE", "NOT_TESTED",
        "Design reviewed. The supporting scan evidence (EV-008) has expired and no test has "
        "been performed against the current load balancer configuration.",
    ),
    "DP-003": ("EFFECTIVE", "NOT_TESTED", "Policy design reviewed; operation never tested."),
    "DP-004": ("EFFECTIVE", "EFFECTIVE", None),
    "DP-005": (
        "DEFICIENT", "INEFFECTIVE",
        "Design deficiency: masking is scoped to the primary application database only, so "
        "analytics and support environments are out of scope by design. TEST-008 concluded "
        "FAIL — the control did not achieve its objective during the period, and roughly "
        "192,000 unmasked customer records were found outside production. The jobs that do "
        "run execute reliably, but reliable execution of a control pointed at the wrong "
        "scope is not effectiveness.",
    ),
    "OP-001": ("EFFECTIVE", "EFFECTIVE", None),
    "OP-002": ("EFFECTIVE", "EFFECTIVE", None),
    "OP-003": ("EFFECTIVE", "EFFECTIVE", "Rated from pipeline configuration review."),
    "OP-004": (
        "EFFECTIVE", "EFFECTIVE_WITH_EXCEPTIONS",
        "Critical and high severities remediated within SLA; medium shows a 12% breach rate.",
    ),
    "OP-005": ("EFFECTIVE", "EFFECTIVE", None),
    "OP-006": ("EFFECTIVE", "EFFECTIVE", "Rated from architecture and configuration review."),
    "OP-007": ("EFFECTIVE", "EFFECTIVE", "Rated from MDM compliance reporting."),
    "CM-001": ("EFFECTIVE", "EFFECTIVE", "Rated from branch protection configuration review."),
    "CM-002": ("EFFECTIVE", "EFFECTIVE", None),
    "CM-003": ("EFFECTIVE", "EFFECTIVE", None),
    "CM-004": ("EFFECTIVE", "EFFECTIVE", None),
    "CM-005": ("EFFECTIVE", "EFFECTIVE", None),
    "TP-001": ("EFFECTIVE", "EFFECTIVE", None),
    "TP-002": (
        "EFFECTIVE", "EFFECTIVE",
        "Review process operates. Note the AWS report obtained under it (EV-023) has since "
        "expired, which is an evidence-freshness issue rather than a control failure.",
    ),
    "TP-003": ("EFFECTIVE", "EFFECTIVE", None),
    "HR-001": ("EFFECTIVE", "EFFECTIVE", None),
    "HR-002": ("EFFECTIVE", "EFFECTIVE", "94% completion; outstanding staff escalated."),
    "HR-003": ("EFFECTIVE", "EFFECTIVE", None),
    "IR-001": ("EFFECTIVE", "EFFECTIVE", None),
    "IR-002": ("EFFECTIVE", "EFFECTIVE", None),
    "BC-001": (
        "EFFECTIVE", "NOT_TESTED",
        "Plan design reviewed at draft v0.9. No exercise has been run, so operation cannot "
        "be rated.",
    ),
    "GV-001": ("EFFECTIVE", "EFFECTIVE", None),
    "GV-002": ("EFFECTIVE", "NOT_TESTED", "Role definitions reviewed; operation not tested."),
    "GV-003": (
        "EFFECTIVE", "NOT_TESTED",
        "Cadence is defined but has not yet completed a full cycle, so there is nothing to "
        "test against.",
    ),
}


INTERNAL_CONTROLS: list[InternalControl] = [
    # --- Access and identity ------------------------------------------------
    InternalControl(
        "AC-001",
        "Okta SSO enforced for all business applications",
        "All SaaS applications holding company or customer data are integrated with Okta "
        "for single sign-on. Local application accounts are prohibited outside of documented "
        "break-glass exceptions.",
        "Access Control",
        "Head of Engineering",
        ("A.5.16", "A.5.17", "A.8.3"),
    ),
    InternalControl(
        "AC-002",
        "Multi-factor authentication enforced via Okta",
        "Okta sign-on policy requires a phishing-resistant second factor for all users. "
        "Privileged AWS and GitHub roles require re-authentication on each elevation.",
        "Access Control",
        "Head of Engineering",
        ("A.8.5", "A.5.17"),
    ),
    InternalControl(
        "AC-003",
        "Privileged AWS access granted through time-bound role assumption",
        "Standing administrative credentials are not issued. Engineers assume a privileged "
        "role for a bounded session through AWS IAM Identity Center, with the elevation "
        "logged to CloudTrail.",
        "Access Control",
        "Head of Engineering",
        ("A.8.2", "A.8.18"),
    ),
    InternalControl(
        "AC-004",
        "Quarterly user access review",
        "Application and infrastructure owners review entitlement reports each quarter and "
        "attest to them in writing. Revocations are tracked to completion.",
        "Access Control",
        "Head of Engineering",
        ("A.5.18", "A.8.3"),
    ),
    InternalControl(
        "AC-005",
        "Joiner, mover and leaver process driven by Okta lifecycle management",
        "HR system changes drive Okta provisioning and deprovisioning. Departures trigger "
        "same-day session revocation and access removal.",
        "Access Control",
        "Head of People",
        ("A.5.16", "A.5.18", "A.6.5", "A.5.11"),
    ),
    InternalControl(
        "AC-006",
        "GitHub repository access restricted by team membership",
        "Repository permissions are assigned to teams rather than individuals, with write "
        "access to production repositories limited to the owning team.",
        "Access Control",
        "Head of Engineering",
        ("A.8.4", "A.8.3"),
    ),
    # --- Data protection -----------------------------------------------------
    InternalControl(
        "DP-001",
        "Encryption at rest using AWS KMS customer-managed keys",
        "All RDS instances, S3 buckets and EBS volumes holding customer data are encrypted "
        "with customer-managed KMS keys. Key policies restrict administrative use.",
        "Data Protection",
        "Head of Engineering",
        ("A.8.24",),
    ),
    InternalControl(
        "DP-002",
        "TLS 1.2 or higher enforced for all data in transit",
        "Public endpoints terminate TLS 1.2+ at the load balancer with weak ciphers "
        "disabled. Internal service-to-service traffic is encrypted.",
        "Data Protection",
        "Head of Engineering",
        ("A.8.24", "A.5.14"),
    ),
    InternalControl(
        "DP-003",
        "Information classification policy applied to data stores",
        "Data is classified as Public, Internal, Confidential or Restricted, with handling "
        "requirements defined per tier and applied to each data store.",
        "Data Protection",
        "Head of Legal & Compliance",
        ("A.5.12", "A.5.13"),
    ),
    InternalControl(
        "DP-004",
        "Documented retention schedule with automated deletion",
        "Retention periods are defined per data category and enforced by scheduled deletion "
        "jobs. Deletions are logged.",
        "Data Protection",
        "Head of Legal & Compliance",
        ("A.5.33", "A.8.10"),
    ),
    InternalControl(
        "DP-005",
        "Production data masked before use in non-production environments",
        "Non-production environments are seeded from synthetic or masked data. Copying "
        "unmasked production data to a lower environment is prohibited.",
        "Data Protection",
        "Head of Engineering",
        ("A.8.11", "A.8.33"),
    ),
    # --- Operations ----------------------------------------------------------
    InternalControl(
        "OP-001",
        "Centralised logging with 12-month retention",
        "Application, infrastructure and CloudTrail logs are shipped to a dedicated logging "
        "account with restricted access and 12-month retention.",
        "Operations",
        "Head of Engineering",
        ("A.8.15", "A.5.28"),
    ),
    InternalControl(
        "OP-002",
        "Security monitoring and alerting on the AWS estate",
        "GuardDuty, Config and CloudTrail alerts route to an on-call rotation with defined "
        "triage timeframes by severity.",
        "Operations",
        "Head of Engineering",
        ("A.8.16", "A.5.25"),
    ),
    InternalControl(
        "OP-003",
        "Automated vulnerability scanning of container images and dependencies",
        "Images are scanned on build and on a weekly schedule. Critical findings block "
        "promotion to production.",
        "Operations",
        "Head of Engineering",
        ("A.8.8",),
    ),
    InternalControl(
        "OP-004",
        "Patch management with severity-based remediation SLAs",
        "Critical vulnerabilities are remediated within 7 days, high within 30, medium "
        "within 90. Exceptions require documented approval.",
        "Operations",
        "Head of Engineering",
        ("A.8.8", "A.8.19"),
    ),
    InternalControl(
        "OP-005",
        "Daily automated backups with periodic restore testing",
        "RDS automated backups and point-in-time recovery are enabled with cross-region "
        "copies. Restores are exercised on a defined schedule.",
        "Operations",
        "Head of Engineering",
        ("A.8.13", "A.5.30"),
    ),
    InternalControl(
        "OP-006",
        "Multi-availability-zone deployment for production services",
        "Production compute and database tiers run across at least two availability zones "
        "with automated failover.",
        "Operations",
        "Head of Engineering",
        ("A.8.14", "A.5.30"),
    ),
    InternalControl(
        "OP-007",
        "Managed endpoint protection on the macOS fleet",
        "Company laptops are enrolled in MDM with full-disk encryption, screen lock, "
        "automatic updates and endpoint detection and response deployed.",
        "Operations",
        "Head of Engineering",
        ("A.8.1", "A.8.7", "A.7.9"),
    ),
    # --- Change and development ----------------------------------------------
    InternalControl(
        "CM-001",
        "Peer-reviewed pull requests required for production changes",
        "Branch protection requires at least one approving review from a second engineer "
        "and passing status checks before merge to the release branch.",
        "Change Management",
        "Head of Engineering",
        ("A.8.32", "A.5.3"),
    ),
    InternalControl(
        "CM-002",
        "Separate AWS accounts for development, staging and production",
        "Environments are isolated in distinct AWS accounts under an organisation, with no "
        "network path from lower environments into production.",
        "Change Management",
        "Head of Engineering",
        ("A.8.31", "A.8.22"),
    ),
    InternalControl(
        "CM-003",
        "Static application security testing in the CI pipeline",
        "SAST runs on every pull request. High-severity findings must be resolved or "
        "explicitly waived with justification before merge.",
        "Change Management",
        "Head of Engineering",
        ("A.8.28", "A.8.29"),
    ),
    InternalControl(
        "CM-004",
        "Automated dependency vulnerability alerting",
        "Dependabot alerts are enabled on all repositories and triaged against the patch "
        "management SLA.",
        "Change Management",
        "Head of Engineering",
        ("A.8.8", "A.5.21"),
    ),
    InternalControl(
        "CM-005",
        "Infrastructure defined as code and applied through review",
        "Infrastructure changes are made through Terraform in version control. Manual "
        "console changes in production are treated as incidents.",
        "Change Management",
        "Head of Engineering",
        ("A.8.9", "A.8.32"),
    ),
    # --- Third party ----------------------------------------------------------
    InternalControl(
        "TP-001",
        "Security review before vendor onboarding",
        "Vendors handling company or customer data complete a security review covering "
        "certifications, data location, subprocessors and breach notification before "
        "contract signature.",
        "Third Party",
        "Head of Legal & Compliance",
        ("A.5.19", "A.5.21"),
    ),
    InternalControl(
        "TP-002",
        "Annual review of critical vendor assurance reports",
        "SOC 2 Type II or ISO 27001 certificates for critical vendors, including AWS and the "
        "payment service provider, are obtained and reviewed annually, with exceptions "
        "tracked.",
        "Third Party",
        "Head of Legal & Compliance",
        ("A.5.22", "A.5.23"),
    ),
    InternalControl(
        "TP-003",
        "Security and data protection clauses in supplier agreements",
        "Standard contract terms cover confidentiality, security obligations, breach "
        "notification timeframes and, where personal data is processed, Article 28 terms.",
        "Third Party",
        "Head of Legal & Compliance",
        ("A.5.20", "A.6.6"),
    ),
    # --- People ----------------------------------------------------------------
    InternalControl(
        "HR-001",
        "Pre-employment background screening",
        "Identity, right to work and employment history are verified before a start date, "
        "proportionate to the role and to local law.",
        "People",
        "Head of People",
        ("A.6.1",),
    ),
    InternalControl(
        "HR-002",
        "Security awareness training at onboarding and annually",
        "All staff complete security and data protection training within 30 days of joining "
        "and annually thereafter. Completion is tracked and escalated.",
        "People",
        "Head of People",
        ("A.6.3", "A.6.8"),
    ),
    InternalControl(
        "HR-003",
        "Confidentiality agreements signed at onboarding",
        "All employees and contractors sign confidentiality terms before receiving access to "
        "company systems.",
        "People",
        "Head of People",
        ("A.6.6", "A.6.2"),
    ),
    # --- Incident and continuity -------------------------------------------------
    InternalControl(
        "IR-001",
        "Documented incident response plan with assigned roles",
        "The plan defines severity levels, an incident commander role, communication paths "
        "and regulatory notification timeframes including GDPR Article 33.",
        "Incident Response",
        "Head of Engineering",
        ("A.5.24", "A.5.26"),
    ),
    InternalControl(
        "IR-002",
        "Post-incident review with tracked actions",
        "Every severity 1 and 2 incident receives a blameless post-mortem with root cause "
        "and corrective actions tracked to closure.",
        "Incident Response",
        "Head of Engineering",
        ("A.5.27",),
    ),
    InternalControl(
        "BC-001",
        "Business continuity plan with annual exercise",
        "Continuity plans cover loss of a cloud region, loss of a critical SaaS provider and "
        "loss of key personnel, and are exercised at least annually.",
        "Business Continuity",
        "Chief Operating Officer",
        ("A.5.29", "A.5.30"),
    ),
    # --- Governance ---------------------------------------------------------------
    InternalControl(
        "GV-001",
        "Information security policy set reviewed and approved annually",
        "A policy set covering acceptable use, access control, cryptography, incident "
        "response and supplier security is approved by leadership annually and published to "
        "all staff.",
        "Governance",
        "Head of Legal & Compliance",
        ("A.5.1", "A.5.36", "A.5.10"),
    ),
    InternalControl(
        "GV-002",
        "Defined and documented security roles and responsibilities",
        "Security responsibilities are assigned by role, documented, and reflected in job "
        "descriptions and the ISMS scope document.",
        "Governance",
        "Chief Operating Officer",
        ("A.5.2", "A.5.4"),
    ),
    InternalControl(
        "GV-003",
        "Annual risk assessment with quarterly register review",
        "The full risk assessment is refreshed annually. The register is reviewed quarterly "
        "by risk owners, and residual scores are re-justified when controls change.",
        "Governance",
        "Chief Operating Officer",
        ("A.5.35", "A.5.31"),
    ),
]
