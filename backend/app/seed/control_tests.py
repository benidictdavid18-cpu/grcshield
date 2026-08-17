"""Control testing workpapers, audit findings and the ISO clause-level records.

Twelve tests: eight PASS, three PASS_WITH_EXCEPTIONS, one FAIL. The four non-clean
conclusions each cascade into an audit finding and a remediation item, which is the
rule the API enforces on write.

Three of the four findings attach to remediation items that already exist from the SoA
gap analysis, because the work needed was already known and planned. Manufacturing four
fresh remediation items would double-count the same effort.

``sampling_rationale`` is left as ``TODO AUTHOR:BENNY`` on four tests: TEST-003,
TEST-005, TEST-008 and TEST-011.
"""

from datetime import date
from typing import NamedTuple

TODO = "TODO AUTHOR:BENNY"

TESTER_ENG = "Priya Raghavan, Security Engineer"
TESTER_COMPLIANCE = "Marcus Whitfield, Compliance Analyst"
REVIEWER_LEGAL = "Head of Legal & Compliance"
REVIEWER_ENG = "Head of Engineering"


class ControlTestSpec(NamedTuple):
    ref: str
    control_ref: str
    tester: str
    test_date: date
    period_start: date
    period_end: date
    objective: str
    procedure: str
    population_description: str
    population_size: int
    sample_size: int
    method: str
    sampling_rationale: str
    results_summary: str
    exceptions_count: int
    exception_details: str | None
    conclusion: str
    reviewed_by: str | None
    review_date: date | None
    evidence: tuple[str, ...]
    finding_ref: str | None


CONTROL_TESTS: list[ControlTestSpec] = [
    ControlTestSpec(
        "TEST-001", "AC-001", TESTER_ENG,
        date(2026, 6, 5), date(2026, 1, 1), date(2026, 5, 31),
        "Determine whether all business applications holding company or customer data "
        "authenticate through Okta, with no local accounts outside documented break-glass "
        "exceptions.",
        "Obtained the SaaS application inventory and the Okta application catalogue. "
        "Reconciled the two. For each sampled application, inspected the authentication "
        "configuration and attempted a local login to confirm it was refused.",
        "All 34 SaaS applications recorded in the vendor register as holding company or "
        "customer data, active during the period.",
        34, 34, "FULL_POPULATION",
        "The population is small enough to examine in full, so sampling adds no value and "
        "leaves residual uncertainty for nothing. Full-population testing also gives a "
        "definitive answer to the completeness question a sample cannot close.",
        "All 34 applications federate to Okta. Two documented break-glass accounts exist "
        "(AWS root, Okta super-admin), both stored offline and covered by IR-001.",
        0, None, "PASS", REVIEWER_LEGAL, date(2026, 6, 12),
        ("EV-001",), None,
    ),
    ControlTestSpec(
        "TEST-002", "AC-002", TESTER_ENG,
        date(2026, 6, 8), date(2026, 1, 1), date(2026, 5, 31),
        "Determine whether workforce users are required to present a phishing-resistant "
        "second factor at sign-in.",
        "Extracted the Okta sign-on policy and the full user factor enrolment report. "
        "Selected a sample of users and inspected their enrolled factors and the policy "
        "rule applied to them. Reviewed 30 days of sign-in logs for the sampled users to "
        "confirm a second factor was actually presented.",
        "All 41 active workforce accounts in Okta during the period, excluding the two "
        "documented break-glass accounts.",
        41, 25, "RANDOM",
        "A random sample removes selection bias, which matters here because enrolment "
        "gaps cluster by team and a judgmental sample would probably have picked "
        "engineering. Twenty-five of forty-one gives reasonable coverage of a control "
        "expected to operate without exception.",
        "All 25 sampled accounts had a phishing-resistant factor enrolled and the sign-on "
        "policy applied. Sign-in logs confirmed the factor was presented on every "
        "authentication in the 30-day window.",
        0, None, "PASS", REVIEWER_LEGAL, date(2026, 6, 15),
        ("EV-001",), None,
    ),
    ControlTestSpec(
        # The RISK-004 walkthrough test.
        "TEST-003", "AC-002", TESTER_ENG,
        date(2026, 7, 16), date(2026, 1, 1), date(2026, 6, 30),
        "Determine whether MFA is enforced on every privileged access path into the AWS "
        "production account, including legacy and programmatic paths.",
        "Obtained the list of privileged role holders from AWS IAM Identity Center and "
        "reconciled it to Okta group membership. Examined every privileged account's "
        "enrolled factors. Traced each documented access path into production and tested "
        "whether the Okta sign-on policy was applied on each.",
        "All 15 accounts holding a privileged role in the AWS production account at any "
        "point during the period.",
        15, 15, "FULL_POPULATION",
        f"{TODO} — explain why a privileged population this small warrants full-population "
        "testing rather than a sample, and what that choice buys you when the exception "
        "rate turns out to be 40%.",
        "Nine of fifteen privileged accounts (60%) have a phishing-resistant factor "
        "enrolled and the sign-on policy applied. Six do not.",
        6,
        "Six privileged accounts authenticate without a phishing-resistant factor: four "
        "reach production through a legacy IAM user with programmatic keys that bypass the "
        "Okta sign-on policy entirely, and two are engineer accounts enrolled only with "
        "SMS, which the policy does not treat as phishing-resistant. Any of the six is "
        "sufficient for an attacker holding a stolen password to reach production.",
        "PASS_WITH_EXCEPTIONS", REVIEWER_LEGAL, date(2026, 7, 23),
        ("EV-002",), "FIND-001",
    ),
    ControlTestSpec(
        "TEST-004", "AC-003", TESTER_ENG,
        date(2026, 7, 16), date(2026, 1, 1), date(2026, 6, 30),
        "Determine whether privileged AWS access is granted only through time-bound role "
        "assumption, with each elevation logged.",
        "Extracted all privileged sessions from CloudTrail for the period. Sampled "
        "elevation events and traced each to an IAM Identity Center permission set with a "
        "bounded session duration. Separately searched for privileged API activity not "
        "preceded by a role assumption event.",
        "All 612 privileged sessions in the AWS production account during the period.",
        612, 40, "RANDOM",
        "Random selection across the full period avoids over-weighting any single month, "
        "and forty items is enough to detect a systemic bypass while remaining "
        "proportionate to a control with a compensating detective layer in OP-002.",
        "All 40 sampled elevations used a time-bound permission set and were logged. The "
        "separate search for unattributed privileged activity found two long-lived IAM "
        "users operating outside the elevation path.",
        2,
        "Two legacy IAM users hold standing programmatic access to production and do not "
        "pass through role assumption, so their activity is logged but not gated. These "
        "are the same access paths recorded in the exceptions to TEST-003.",
        "PASS_WITH_EXCEPTIONS", REVIEWER_LEGAL, date(2026, 7, 23),
        ("EV-003",), "FIND-002",
    ),
    ControlTestSpec(
        "TEST-005", "AC-004", TESTER_COMPLIANCE,
        date(2026, 7, 10), date(2026, 4, 1), date(2026, 6, 30),
        "Determine whether the Q2 2026 quarterly access review was performed by the "
        "correct owners, completed within the period, and that identified revocations were "
        "carried out.",
        "Obtained the Q2 entitlement reports and owner attestations. For each sampled "
        "application, confirmed the attestation was signed by the recorded owner and dated "
        "within the review window. Traced every revocation on the sampled reports through "
        "to removal in Okta or AWS.",
        "All 18 applications and infrastructure entitlement sets in scope for the quarterly "
        "review.",
        18, 18, "FULL_POPULATION",
        f"{TODO} — the population here is the review itself rather than individual users. "
        "Explain why that is the right unit of testing for a periodic control, and what "
        "you would have tested instead if the review had been continuous.",
        "All 18 attestations were signed by the recorded owner within the review window. "
        "All 23 identified revocations were completed, with a median of 2 days to removal "
        "and none exceeding the 5-day target.",
        0, None, "PASS", REVIEWER_LEGAL, date(2026, 7, 17),
        ("EV-004",), None,
    ),
    ControlTestSpec(
        "TEST-006", "DP-001", TESTER_ENG,
        date(2026, 6, 9), date(2026, 1, 1), date(2026, 5, 31),
        "Determine whether all production data stores holding customer data are encrypted "
        "at rest with customer-managed KMS keys, and that key policies restrict "
        "administrative use.",
        "Enumerated every RDS instance, S3 bucket and EBS volume in the production account "
        "via the AWS API. Inspected the encryption configuration and key ARN of each. "
        "Reviewed the KMS key policy for administrative principals.",
        "All 27 data stores in the production account (4 RDS instances, 19 S3 buckets, "
        "4 EBS volume sets).",
        27, 27, "FULL_POPULATION",
        "Encryption is a binary configuration attribute that can be read programmatically "
        "for every resource at negligible cost, so sampling would trade certainty for "
        "nothing. A single unencrypted store is a reportable exposure, which makes "
        "completeness the point of the test.",
        "All 27 stores are encrypted with customer-managed keys. Key policies restrict "
        "administrative operations to a single break-glass role.",
        0, None, "PASS", REVIEWER_LEGAL, date(2026, 6, 16),
        ("EV-007",), None,
    ),
    ControlTestSpec(
        "TEST-007", "DP-004", TESTER_COMPLIANCE,
        date(2026, 7, 6), date(2026, 4, 1), date(2026, 6, 30),
        "Determine whether scheduled deletion jobs executed as configured and removed "
        "records that had passed their retention period.",
        "Obtained the retention schedule and the deletion job execution logs for the "
        "quarter. Sampled job runs and confirmed each completed successfully. For each "
        "sampled run, queried the target table for records older than the retention period "
        "to confirm none remained.",
        "All 91 scheduled deletion job runs across 7 data categories during the quarter.",
        91, 20, "HAPHAZARD",
        "Haphazard selection across categories and dates was proportionate here: the jobs "
        "are automated and identical in mechanism, so the risk is systemic failure rather "
        "than item-level variation, and a systemic failure would appear in any selection.",
        "All 20 sampled runs completed successfully. No records past their retention period "
        "remained in the sampled tables.",
        0, None, "PASS", REVIEWER_LEGAL, date(2026, 7, 13),
        ("EV-010",), None,
    ),
    ControlTestSpec(
        "TEST-008", "DP-005", TESTER_ENG,
        date(2026, 7, 24), date(2026, 1, 1), date(2026, 6, 30),
        "Determine whether all non-production environments are seeded exclusively with "
        "synthetic or masked data.",
        "Enumerated every non-production data store across the development, staging and "
        "analytics accounts. For each, sampled records from tables known to carry personal "
        "data and inspected them for real customer values. Reviewed the seed job "
        "configuration to establish which environments it covers.",
        "All 11 non-production data stores across the development, staging and analytics "
        "accounts.",
        11, 11, "FULL_POPULATION",
        f"{TODO} — this test found a design deficiency rather than an operating failure. "
        "Explain how the population you chose made that visible, and why a sample of the "
        "application database alone would have concluded PASS.",
        "The masking job covers the primary application database and operates correctly "
        "there. It does not cover the analytics warehouse or the support tooling data "
        "store, both of which were found to hold unmasked customer records including email "
        "addresses and partial payment identifiers.",
        2,
        "Two of eleven non-production stores hold unmasked customer personal data: the "
        "analytics warehouse (approximately 180,000 records) and the support tooling "
        "replica (approximately 12,000 records). Neither is within the scope of the seed "
        "job as configured, so this is a deficiency in the control's design rather than a "
        "failure of its operation — the job cannot mask what it was never pointed at.",
        "FAIL", REVIEWER_LEGAL, date(2026, 7, 31),
        ("EV-011",), "FIND-003",
    ),
    ControlTestSpec(
        "TEST-009", "OP-001", TESTER_ENG,
        date(2026, 6, 16), date(2026, 1, 1), date(2026, 5, 31),
        "Determine whether application, infrastructure and CloudTrail logs are shipped to "
        "the dedicated logging account with 12-month retention and restricted access.",
        "Enumerated log groups across the production and logging accounts. Inspected "
        "retention configuration and resource policies on each. Sampled dates within the "
        "period and confirmed logs were present and continuous for those dates.",
        "All 46 log groups across the production and logging accounts.",
        46, 46, "FULL_POPULATION",
        "Retention is a configuration attribute readable for every log group at no cost, "
        "and a single group with a shorter retention would silently defeat the control. "
        "Completeness is cheap here, so it was purchased.",
        "All 46 log groups are configured with 12-month retention in the logging account. "
        "Access is restricted to two roles. Sampled dates showed continuous coverage with "
        "no gaps.",
        0, None, "PASS", REVIEWER_LEGAL, date(2026, 6, 23),
        ("EV-012",), None,
    ),
    ControlTestSpec(
        "TEST-010", "OP-002", TESTER_COMPLIANCE,
        date(2026, 7, 13), date(2026, 4, 1), date(2026, 6, 30),
        "Determine whether security alerts were triaged within the timeframes defined for "
        "their severity.",
        "Extracted all GuardDuty and Config alerts raised during the quarter with their "
        "routing and acknowledgement timestamps. Sampled alerts stratified across severity "
        "levels and computed time to first response against the defined target.",
        "All 214 security alerts raised during the quarter (8 high, 41 medium, 165 low).",
        214, 30, "JUDGMENTAL",
        "Stratified judgmental selection weighted towards high severity: all 8 high alerts "
        "were examined plus 22 across medium and low. A proportionate random sample would "
        "have drawn roughly one high alert, which would say nothing about the response "
        "path that actually matters.",
        "All 8 high-severity alerts were acknowledged within the 30-minute target, median "
        "9 minutes. The 22 sampled medium and low alerts were all triaged within their "
        "respective targets.",
        0, None, "PASS", REVIEWER_ENG, date(2026, 7, 20),
        ("EV-013",), None,
    ),
    ControlTestSpec(
        "TEST-011", "OP-004", TESTER_ENG,
        date(2026, 7, 14), date(2026, 1, 1), date(2026, 6, 30),
        "Determine whether vulnerabilities were remediated within the severity-based SLA "
        "of 7 days for critical, 30 for high and 90 for medium.",
        "Extracted all vulnerability findings raised and closed during the period from AWS "
        "Systems Manager and the container registry. Sampled findings stratified by "
        "severity and computed elapsed days from detection to remediation against the SLA. "
        "Reviewed documented exception approvals for any breach.",
        "All 487 vulnerability findings raised during the period (6 critical, 78 high, "
        "403 medium).",
        487, 45, "JUDGMENTAL",
        f"{TODO} — you weighted this sample towards critical and high. Justify that against "
        "the fact that the exceptions all turned out to be in medium, and say whether the "
        "weighting was still the right call.",
        "All 6 critical and all 15 sampled high findings were remediated within SLA. Of 24 "
        "sampled medium findings, 3 exceeded the 90-day SLA, none with a documented "
        "exception approval.",
        3,
        "Three medium-severity findings were remediated at 104, 112 and 137 days against a "
        "90-day SLA, none carrying a documented exception approval. Extrapolated across the "
        "medium population this indicates roughly a 12% breach rate. Critical and high "
        "severities showed no exceptions.",
        "PASS_WITH_EXCEPTIONS", REVIEWER_LEGAL, date(2026, 7, 21),
        ("EV-015",), "FIND-004",
    ),
    ControlTestSpec(
        "TEST-012", "OP-005", TESTER_ENG,
        date(2026, 6, 30), date(2026, 1, 1), date(2026, 5, 31),
        "Determine whether backups completed as scheduled and whether a restore from "
        "backup produces a usable database within the recovery time objective.",
        "Reviewed backup completion status for every day in the period. Performed a live "
        "restore of the production database from a cross-region copy into an isolated "
        "account, timed it, and ran integrity checks against the restored data.",
        "All 151 daily automated backup runs during the period, plus one full restore "
        "exercise.",
        151, 151, "FULL_POPULATION",
        "Backup completion status is available for every run, so the schedule was tested in "
        "full. The restore is necessarily a single exercise — a backup nobody has restored "
        "is an untested control, and testing it once is the difference between evidence and "
        "assumption.",
        "All 151 backup runs completed successfully. The restore exercise completed in 47 "
        "minutes against a 4-hour RTO, with integrity checks passing on the restored data.",
        0, None, "PASS", REVIEWER_LEGAL, date(2026, 7, 7),
        ("EV-016",), None,
    ),
]


class FindingSpec(NamedTuple):
    ref: str
    title: str
    description: str
    severity: str
    status: str
    source: str
    identified_date: date
    identified_by: str
    owner: str
    control_ref: str | None
    remediation: tuple[str, ...]
    closed_date: date | None


AUDIT_FINDINGS: list[FindingSpec] = [
    FindingSpec(
        "FIND-001",
        "MFA is not enforced on 40% of privileged production accounts",
        "TEST-003 found that six of fifteen privileged AWS accounts authenticate without a "
        "phishing-resistant factor. Four use legacy IAM users with programmatic keys that "
        "bypass the Okta sign-on policy; two are enrolled only with SMS. This is the "
        "control weakness underlying RISK-004, whose residual score of 15 sits above the "
        "Cybersecurity appetite ceiling.",
        "HIGH", "OPEN", "CONTROL_TEST",
        date(2026, 7, 16), TESTER_ENG, "Head of Engineering",
        "AC-002", ("REM-001",), None,
    ),
    FindingSpec(
        "FIND-002",
        "Two legacy IAM users hold standing access outside the elevation path",
        "TEST-004 identified two long-lived IAM users with standing programmatic access to "
        "production that do not pass through time-bound role assumption. Their activity is "
        "logged but not gated, so the preventive intent of AC-003 does not apply to them. "
        "These are the same access paths recorded in the TEST-003 exceptions.",
        "MEDIUM", "OPEN", "CONTROL_TEST",
        date(2026, 7, 16), TESTER_ENG, "Head of Engineering",
        "AC-003", ("REM-001",), None,
    ),
    FindingSpec(
        "FIND-003",
        "Non-production masking does not cover analytics or support environments",
        "TEST-008 found unmasked customer personal data in two of eleven non-production "
        "stores: approximately 180,000 records in the analytics warehouse and 12,000 in "
        "the support tooling replica. The masking job operates correctly within its "
        "configured scope, which does not include either store. This is a design "
        "deficiency rather than an operating failure, and it is why DP-005 carries a "
        "DEFICIENT design rating.",
        "HIGH", "OPEN", "CONTROL_TEST",
        date(2026, 7, 24), TESTER_ENG, "Head of Engineering",
        "DP-005", ("REM-017",), None,
    ),
    FindingSpec(
        "FIND-004",
        "Medium-severity patch SLA breached without documented exception approval",
        "TEST-011 found three of twenty-four sampled medium-severity findings remediated "
        "beyond the 90-day SLA at 104, 112 and 137 days, none carrying a documented "
        "exception approval. Extrapolated, this indicates roughly a 12% breach rate on the "
        "medium population. Critical and high severities showed no exceptions.",
        "MEDIUM", "OPEN", "CONTROL_TEST",
        date(2026, 7, 14), TESTER_ENG, "Head of Engineering",
        "OP-004", ("REM-020",), None,
    ),
]


class InternalAuditSpec(NamedTuple):
    ref: str
    title: str
    scope: str
    objectives: str
    criteria: str
    auditor: str
    independence_note: str
    planned_start: date
    planned_end: date
    actual_start: date | None
    actual_end: date | None
    status: str
    outcome_summary: str | None


INTERNAL_AUDITS: list[InternalAuditSpec] = [
    InternalAuditSpec(
        "AUD-001",
        "Access control and identity management",
        "Annex A controls A.5.15 to A.5.18, A.8.2 to A.8.5 and A.8.18, together with the "
        "internal controls AC-001 to AC-006. Covers the AWS production account, Okta and "
        "GitHub.",
        "Determine whether access to production systems and customer data is granted, "
        "reviewed and revoked in line with the access control policy, and whether "
        "privileged access is adequately restricted.",
        "ISO/IEC 27001:2022 Clauses 6.1.3 and 8.1, Annex A as listed, and the FinFlow "
        "access control policy v3.0.",
        "Marcus Whitfield, Compliance Analyst",
        "The auditor does not hold administrative access to AWS, Okta or GitHub and had no "
        "role in designing or operating the access controls under audit. Testing of "
        "controls the auditor could not independently examine was performed by the Security "
        "Engineer and reviewed by the Head of Legal & Compliance. At forty people full "
        "auditor independence is not achievable for every control, so the compensating "
        "arrangement is recorded rather than the independence claim overstated.",
        date(2026, 6, 1), date(2026, 7, 31), date(2026, 6, 5), date(2026, 7, 23),
        "COMPLETED",
        "Six controls tested (TEST-001 to TEST-005 plus TEST-006). Two findings raised: "
        "FIND-001 (privileged MFA coverage at 60%) and FIND-002 (standing IAM access "
        "outside the elevation path). Both trace to the same remediation item, REM-001. "
        "Joiner/mover/leaver and quarterly review controls operated without exception.",
    ),
    InternalAuditSpec(
        "AUD-002",
        "Data protection, logging and operational security",
        "Annex A controls A.5.33, A.5.34, A.8.10 to A.8.13, A.8.15 to A.8.17 and A.8.33, "
        "together with internal controls DP-001 to DP-005, OP-001 to OP-005.",
        "Determine whether customer personal data is protected through its lifecycle in "
        "production and non-production environments, and whether operational monitoring "
        "and recovery controls operate as designed.",
        "ISO/IEC 27001:2022 Annex A as listed, GDPR Articles 5 and 32, and the FinFlow "
        "information classification policy v2.1.",
        "Marcus Whitfield, Compliance Analyst",
        "The auditor holds no access to production data stores and did not participate in "
        "the design of the masking or retention controls. TEST-008 was executed by the "
        "Security Engineer, who does operate the environments concerned; that dependency is "
        "disclosed, and the workpaper was reviewed by the Head of Legal & Compliance rather "
        "than accepted on the tester's word.",
        date(2026, 7, 1), date(2026, 8, 31), date(2026, 7, 6), None,
        "IN_PROGRESS",
        "Six of nine planned tests complete. One FAIL raised so far: FIND-003, unmasked "
        "customer data in two non-production stores, traced to a design deficiency in "
        "DP-005. Remaining tests cover A.8.12, A.8.16 and A.8.17.",
    ),
    InternalAuditSpec(
        "AUD-003",
        "Full ISMS audit ahead of certification",
        "All ISMS clauses 4 to 10 and every applicable Annex A control per the Statement of "
        "Applicability v1.0.",
        "Determine whether the ISMS conforms to ISO/IEC 27001:2022 and to FinFlow's own "
        "requirements, and whether it is effectively implemented and maintained, ahead of "
        "the Stage 1 certification audit.",
        "ISO/IEC 27001:2022 in full, and the Statement of Applicability v1.0.",
        "External consultant, to be appointed",
        "This audit will be performed by an external party specifically because no internal "
        "person is independent of the ISMS as a whole. The two internal audits completed "
        "this year cover subsets where independence was achievable; a full-scope internal "
        "audit is not credible at this headcount.",
        date(2026, 11, 2), date(2026, 12, 18), None, None,
        "PLANNED", None,
    ),
]


class ManagementReviewSpec(NamedTuple):
    ref: str
    review_date: date
    chair: str
    attendees: str
    inputs_considered: str
    decisions: str
    actions: str
    next_review_date: date | None


MANAGEMENT_REVIEWS: list[ManagementReviewSpec] = [
    ManagementReviewSpec(
        "MR-2025-H2", date(2025, 12, 11),
        "Chief Executive Officer",
        "Chief Executive Officer (chair), Chief Technology Officer, Chief Operating "
        "Officer, Chief Financial Officer, Head of Legal & Compliance, Head of Engineering, "
        "Head of People.",
        "Clause 9.3.2 inputs considered:\n"
        "(a) Status of actions from the previous review — first formal review, none "
        "carried forward.\n"
        "(b) Changes in external and internal issues — India customer expansion brought "
        "new data protection obligations; headcount grew from 28 to 39.\n"
        "(c) ISMS performance: no nonconformities recorded to date; no internal audit yet "
        "performed; risk register at 17 risks.\n"
        "(d) Feedback from interested parties — three enterprise prospects made ISO 27001 "
        "certification a contractual precondition.\n"
        "(e) Results of risk assessment and status of the treatment plan — annual "
        "assessment refreshed November 2025.\n"
        "(f) Opportunities for continual improvement — proposed formalising the internal "
        "audit programme.",
        "Certification was confirmed as a funded objective for 2026 with a target of Q1 "
        "2027. The internal audit programme was approved. A proposal to pursue SOC 2 in "
        "parallel was rejected on the grounds that two frameworks at once would produce "
        "breadth without assurance; SOC 2 coverage will instead be derived by mapping from "
        "ISO.",
        "1. Appoint an ISMS owner and document security roles (Head of Legal & Compliance, "
        "Q1 2026) — completed, evidenced by GV-002.\n"
        "2. Define the internal audit programme (Head of Legal & Compliance, Q2 2026) — "
        "completed, AUD-001 executed.\n"
        "3. Approve the policy set (Chief Executive Officer, Q2 2026) — completed 30 April "
        "2026, evidenced by EV-029.",
        date(2026, 6, 1),
    ),
    ManagementReviewSpec(
        "MR-2026-H1", date(2026, 6, 24),
        "Chief Executive Officer",
        "Chief Executive Officer (chair), Chief Technology Officer, Chief Operating "
        "Officer, Chief Financial Officer, Head of Legal & Compliance, Head of Engineering, "
        "Head of People, Data Protection Officer.",
        "Clause 9.3.2 inputs considered:\n"
        "(a) Status of actions from MR-2025-H2 — all three actions closed.\n"
        "(b) Changes in external and internal issues — no change to the hosting region or "
        "product scope; the payment service provider relationship remains single-sourced.\n"
        "(c) ISMS performance: AUD-001 completed with two findings (FIND-001, FIND-002); "
        "one nonconformity raised (NC-001); SoA implementation at 66.7% of applicable "
        "controls; 17 remediation items open, 2 overdue; 3 evidence artifacts expired.\n"
        "(d) Feedback from interested parties — no customer security incidents or "
        "complaints in the period.\n"
        "(e) Risk assessment and treatment status — 20 risks on the register, 5 above "
        "category appetite (RISK-002, 004, 009, 010, 019).\n"
        "(f) Opportunities for continual improvement — evidence freshness and the absence "
        "of a continuity exercise were both raised.",
        "RISK-003 (single payment service provider) was formally accepted at current scale "
        "rather than mitigated; secondary PSP integration remains unfunded this year. "
        "RISK-004 was rejected for acceptance and must be remediated before the "
        "certification audit — the Chief Technology Officer noted that accepting a "
        "privileged access gap while seeking certification is not defensible. Business "
        "Continuity appetite was reaffirmed at High on the basis that hour-scale recovery "
        "objectives are appropriate to the company's stage.",
        "1. Close REM-001 (privileged MFA enforcement) before the Stage 1 audit (Head of "
        "Engineering, 31 October 2026) — in progress.\n"
        "2. Obtain the FY2026 AWS SOC 2 Type II report; the FY2025 report (EV-023) has "
        "expired and eight A.7 exclusion justifications currently rest on it (Head of Legal "
        "& Compliance, 30 September 2026) — open.\n"
        "3. Run the first continuity exercise covering loss of region and loss of the "
        "identity provider (Chief Operating Officer, 19 December 2026) — open, tracked as "
        "REM-003.\n"
        "4. Appoint an external auditor for the full-scope pre-certification audit AUD-003 "
        "(Chief Executive Officer, 30 September 2026) — open.",
        date(2026, 12, 9),
    ),
]


class NonconformitySpec(NamedTuple):
    ref: str
    description: str
    source: str
    identified_date: date
    identified_by: str
    owner: str
    immediate_correction: str
    root_cause_analysis: str | None
    corrective_action: str | None
    target_date: date | None
    effectiveness_check_date: date | None
    effectiveness_check_result: str | None
    status: str
    closure_date: date | None
    finding_ref: str | None


NONCONFORMITIES: list[NonconformitySpec] = [
    NonconformitySpec(
        "NC-001",
        "Clause 8.1: privileged access to production is not operating in accordance with "
        "the documented access control policy. The policy requires a phishing-resistant "
        "second factor on all privileged access; AUD-001 found six of fifteen privileged "
        "accounts operating outside that requirement.",
        "INTERNAL_AUDIT", date(2026, 7, 23), "Marcus Whitfield, Compliance Analyst",
        "Head of Engineering",
        "The two SMS-only engineer accounts were re-enrolled with hardware factors within "
        "48 hours of the finding. The four legacy IAM users were restricted to a "
        "read-only policy pending removal, which stops the immediate exposure without "
        "breaking the deployment pipeline that depends on them.",
        "The legacy IAM users predate the Okta migration in 2024 and were never included "
        "in it, because the migration scope was defined by human user accounts and these "
        "are service credentials used by humans. No control existed to detect access paths "
        "created before the policy, so the gap was invisible rather than accepted. The SMS "
        "enrolments arose because the sign-on policy treated SMS as acceptable until it "
        "was tightened in March 2026, and existing enrolments were not re-validated after "
        "the change.",
        "Two actions. First, migrate the four legacy IAM users to time-bound role "
        "assumption and delete the standing credentials, tracked as REM-001. Second, add a "
        "quarterly reconciliation of all AWS principals against Okta identity, so an access "
        "path created outside the standard process is detected rather than waiting for the "
        "next audit — this addresses the cause rather than the instance.",
        date(2026, 10, 31), date(2027, 1, 31), None,
        "CORRECTIVE_ACTION_IN_PROGRESS", None, "FIND-001",
    ),
    NonconformitySpec(
        "NC-002",
        "Clause 8.1: customer personal data is present in non-production environments "
        "contrary to the information classification policy, which requires Restricted data "
        "to be masked or synthetic outside production.",
        "INTERNAL_AUDIT", date(2026, 7, 31), "Marcus Whitfield, Compliance Analyst",
        "Head of Engineering",
        "Access to the analytics warehouse and the support tooling replica was restricted "
        "to two named engineers within 24 hours. The unmasked support replica was dropped "
        "and rebuilt from masked data on 3 August 2026; the analytics warehouse could not "
        "be rebuilt immediately without breaking active reporting.",
        "The masking job was designed and scoped in 2024, when the application database was "
        "the only non-production data store. The analytics warehouse and support replica "
        "were created later, and no step in the environment provisioning process requires "
        "the masking scope to be extended. The control did not degrade — it was never "
        "designed to cover what did not exist when it was written.",
        "Extend the masking job to all non-production data stores (REM-017), and add a "
        "masking scope check to the environment provisioning checklist so that a new "
        "non-production store cannot be created without one. The second action is the "
        "corrective one: without it the same gap reappears with the next environment.",
        date(2026, 10, 30), None, None,
        "CORRECTION_APPLIED", None, "FIND-003",
    ),
    NonconformitySpec(
        "NC-003",
        "Clause 7.5.3: a controlled document was not reviewed at its defined frequency. "
        "The incident response plan carried a 12-month review cycle and was found 4 months "
        "past its review date during preparation for AUD-001.",
        "INTERNAL_AUDIT", date(2026, 5, 12), "Head of Legal & Compliance",
        "Head of Engineering",
        "The incident response plan was reviewed and reissued as v1.3 on 29 May 2026, with "
        "the severity definitions and the Article 33 notification path updated.",
        "Document review dates were tracked in a spreadsheet with no reminder mechanism, so "
        "review depended on somebody noticing. The plan was not unique in this — three "
        "other controlled documents were within 60 days of the same failure.",
        "Review dates moved into the compliance calendar with automated reminders 30 days "
        "ahead, covering all controlled documents rather than only the incident response "
        "plan.",
        date(2026, 6, 30), date(2026, 8, 3),
        "Checked on 3 August 2026. Reminders fired correctly for two documents due in July, "
        "both of which were reviewed before their due date. No controlled document is "
        "currently past review. The corrective action is effective and the nonconformity is "
        "closed.",
        "CLOSED", date(2026, 8, 3), None,
    ),
]
