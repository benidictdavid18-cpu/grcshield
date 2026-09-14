"""Statement of Applicability — 93 entries, one per Annex A control.

Required by ISO/IEC 27001:2022 Clause 6.1.3 d).

Applicability follows FinFlow's operating profile: fully remote, no owned or leased
premises, all production infrastructure in AWS eu-west-1, no outsourced development.
Nine controls are excluded. Each exclusion justification says **where the risk went** —
transferred to a provider, addressed by a different control, or genuinely absent — since
a control that is merely "not applicable" with no onward destination is an unmanaged
risk with paperwork attached.

Eight inclusion justifications were written last, having been held as a
one-line hint: A.5.7, A.5.15, A.5.23, A.6.3, A.8.5, A.8.12, A.8.16 and A.8.28. Those
are the author's to write.
"""

from datetime import date
from typing import NamedTuple

ENG = "Head of Engineering"
LEGAL = "Head of Legal & Compliance"
PEOPLE = "Head of People"
COO = "Chief Operating Officer"
DPO = "Data Protection Officer"

NOT_IMPL = "NOT_IMPLEMENTED"
PARTIAL = "PARTIALLY_IMPLEMENTED"
IMPL = "IMPLEMENTED"

# The SoA is approved by top management, not by the security function. ISO/IEC
# 27001:2022 Clause 5.1 places accountability for the ISMS with leadership, and the SoA
# is the document that records what leadership has accepted.
SOA_VERSION = "1.0"
SOA_APPROVED_BY = "Chief Executive Officer"
SOA_APPROVED_DATE = date(2026, 5, 15)
SOA_LAST_REVIEWED = date(2026, 7, 31)
SOA_NEXT_REVIEW = date(2027, 1, 31)


class SoASpec(NamedTuple):
    ref: str
    applicable: bool
    status: str
    owner: str
    inclusion: str | None
    exclusion: str | None
    implementation: str | None
    controls: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    remediation: tuple[str, ...] = ()


SOA_ENTRIES: list[SoASpec] = [
    # ================= A.5 Organizational controls (37) =================
    SoASpec(
        "A.5.1", True, IMPL, LEGAL,
        "Enterprise customer contracts require a documented and approved security policy "
        "set, and RISK-009 makes certification a direct revenue dependency.",
        None,
        "Policy set v3.0 approved by leadership on 30 April 2026 and published to all staff "
        "with acknowledgement tracked.",
        ("GV-001",), ("RISK-009",), ("EV-029",),
    ),
    SoASpec(
        "A.5.2", True, IMPL, COO,
        "RISK-006 shows security accountability concentrated in a small number of people. "
        "Documented role assignment is what makes that concentration visible and reviewable.",
        None,
        "Security responsibilities assigned by role, documented in the ISMS scope document "
        "and reflected in job descriptions.",
        ("GV-002",), ("RISK-006",), ("EV-029",),
    ),
    SoASpec(
        "A.5.3", True, PARTIAL, COO,
        "RISK-018 (insider misuse of production access) depends on no single person being "
        "able to both make and approve a change to production.",
        None,
        "Pull request review enforces separation for code changes. Segregation in "
        "finance and vendor onboarding processes is not yet documented, and at forty "
        "people full separation is not achievable in every process.",
        ("CM-001",), ("RISK-018",), ("EV-019",), ("REM-010",),
    ),
    SoASpec(
        "A.5.4", True, IMPL, COO,
        "RISK-009 makes leadership engagement a certification prerequisite; management "
        "commitment is what turns the policy set into operating practice.",
        None,
        "Leadership approves the policy set annually and reviews ISMS performance at the "
        "management review meeting.",
        ("GV-002", "GV-001"), ("RISK-009",), ("EV-029",),
    ),
    SoASpec(
        "A.5.5", True, NOT_IMPL, LEGAL,
        "GDPR Article 33 imposes a 72-hour regulatory notification deadline. Without a "
        "recorded contact point for the supervisory authority, RISK-019 becomes a missed "
        "statutory deadline rather than a paperwork gap.",
        None,
        "No contact register exists. Notification routing would be improvised.",
        (), ("RISK-019", "RISK-008"), (), ("REM-007",),
    ),
    SoASpec(
        "A.5.6", True, NOT_IMPL, ENG,
        "RISK-011 (supply chain compromise) depends on learning about upstream package "
        "compromises from the security community before they reach production.",
        None,
        "Engineers follow vendor advisories informally. No membership or defined channel "
        "exists.",
        (), ("RISK-011",), (), ("REM-007",),
    ),
    SoASpec(
        "A.5.7", True, NOT_IMPL, ENG,
        "Necessary for RISK-011, supply chain compromise of an upstream dependency, and "
        "RISK-001, credential attacks against the customer base. Both are risks where "
        "FinFlow learns about a technique from outside or does not learn about it at "
        "all: a maintainer account compromise and a credential-stuffing campaign are "
        "both visible to the wider community before they are visible here. "
        "The proportionate version of this control at forty people is not a threat "
        "intelligence function. It is a named source list, a defined cadence, and a "
        "route into the risk review so that what is read changes something. FinFlow has "
        "none of the three, which is why this is recorded as a gap rather than argued "
        "away as disproportionate — the cost of the proportionate version is an hour a "
        "month, and that is not a scale argument.",
        None,
        "Threat information is consumed ad hoc by individual engineers with no defined "
        "sources, cadence or route into the risk assessment.",
        (), ("RISK-001", "RISK-011"), (), ("REM-008",),
    ),
    SoASpec(
        "A.5.8", True, PARTIAL, ENG,
        "RISK-012 (misconfiguration exposing data) originates in changes shipped without a "
        "security review at design time.",
        None,
        "Security is considered informally during design review. No explicit security "
        "requirement gate exists in the project intake checklist.",
        ("CM-001",), ("RISK-012",), ("EV-019",), ("REM-011",),
    ),
    SoASpec(
        "A.5.9", True, PARTIAL, ENG,
        "RISK-002 and RISK-012 both require knowing where customer data actually lives; an "
        "asset that is not inventoried cannot be protected or classified.",
        None,
        "Infrastructure assets are inventoried through Terraform state. Information assets "
        "and supplier-provided components are not.",
        ("CM-005",), ("RISK-002", "RISK-012"), ("EV-020",), ("REM-009",),
    ),
    SoASpec(
        "A.5.10", True, IMPL, LEGAL,
        "RISK-018 depends on staff understanding what constitutes acceptable use of "
        "production data before misuse becomes a disciplinary matter.",
        None,
        "Acceptable use policy published as part of policy set v3.0 with acknowledgement "
        "recorded at onboarding.",
        ("GV-001",), ("RISK-018",), ("EV-029",),
    ),
    SoASpec(
        "A.5.11", True, IMPL, PEOPLE,
        "RISK-018 extends past the leaving date: a departing engineer retaining a company "
        "laptop retains the data on it.",
        None,
        "Okta lifecycle deprovisioning plus laptop return tracked as part of the offboarding "
        "checklist, with same-day session revocation.",
        ("AC-005",), ("RISK-018",), ("EV-005",),
    ),
    SoASpec(
        "A.5.12", True, IMPL, LEGAL,
        "RISK-002 requires knowing which data is Restricted before deciding what protection "
        "it warrants; classification is the input to every handling rule.",
        None,
        "Four-tier classification defined in policy v2.1 with handling requirements per "
        "tier, applied to each production data store.",
        ("DP-003",), ("RISK-002",), ("EV-009",),
    ),
    SoASpec(
        "A.5.13", True, NOT_IMPL, LEGAL,
        "Classification under A.5.12 only changes behaviour if the classification is "
        "visible at the point of handling; RISK-002 turns on staff knowing what they hold.",
        None,
        "Tiers are defined but nothing is labelled, so handling rules cannot be applied "
        "consistently.",
        ("DP-003",), ("RISK-002",), ("EV-009",), ("REM-006",),
    ),
    SoASpec(
        "A.5.14", True, IMPL, ENG,
        "RISK-008 concerns personal data crossing jurisdictions; transfer controls are what "
        "keep that movement lawful and protected.",
        None,
        "TLS 1.2+ enforced on all external transfer paths; support tooling exposes masked "
        "records. Note the supporting scan evidence (EV-008) has expired.",
        ("DP-002", "DP-005"), ("RISK-008",), ("EV-008",),
    ),
    SoASpec(
        "A.5.15", True, PARTIAL, ENG,
        "Necessary for RISK-004, compromise of a privileged AWS account, and RISK-002, "
        "unauthorised access to customer personal data. Those two risks are the driver "
        "cited, and they are cited deliberately in preference to a compliance "
        "obligation. "
        "PCI DSS is not the reason. FinFlow does not store, process or transmit "
        "cardholder data — the payment service provider does — so PCI DSS requirements "
        "do not apply directly, and citing them here would be a claim the scope "
        "statement contradicts. Customer contracts do impose least-privilege and access "
        "review commitments, and those are real, but they are a secondary driver: they "
        "would not change what this control has to do, and the risks would demand it "
        "even with no contract in place. "
        "The gap is on the privileged path specifically. Policy exists and Okta enforces "
        "it for the workforce; RISK-004 records where enforcement stops.",
        None,
        "Access control policy is defined and enforced through Okta. Enforcement is "
        "incomplete on privileged AWS paths, which is the gap RISK-004 records.",
        ("AC-001", "AC-004"), ("RISK-002", "RISK-004"), ("EV-004",), ("REM-001",),
    ),
    SoASpec(
        "A.5.16", True, IMPL, ENG,
        "RISK-001 (credential stuffing) depends on every identity being uniquely "
        "attributable and centrally revocable.",
        None,
        "Okta is the single source of identity; shared accounts are prohibited outside "
        "documented break-glass exceptions.",
        ("AC-001", "AC-005"), ("RISK-001",), ("EV-001", "EV-005"),
    ),
    SoASpec(
        "A.5.17", True, IMPL, ENG,
        "RISK-001 exists precisely because passwords leak; how authentication secrets are "
        "issued and handled is the control that limits the consequence.",
        None,
        "Phishing-resistant factors issued through Okta; password policy and secret "
        "handling defined in policy set v3.0.",
        ("AC-002", "AC-001"), ("RISK-001",), ("EV-001",),
    ),
    SoASpec(
        "A.5.18", True, IMPL, ENG,
        "RISK-018 depends on entitlements being removed when they are no longer needed, not "
        "merely granted correctly at the start.",
        None,
        "Quarterly entitlement review with written owner attestation; revocations tracked to "
        "completion. Q2 2026 review completed on schedule.",
        ("AC-004", "AC-005"), ("RISK-018",), ("EV-004",),
    ),
    SoASpec(
        "A.5.19", True, IMPL, LEGAL,
        "RISK-010 makes vendor selection a security decision: FinFlow cannot test vendor "
        "controls directly, so the review before signature is the main lever available.",
        None,
        "Security review required before contract signature for any vendor handling company "
        "or customer data.",
        ("TP-001",), ("RISK-010",), ("EV-022",),
    ),
    SoASpec(
        "A.5.20", True, IMPL, LEGAL,
        "RISK-010 and RISK-008 both rest on contractual obligations — breach notification "
        "timeframes and GDPR Article 28 processor terms — being in the agreement.",
        None,
        "Standard supplier terms cover confidentiality, security obligations, breach "
        "notification and Article 28 processor terms where personal data is processed.",
        ("TP-003",), ("RISK-010", "RISK-008"), ("EV-024",),
    ),
    SoASpec(
        "A.5.21", True, PARTIAL, ENG,
        "RISK-011 is a supply chain risk: the components FinFlow ships include code it did "
        "not write and did not procure through a contract.",
        None,
        "Dependency alerting covers direct and transitive packages. The wider ICT supply "
        "chain — build tooling and infrastructure providers — is not yet inventoried.",
        ("CM-004", "TP-001"), ("RISK-011",), (), ("REM-009",),
    ),
    SoASpec(
        "A.5.22", True, IMPL, LEGAL,
        "RISK-003 and RISK-010 persist for the life of the relationship, not just at "
        "onboarding, so the assurance review has to recur.",
        None,
        "Annual review of critical vendor assurance reports. Note the AWS SOC 2 evidence "
        "(EV-023) has expired and the FY2026 report has been requested but not received.",
        ("TP-002",), ("RISK-003", "RISK-010"), ("EV-023",),
    ),
    SoASpec(
        "A.5.23", True, IMPL, ENG,
        "Necessary for RISK-007, extended regional outage, and RISK-012, dependency on a "
        "single infrastructure provider. It also carries the weight of the nine A.7 "
        "exclusions, which is the more important reason and the one an auditor will test. "
        "Under the AWS shared responsibility model FinFlow retains identity and access "
        "management, network and account configuration, encryption key management, "
        "operating system and application patching, and the data itself. AWS retains "
        "physical access to facilities, environmental controls, hardware lifecycle and "
        "secure media disposal. Every A.7 control excluded from this Statement of "
        "Applicability is excluded because it falls on the AWS side of that line, and "
        "this control is what makes the exclusions reviewable rather than convenient. "
        "The assurance relied on is the AWS SOC 2 Type II report, obtained and reviewed "
        "through the vendor review process. That reliance is currently weaker than it "
        "should be: the report on file has passed its validity date, which is recorded "
        "in the evidence register and is the reason KRI-006 sits amber. An exclusion "
        "resting on an expired report is an exclusion resting on what was true last "
        "year.",
        None,
        "Cloud services governed through the vendor review process and AWS account "
        "structure; shared responsibility boundaries documented in the ISMS scope.",
        ("TP-002", "CM-002"), ("RISK-007", "RISK-012"), ("EV-023", "EV-020"),
    ),
    SoASpec(
        "A.5.24", True, IMPL, ENG,
        "RISK-020 and RISK-004 both require a plan that exists before the incident, "
        "including who declares one and who talks to the regulator.",
        None,
        "Incident response plan v1.3 defines severity levels, incident commander role, "
        "communication paths and Article 33 notification timeframes.",
        ("IR-001",), ("RISK-020", "RISK-004"), ("EV-028",),
    ),
    SoASpec(
        "A.5.25", True, IMPL, ENG,
        "RISK-004 turns on how quickly a security event is recognised as an incident rather "
        "than absorbed as noise.",
        None,
        "GuardDuty and CloudTrail alerts route to an on-call rotation with severity-based "
        "triage timeframes; triage decisions recorded.",
        ("OP-002",), ("RISK-004", "RISK-012"), ("EV-013",),
    ),
    SoASpec(
        "A.5.26", True, IMPL, ENG,
        "RISK-004's impact is bounded by response speed once a privileged compromise is "
        "detected.",
        None,
        "Documented response procedures per severity with defined containment steps and an "
        "incident commander.",
        ("IR-001",), ("RISK-004",), ("EV-028",),
    ),
    SoASpec(
        "A.5.27", True, IMPL, ENG,
        "RISK-012 recurs unless the cause of each misconfiguration is addressed rather than "
        "just the symptom.",
        None,
        "Blameless post-incident review required for every severity 1 and 2 incident, with "
        "corrective actions tracked to closure.",
        ("IR-002",), ("RISK-012",), ("EV-031",),
    ),
    SoASpec(
        "A.5.28", True, PARTIAL, ENG,
        "RISK-018 may end in a disciplinary or legal process, which requires evidence "
        "collected in a form that survives scrutiny.",
        None,
        "Logs are retained for 12 months with restricted access. No documented forensic "
        "preservation procedure exists.",
        ("OP-001",), ("RISK-018",), ("EV-012",), ("REM-012",),
    ),
    SoASpec(
        "A.5.29", True, PARTIAL, COO,
        "RISK-007 and RISK-020 are both disruption scenarios where security controls must "
        "keep operating rather than being suspended to restore service.",
        None,
        "Continuity plan exists at draft v0.9 covering loss of region and loss of key "
        "personnel. It has never been exercised, so BC-001 is assessed on design only.",
        ("BC-001",), ("RISK-007", "RISK-020"), ("EV-030",), ("REM-003",),
    ),
    SoASpec(
        "A.5.30", True, PARTIAL, COO,
        "RISK-007 and RISK-017 define recovery objectives that only mean something if the "
        "technical capability to meet them has been demonstrated.",
        None,
        "Multi-AZ deployment and cross-region backup copies are in place and restore-tested. "
        "The full continuity exercise covering a regional loss has not yet run.",
        ("BC-001", "OP-005", "OP-006"), ("RISK-007", "RISK-017"),
        ("EV-016", "EV-030"), ("REM-003",),
    ),
    SoASpec(
        "A.5.31", True, PARTIAL, LEGAL,
        "GDPR applies to FinFlow's EU customers and Indian data protection law to its Indian "
        "ones. RISK-019 records what happens when those statutory obligations are not "
        "tracked systematically.",
        None,
        "Obligations are identified for GDPR but not maintained as a register with owners "
        "and review dates.",
        ("GV-003",), ("RISK-019", "RISK-008"), (), ("REM-002",),
    ),
    SoASpec(
        "A.5.32", True, IMPL, LEGAL,
        "Open-source licence terms and customer contractual warranties both create legal "
        "obligations around software provenance that RISK-014 would surface as a dispute.",
        None,
        "Intellectual property and open-source usage terms defined in policy set v3.0; "
        "licence scanning runs as part of dependency review.",
        ("GV-001", "CM-004"), ("RISK-014",), ("EV-029",),
    ),
    SoASpec(
        "A.5.33", True, IMPL, LEGAL,
        "RISK-016 concerns statutory retention and disclosure obligations — records must be "
        "retrievable for as long as the law requires and no longer.",
        None,
        "Retention schedule defined per data category and enforced by scheduled deletion "
        "jobs, with execution logged.",
        ("DP-004",), ("RISK-016",), ("EV-010",),
    ),
    SoASpec(
        "A.5.34", True, PARTIAL, DPO,
        "GDPR Articles 5, 30 and 35 impose direct statutory duties on FinFlow as controller "
        "for EU personal data. RISK-002, RISK-016 and RISK-019 all trace to this control.",
        None,
        "Classification and retention controls operate. The Record of Processing Activities "
        "is incomplete and DPIAs are not yet performed for all high-risk processing.",
        ("DP-003", "DP-004"), ("RISK-002", "RISK-016", "RISK-019"),
        ("EV-009", "EV-010"), ("REM-002",),
    ),
    SoASpec(
        "A.5.35", True, NOT_IMPL, LEGAL,
        "RISK-009 makes certification a revenue dependency, and Clause 9.2 makes independent "
        "review a precondition of certification.",
        None,
        "No independent review of the ISMS has been performed. The internal audit programme "
        "is defined in Phase 4 of this project but has not yet run a cycle.",
        (), ("RISK-009",), (), ("REM-004",),
    ),
    SoASpec(
        "A.5.36", True, PARTIAL, LEGAL,
        "RISK-009 depends on policies being followed, not merely published; an unverified "
        "policy set is documentation rather than control.",
        None,
        "Policies are published and acknowledged. Compliance with them is not yet verified "
        "through a review cycle.",
        ("GV-001",), ("RISK-009",), ("EV-029",), ("REM-004",),
    ),
    SoASpec(
        "A.5.37", True, IMPL, ENG,
        "RISK-012 originates in inconsistent operational practice; documented procedures are "
        "what make the safe path the default one.",
        None,
        "Security operating procedures documented alongside the policy set; infrastructure "
        "procedures encoded as Terraform modules with review.",
        ("GV-001", "CM-005"), ("RISK-012",), ("EV-029", "EV-020"),
    ),
    # ================= A.6 People controls (8) =================
    SoASpec(
        "A.6.1", True, IMPL, PEOPLE,
        "RISK-018 (insider misuse) is partly addressed before hire, by verifying who is "
        "being granted production access in the first place.",
        None,
        "Identity, right to work and employment history verified before start date, "
        "proportionate to role and local law.",
        ("HR-001",), ("RISK-018",), ("EV-025",),
    ),
    SoASpec(
        "A.6.2", True, IMPL, PEOPLE,
        "RISK-018 requires security obligations to be contractually binding on staff, not "
        "merely stated in a policy.",
        None,
        "Employment contracts carry security and confidentiality obligations; contractors "
        "sign equivalent terms before access is granted.",
        ("HR-003",), ("RISK-018",), ("EV-027",),
    ),
    SoASpec(
        "A.6.3", True, IMPL, PEOPLE,
        "Necessary for RISK-015, successful phishing of a member of staff, and for "
        "A.6.8 event reporting, which depends on it. Both are cited, because they need "
        "different things from the same control and citing only the phishing risk would "
        "understate what training has to cover. "
        "Awareness reduces the likelihood that someone clicks. Reporting depends on "
        "someone who has already clicked being willing to say so quickly, which is a "
        "cultural outcome of how the training is delivered rather than of its content. "
        "A programme that produces compliance without candour satisfies this control and "
        "quietly breaks A.6.8. "
        "Completion at 94% is not acceptable as a resting state, and the number is "
        "recorded here rather than rounded because the residual 6% is the population "
        "that matters. Six per cent of forty people is between two and three "
        "individuals, and one phished account is sufficient. Outstanding staff are "
        "escalated to line managers; the control is rated implemented because the "
        "programme operates as designed, not because coverage is complete.",
        None,
        "Onboarding training within 30 days and annual refresher, currently at 94% "
        "completion with outstanding staff escalated to line managers.",
        ("HR-002",), ("RISK-015",), ("EV-026",),
    ),
    SoASpec(
        "A.6.4", True, IMPL, PEOPLE,
        "RISK-018 only carries deterrent weight if there is a defined consequence for "
        "deliberate misuse.",
        None,
        "Disciplinary process for security violations defined in policy set v3.0 and "
        "referenced in employment terms.",
        ("GV-001", "HR-003"), ("RISK-018",), ("EV-029",),
    ),
    SoASpec(
        "A.6.5", True, IMPL, PEOPLE,
        "RISK-018 does not end at the termination date; obligations that survive employment "
        "are what make post-departure misuse actionable.",
        None,
        "Confidentiality obligations survive termination by contract; access revoked "
        "same-day through Okta lifecycle automation.",
        ("AC-005", "HR-003"), ("RISK-018",), ("EV-005", "EV-027"),
    ),
    SoASpec(
        "A.6.6", True, IMPL, PEOPLE,
        "RISK-010 and RISK-018 both require enforceable confidentiality obligations on the "
        "people and organisations holding FinFlow data.",
        None,
        "Confidentiality terms signed by all employees and contractors before system access; "
        "equivalent terms in supplier agreements.",
        ("HR-003", "TP-003"), ("RISK-010", "RISK-018"), ("EV-027", "EV-024"),
    ),
    SoASpec(
        "A.6.7", True, IMPL, ENG,
        "FinFlow has no offices, so every member of staff works remotely all of the time. "
        "RISK-015 is therefore the normal operating condition rather than an exception.",
        None,
        "Managed laptops with disk encryption, screen lock, EDR and phishing-resistant MFA; "
        "no reliance on network location for trust.",
        ("OP-007", "AC-002"), ("RISK-015",), ("EV-018",),
    ),
    SoASpec(
        "A.6.8", True, IMPL, ENG,
        "RISK-015 depends on a phished employee telling someone quickly; detection tooling "
        "does not cover the cases that never touch a monitored system.",
        None,
        "Reporting route defined in the incident response plan and covered in awareness "
        "training; no-blame reporting stated explicitly.",
        ("HR-002", "IR-001"), ("RISK-015",), ("EV-026", "EV-028"),
    ),
    # ================= A.7 Physical controls (14) =================
    SoASpec(
        "A.7.1", False, NOT_IMPL, COO, None,
        "FinFlow holds no owned or leased premises. Perimeter risk for production systems is "
        "transferred to AWS under the shared responsibility model and assured through the "
        "provider's SOC 2 Type II report, reviewed annually under vendor control TP-001 and "
        "TP-002. Note the current report (EV-023) has expired, which leaves this exclusion "
        "temporarily unsupported.",
        None, (), (), ("EV-023",),
    ),
    SoASpec(
        "A.7.2", False, NOT_IMPL, COO, None,
        "No company-controlled entry points exist. Physical entry authorisation for the "
        "systems processing customer data is an AWS responsibility, assured through their "
        "SOC 2 Type II report under TP-002.",
        None, (), (), ("EV-023",),
    ),
    SoASpec(
        "A.7.3", False, NOT_IMPL, COO, None,
        "FinFlow operates no offices, rooms or facilities. The residual risk that this "
        "control would address — staff working in uncontrolled environments — is retained "
        "and managed through A.6.7 (Remote working) and A.7.9 (Security of assets "
        "off-premises), both of which are applicable and implemented.",
        None, (), (), (),
    ),
    SoASpec(
        "A.7.4", False, NOT_IMPL, COO, None,
        "There are no premises to monitor. Monitoring of the estate that actually holds "
        "customer data is logical rather than physical and is addressed by A.8.16 "
        "(Monitoring activities), which is applicable and implemented.",
        None, (), (), (),
    ),
    SoASpec(
        "A.7.5", False, NOT_IMPL, COO, None,
        "Protection against fire, flood and environmental hazard for production "
        "infrastructure is an AWS responsibility under the shared responsibility model. The "
        "availability consequence is retained by FinFlow and managed through A.8.14 "
        "(Redundancy) and RISK-007, which is formally accepted at Chief Executive Officer "
        "level.",
        None, (), (), ("EV-023",),
    ),
    SoASpec(
        "A.7.6", False, NOT_IMPL, COO, None,
        "FinFlow operates no secure areas, so there are no procedures for working in them. "
        "The equivalent restriction — limiting who can reach sensitive information — is "
        "enforced logically through A.8.3 (Information access restriction).",
        None, (), (), (),
    ),
    SoASpec(
        "A.7.7", True, IMPL, ENG,
        "A remote workforce relocates this risk into homes and public spaces rather than "
        "removing it; RISK-015 covers the endpoint that is left unlocked.",
        None,
        "Screen lock enforced by MDM after inactivity; clear desk expectations set in the "
        "acceptable use policy for staff working in shared spaces.",
        ("OP-007", "GV-001"), ("RISK-015",), ("EV-018",),
    ),
    SoASpec(
        "A.7.8", True, IMPL, ENG,
        "Company laptops sit in homes, cafés and co-working spaces. RISK-015 is the "
        "consequence of one being accessed while unattended.",
        None,
        "Guidance on device siting issued to all staff; full-disk encryption and screen lock "
        "enforced so that physical proximity alone does not yield access.",
        ("OP-007",), ("RISK-015",), ("EV-018",),
    ),
    SoASpec(
        "A.7.9", True, IMPL, ENG,
        "Every FinFlow asset is permanently off-premises, so this control describes the "
        "normal case rather than an exception. RISK-015 and RISK-002 both depend on it.",
        None,
        "All laptops enrolled in MDM with full-disk encryption, remote wipe capability and "
        "compliance reporting.",
        ("OP-007",), ("RISK-015", "RISK-002"), ("EV-018",),
    ),
    SoASpec(
        "A.7.10", True, PARTIAL, ENG,
        "RISK-002 extends to customer data that leaves the primary data store on removable "
        "media or in local exports.",
        None,
        "Laptop storage is encrypted and removable media use is discouraged by policy. "
        "Media handling and disposal procedures are not documented, and deletion coverage "
        "for local exports is incomplete.",
        ("OP-007", "DP-004"), ("RISK-002",), ("EV-018",), ("REM-013",),
    ),
    SoASpec(
        "A.7.11", False, NOT_IMPL, COO, None,
        "FinFlow provides no supporting utilities. Power and cooling for the infrastructure "
        "holding customer data are provided and assured by AWS under the shared "
        "responsibility model, reviewed annually under TP-002.",
        None, (), (), ("EV-023",),
    ),
    SoASpec(
        "A.7.12", False, NOT_IMPL, COO, None,
        "FinFlow owns no cabling infrastructure. The underlying risk — interception or "
        "interference with data in transit — is retained and addressed by A.8.24 (Use of "
        "cryptography), which enforces TLS 1.2+ on all transfer paths.",
        None, (), (), (),
    ),
    SoASpec(
        "A.7.13", True, NOT_IMPL, PEOPLE,
        "A laptop sent for repair leaves FinFlow's control while still holding company data, "
        "which is a RISK-002 exposure with no compensating control today.",
        None,
        "No documented procedure governs data handling when devices are sent for repair or "
        "replacement.",
        (), ("RISK-002",), (), ("REM-016",),
    ),
    SoASpec(
        "A.7.14", True, IMPL, PEOPLE,
        "RISK-002 persists past the end of a device's life; a returned or resold laptop "
        "carries whatever was not securely erased.",
        None,
        "Devices wiped through MDM on return and cryptographically erased before disposal or "
        "reissue; disposal recorded in the offboarding checklist.",
        ("AC-005", "OP-007"), ("RISK-002",), ("EV-005", "EV-018"),
    ),
    # ================= A.8 Technological controls (34) =================
    SoASpec(
        "A.8.1", True, IMPL, ENG,
        "Endpoints are the only devices FinFlow physically issues, and RISK-015 makes them "
        "the most likely initial foothold.",
        None,
        "All laptops MDM-enrolled with encryption, automatic updates, screen lock and EDR. "
        "EDR rollout closed under REM-018.",
        ("OP-007",), ("RISK-015",), ("EV-018",), ("REM-018",),
    ),
    SoASpec(
        "A.8.2", True, PARTIAL, ENG,
        "RISK-004 is entirely about privileged access: standing administrative credentials "
        "are what turn a phished password into a production compromise.",
        None,
        "Privileged access granted through time-bound role assumption in AWS IAM Identity "
        "Center, with elevation logged. Some legacy paths still permit standing access.",
        ("AC-003",), ("RISK-004", "RISK-002"), ("EV-003",), ("REM-001",),
    ),
    SoASpec(
        "A.8.3", True, IMPL, ENG,
        "RISK-002 depends on engineers being able to reach only the data their role "
        "requires.",
        None,
        "Access restricted by role through Okta group membership and AWS permission sets; "
        "repository access assigned by team.",
        ("AC-001", "AC-006"), ("RISK-002",), ("EV-006", "EV-003"),
    ),
    SoASpec(
        "A.8.4", True, IMPL, ENG,
        "RISK-011 includes deliberate modification of FinFlow's own code, not only "
        "compromise of upstream packages.",
        None,
        "Repository permissions assigned to teams; write access to production repositories "
        "limited to the owning team with branch protection enforced.",
        ("AC-006", "CM-001"), ("RISK-011",), ("EV-006", "EV-019"),
    ),
    SoASpec(
        "A.8.5", True, PARTIAL, ENG,
        "Necessary for RISK-004, compromise of a privileged AWS account through "
        "incomplete MFA enforcement, and for RISK-001, customer account takeover. "
        "RISK-004 is the primary driver and the reason this entry is only partially "
        "implemented. "
        "For the workforce, secure authentication means what the control says: a "
        "phishing-resistant factor enforced through the Okta sign-on policy. For the "
        "privileged population it means that for nine of fifteen accounts, and for the "
        "remaining six it means a password. EV-002 is the Okta enrolment export behind "
        "that figure and TEST-003 examined the full population of fifteen rather than a "
        "sample, so 60% is a count and not an estimate. "
        "The six uncovered accounts are the ones that matter most. They reach production "
        "infrastructure and the customer data in it, and they authenticate on legacy "
        "paths that bypass the sign-on policy entirely — so the control is not weaker "
        "for them, it is absent. Recording this entry as implemented because the policy "
        "exists and most users are covered would be exactly the overstatement the "
        "Statement of Applicability exists to prevent.",
        None,
        "Phishing-resistant MFA enforced through Okta for all users. Privileged account "
        "coverage stands at 60% (EV-002): nine of fifteen privileged accounts have a "
        "compliant factor enrolled, with six on legacy password-only paths.",
        ("AC-002",), ("RISK-004", "RISK-001"), ("EV-001", "EV-002"), ("REM-001",),
    ),
    SoASpec(
        "A.8.6", True, PARTIAL, ENG,
        "RISK-014 is a contractual availability commitment; capacity exhaustion is one of "
        "the ways that commitment gets breached.",
        None,
        "Multi-AZ deployment provides headroom and autoscaling responds to load. Capacity is "
        "observed reactively rather than against defined thresholds with advance alerting.",
        ("OP-006",), ("RISK-014",), ("EV-017",), ("REM-014",),
    ),
    SoASpec(
        "A.8.7", True, IMPL, ENG,
        "RISK-015 ends at the endpoint, where malware is the usual payload of a successful "
        "phish.",
        None,
        "EDR deployed across the macOS fleet with alerting into the on-call rotation; agent "
        "health reported through MDM compliance. Rollout closed under REM-018.",
        ("OP-007",), ("RISK-015",), ("EV-018",), ("REM-018",),
    ),
    SoASpec(
        "A.8.8", True, IMPL, ENG,
        "RISK-005 is the direct expression of this control failing: a known CVE left "
        "unpatched on an internet-facing service.",
        None,
        "Image and dependency scanning on build and weekly; severity-based remediation SLAs "
        "of 7/30/90 days. Medium-severity SLA adherence currently shows a 12% breach rate.",
        ("OP-003", "OP-004", "CM-004"), ("RISK-005",), ("EV-014", "EV-015"),
    ),
    SoASpec(
        "A.8.9", True, IMPL, ENG,
        "RISK-012 originates in configuration drift; a baseline that is not defined cannot "
        "be checked.",
        None,
        "Infrastructure defined in Terraform with review required; console changes in "
        "production treated as incidents. Migration closed under REM-019.",
        ("CM-005",), ("RISK-012",), ("EV-020",), ("REM-019",),
    ),
    SoASpec(
        "A.8.10", True, PARTIAL, LEGAL,
        "GDPR Article 17 gives data subjects a right to erasure, and RISK-016 records what "
        "happens when data cannot be located to delete it.",
        None,
        "Scheduled deletion jobs cover the primary database. Object storage exports, support "
        "attachments and local copies are not yet in scope.",
        ("DP-004",), ("RISK-016",), ("EV-010",), ("REM-013",),
    ),
    SoASpec(
        "A.8.11", True, PARTIAL, ENG,
        "RISK-008 concerns support staff in India reaching EU personal data during ordinary "
        "work; masking removes the need for that access to be raw.",
        None,
        "Downgraded from Implemented after TEST-008. The masking job covers the primary "
        "application database and operates correctly there, but not the analytics warehouse "
        "or the support tooling replica, both of which were found holding unmasked customer "
        "records. This is a deficiency in the control's design scope rather than its "
        "execution.",
        ("DP-005",), ("RISK-008",), ("EV-011",), ("REM-017",),
    ),
    SoASpec(
        "A.8.12", True, NOT_IMPL, ENG,
        "Necessary for RISK-018, insider misuse of production data access, and RISK-002, "
        "unauthorised access to customer personal data. RISK-018 is the primary driver: "
        "it is currently at its inherent level with no reduction claimed, and it is one "
        "of the risks above appetite with no live acceptance covering it. "
        "Full data loss prevention tooling — endpoint agents, mail inspection, egress "
        "classification — is not proportionate at forty people with no premises and no "
        "corporate network to place a gateway on. That argument is sound and it is not "
        "sufficient to exclude the control, because the objective is preventing "
        "unauthorised extraction, not buying a product. "
        "The honest position is that A.8.3 restriction of information access and A.8.11 "
        "data masking were expected to carry this objective between them, and A.8.11 is "
        "not currently carrying anything: TEST-008 rated DP-005 ineffective across the "
        "analytics warehouse and the support tooling. So the load-bearing half of the "
        "compensating argument is broken, and this entry stays applicable and not "
        "implemented until either masking is re-tested or a proportionate control is "
        "chosen for the extraction path itself.",
        None,
        "No data loss prevention capability exists on email, endpoints or support tooling.",
        (), ("RISK-018", "RISK-002"), (), ("REM-005",),
    ),
    SoASpec(
        "A.8.13", True, IMPL, ENG,
        "RISK-017 is the direct expression of backup failure, and its impact of 5 cannot be "
        "reduced by any other control.",
        None,
        "Daily automated backups with point-in-time recovery and cross-region copies; restore "
        "exercised on a defined schedule with the June 2026 test recorded.",
        ("OP-005",), ("RISK-017",), ("EV-016",),
    ),
    SoASpec(
        "A.8.14", True, IMPL, ENG,
        "RISK-007 retains an availability consequence that AWS's own resilience does not "
        "remove; redundancy inside the region is what FinFlow controls.",
        None,
        "Production compute and database tiers run across at least two availability zones "
        "with automated failover.",
        ("OP-006",), ("RISK-007",), ("EV-017",),
    ),
    SoASpec(
        "A.8.15", True, IMPL, ENG,
        "RISK-018 is detected rather than prevented; without logs there is no detection and "
        "no evidence afterwards.",
        None,
        "Application, infrastructure and CloudTrail logs shipped to a dedicated logging "
        "account with restricted access and 12-month retention.",
        ("OP-001",), ("RISK-018",), ("EV-012",),
    ),
    SoASpec(
        "A.8.16", True, IMPL, ENG,
        "Necessary for RISK-004, privileged account compromise, and RISK-012, provider "
        "dependency. It also carries the A.7.4 physical monitoring exclusion, and all "
        "three are cited because the exclusion is the one that would surprise an "
        "auditor. "
        "For RISK-004 this is the control that shortens the incident rather than "
        "preventing it — the compensating control the CTO named when refusing EXC-004, "
        "and named as detective for exactly that reason. For RISK-012 it is how a "
        "provider-side problem becomes visible before a customer reports it. "
        "A.7.4 is excluded because FinFlow has no premises to monitor, and an exclusion "
        "on those grounds is only honest if the risk it would have addressed went "
        "somewhere. It went here. Unauthorised access to the estate is a logical event "
        "for this organisation, detected through GuardDuty, Config and CloudTrail with "
        "severity-based triage and ninety days of triage records, rather than a physical "
        "one detected by cameras and door logs.",
        None,
        "GuardDuty, Config and CloudTrail alerting routed to an on-call rotation with "
        "severity-based triage timeframes; 90 days of triage records retained.",
        ("OP-002",), ("RISK-004", "RISK-012"), ("EV-013",),
    ),
    SoASpec(
        "A.8.17", True, IMPL, ENG,
        "RISK-018 depends on log timestamps being comparable across systems; correlation "
        "fails silently when clocks disagree.",
        None,
        "All AWS compute uses the Amazon Time Sync Service; log timestamps normalised to UTC "
        "at ingestion.",
        ("OP-001",), ("RISK-018",), ("EV-012",),
    ),
    SoASpec(
        "A.8.18", True, IMPL, ENG,
        "RISK-004 concerns exactly this: tooling that can override normal access controls in "
        "the hands of someone who should not hold it.",
        None,
        "Administrative tooling reachable only through time-bound privileged role assumption, "
        "with use logged to CloudTrail.",
        ("AC-003",), ("RISK-004",), ("EV-003",),
    ),
    SoASpec(
        "A.8.19", True, PARTIAL, ENG,
        "RISK-015 extends past the initial phish: unrestricted software installation is how a "
        "foothold becomes persistence.",
        None,
        "Managed software distributed through MDM and patched automatically. Engineers retain "
        "local administrator rights, so unapproved installation is not prevented.",
        ("OP-007", "OP-004"), ("RISK-015",), ("EV-018",), ("REM-015",),
    ),
    SoASpec(
        "A.8.20", True, IMPL, ENG,
        "RISK-012 includes security group misconfiguration exposing internal services to the "
        "internet.",
        None,
        "Network boundaries defined in Terraform with default-deny security groups; public "
        "exposure changes flagged by Config rules.",
        ("CM-002", "CM-005"), ("RISK-012",), ("EV-020",),
    ),
    SoASpec(
        "A.8.21", True, IMPL, ENG,
        "RISK-012 and RISK-008 both depend on the security properties of the network services "
        "carrying customer data.",
        None,
        "Managed AWS network services used with encryption in transit enforced; service "
        "configuration held in Terraform.",
        ("CM-002", "DP-002"), ("RISK-012", "RISK-008"), ("EV-020",),
    ),
    SoASpec(
        "A.8.22", True, IMPL, ENG,
        "RISK-012 is bounded by whether a misconfiguration in a lower environment can reach "
        "production.",
        None,
        "Development, staging and production run in separate AWS accounts with no network "
        "path between lower environments and production.",
        ("CM-002",), ("RISK-012",), ("EV-020",),
    ),
    SoASpec(
        "A.8.23", True, NOT_IMPL, ENG,
        "RISK-015 begins with a staff member reaching a malicious site; nothing currently "
        "intervenes between the click and the payload.",
        None,
        "No web filtering is applied to the macOS fleet.",
        (), ("RISK-015",), (), ("REM-015",),
    ),
    SoASpec(
        "A.8.24", True, IMPL, ENG,
        "RISK-002 and RISK-008 both depend on cryptography, and it is also the control that "
        "carries the retained risk from the A.7.12 cabling exclusion.",
        None,
        "Encryption at rest with customer-managed KMS keys; TLS 1.2+ enforced in transit with "
        "weak ciphers disabled. Key policies restrict administrative use.",
        ("DP-001", "DP-002"), ("RISK-002", "RISK-008"), ("EV-007",),
    ),
    SoASpec(
        "A.8.25", True, IMPL, ENG,
        "RISK-011 and RISK-005 both arise during development rather than in operation.",
        None,
        "Security activities embedded in the development lifecycle: peer review, SAST on "
        "every pull request and dependency scanning before merge.",
        ("CM-001", "CM-003"), ("RISK-011", "RISK-005"), ("EV-019", "EV-021"),
    ),
    SoASpec(
        "A.8.26", True, IMPL, ENG,
        "RISK-005 is an application-layer exposure; requirements defined before build are "
        "cheaper than findings after release.",
        None,
        "Security requirements defined for authentication, authorisation, input validation "
        "and logging, enforced through review and SAST rules.",
        ("CM-003", "CM-001"), ("RISK-005",), ("EV-021",),
    ),
    SoASpec(
        "A.8.27", True, IMPL, ENG,
        "RISK-012 is an architectural property as much as an operational one — isolation "
        "boundaries are decided at design time.",
        None,
        "Account isolation, least-privilege IAM and default-deny networking applied as "
        "standing architectural principles, encoded in Terraform modules.",
        ("CM-002", "CM-005"), ("RISK-012",), ("EV-020",),
    ),
    SoASpec(
        "A.8.28", True, IMPL, ENG,
        "Necessary for RISK-005, exploitation of an application vulnerability in the "
        "payments platform, and RISK-011, malicious or vulnerable third-party "
        "dependency. RISK-005 is the primary driver: it concerns code FinFlow writes, "
        "which is what this control governs, while RISK-011 concerns code FinFlow "
        "imports and is treated principally through OP-003 scanning at the build gate. "
        "The coding weaknesses that matter for a payments product are not generic. "
        "Broken authorisation on transaction endpoints, where a request is authenticated "
        "but not checked against ownership of the merchant account it names; missing "
        "idempotency on payment submission, where a retried request becomes a second "
        "charge; and injection into the reconciliation and reporting paths that read "
        "across merchants. Those are the classes peer review and SAST are configured to "
        "block, and high-severity findings either block merge or carry a recorded "
        "waiver. "
        "Secure coding obligations do flow down from the payment service provider "
        "contract. They are noted rather than cited as the driver, because the risks "
        "would require this control on their own and a justification that leans on a "
        "contract is only as durable as the contract.",
        None,
        "Secure coding standards enforced through peer review and SAST; high-severity "
        "findings block merge or carry a recorded waiver.",
        ("CM-001", "CM-003"), ("RISK-011", "RISK-005"), ("EV-021", "EV-019"),
    ),
    SoASpec(
        "A.8.29", True, PARTIAL, ENG,
        "RISK-005 depends on vulnerabilities being found before release rather than by an "
        "attacker afterwards.",
        None,
        "SAST and image scanning run in the pipeline. No independent penetration test has "
        "been commissioned and there is no formal security acceptance gate before release.",
        ("CM-003", "OP-003"), ("RISK-005",), ("EV-021", "EV-014"), ("REM-011",),
    ),
    SoASpec(
        "A.8.30", False, NOT_IMPL, ENG, None,
        "All software is developed in-house by FinFlow engineers. No development is "
        "outsourced to a third party, so there is no supplier development activity to direct "
        "or monitor. Risk arising from third-party *code* rather than third-party "
        "*developers* is retained and managed under A.5.21 and A.8.28, and recorded as "
        "RISK-011. This exclusion will be revisited if contract development is ever engaged.",
        None, (), (), (),
    ),
    SoASpec(
        "A.8.31", True, IMPL, ENG,
        "RISK-012 is contained by ensuring a change tested in staging cannot affect "
        "production data.",
        None,
        "Separate AWS accounts per environment with independent credentials and no shared "
        "data stores.",
        ("CM-002",), ("RISK-012",), ("EV-020",),
    ),
    SoASpec(
        "A.8.32", True, IMPL, ENG,
        "RISK-012 originates in unreviewed change; controlled change is the primary "
        "preventive control against it.",
        None,
        "All production changes flow through reviewed pull requests with required status "
        "checks; infrastructure changes applied through Terraform. Closed under REM-019.",
        ("CM-001", "CM-005"), ("RISK-012",), ("EV-019", "EV-020"), ("REM-019",),
    ),
    SoASpec(
        "A.8.33", True, PARTIAL, ENG,
        "RISK-008 covers personal data reaching environments and people it should not; test "
        "datasets are one of the ways that happens quietly.",
        None,
        "The main application database is masked in non-production. Analytics and support "
        "environments still receive partially unmasked extracts.",
        ("DP-005",), ("RISK-008",), ("EV-011",), ("REM-017",),
    ),
    SoASpec(
        "A.8.34", True, NOT_IMPL, LEGAL,
        "RISK-009 requires an audit programme, and audit activity against production systems "
        "is itself capable of causing the disruption it is meant to prevent.",
        None,
        "No audit testing has been performed, so no protective arrangements exist. This will "
        "be defined alongside the internal audit programme.",
        (), ("RISK-009",), (), ("REM-004",),
    ),
]
