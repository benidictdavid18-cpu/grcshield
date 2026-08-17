"""Risk appetite thresholds and the 20-risk register.

Every residual score here was chosen by hand against FinFlow's profile, not derived.
Read any row as a claim an auditor could challenge: the justification must name which
control moved which dimension, and why the other dimension did not move.

Five justifications are deliberately left as ``TODO AUTHOR:BENNY`` — RISK-002, 007,
011, 014 and 018. Those are the author's to write.
"""

from datetime import date
from typing import NamedTuple

from app.services.risk_scoring import (
    ControlEffectivenessBasis as Basis,
)
from app.services.risk_scoring import (
    RiskBand,
    RiskCategory,
    RiskStatus,
    TreatmentDecision,
)

TODO = "TODO AUTHOR:BENNY"


class AppetiteSpec(NamedTuple):
    category: RiskCategory
    max_acceptable_band: RiskBand
    approver_role: str
    rationale: str


# Appetite is set by whoever answers for the consequence. None of these approvers is
# the security function -- security advises on risk, the business accepts it.
APPETITE_THRESHOLDS: list[AppetiteSpec] = [
    AppetiteSpec(
        RiskCategory.CYBERSECURITY,
        RiskBand.MEDIUM,
        "Chief Technology Officer",
        "Operating an internet-facing product carries irreducible attack surface. Medium "
        "residual exposure is accepted where controls are tested; anything above it "
        "competes for engineering time against roadmap delivery and needs a decision.",
    ),
    AppetiteSpec(
        RiskCategory.DATA_PRIVACY,
        RiskBand.LOW,
        "Data Protection Officer",
        "GDPR exposure is asymmetric: fines reach 4% of global turnover and reputational "
        "damage in payments is not recoverable. The lowest appetite of any category.",
    ),
    AppetiteSpec(
        RiskCategory.THIRD_PARTY,
        RiskBand.MEDIUM,
        "Chief Operating Officer",
        "A 40-person company runs on other companies' software. Vendor risk cannot be "
        "engineered away, only selected and monitored, so medium residual is the "
        "realistic floor.",
    ),
    AppetiteSpec(
        RiskCategory.OPERATIONAL,
        RiskBand.MEDIUM,
        "Chief Operating Officer",
        "Process and people risks are absorbed by a small team that can adapt quickly. "
        "Medium is tolerable where a workaround exists.",
    ),
    AppetiteSpec(
        RiskCategory.FINANCIAL,
        RiskBand.LOW,
        "Chief Financial Officer",
        "Direct loss and fraud exposure hits a pre-profitability balance sheet "
        "immediately and is visible to investors. Low appetite.",
    ),
    AppetiteSpec(
        RiskCategory.LEGAL,
        RiskBand.MEDIUM,
        "Head of Legal & Compliance",
        "Contractual disputes are bounded, insurable and negotiable. Medium residual is "
        "acceptable where liability caps are in place.",
    ),
    AppetiteSpec(
        RiskCategory.COMPLIANCE,
        RiskBand.LOW,
        "Head of Legal & Compliance",
        "Enterprise deals are gated on certification and regulatory standing. A "
        "compliance failure removes revenue rather than merely costing money.",
    ),
    AppetiteSpec(
        RiskCategory.BUSINESS_CONTINUITY,
        RiskBand.HIGH,
        "Chief Executive Officer",
        "The highest appetite of any category, and deliberately so. FinFlow's recovery "
        "objectives are measured in hours, not the minutes an incumbent bank commits to. "
        "Buying that down further means multi-region spend the company has chosen not to "
        "make at this stage.",
    ),
    AppetiteSpec(
        RiskCategory.TECHNOLOGY,
        RiskBand.MEDIUM,
        "Chief Technology Officer",
        "Technical debt and platform fragility are accepted at medium level as the cost "
        "of shipping quickly, provided monitoring gives early warning.",
    ),
]


class RiskSpec(NamedTuple):
    risk_ref: str
    title: str
    description: str
    category: RiskCategory
    owner_role: str
    status: RiskStatus
    asset: str
    threat: str
    vulnerability: str
    inherent_likelihood: int
    inherent_impact: int
    residual_likelihood: int
    residual_impact: int
    residual_justification: str
    treatment_decision: TreatmentDecision
    treatment_summary: str
    date_identified: date
    last_reviewed: date
    next_review: date
    controls: tuple[tuple[str, Basis], ...]


RISKS: list[RiskSpec] = [
    RiskSpec(
        "RISK-001",
        "Customer account takeover via credential stuffing",
        "Attackers replay credentials leaked from unrelated breaches against the customer "
        "sign-in endpoint, gaining access to merchant dashboards and payout settings.",
        RiskCategory.CYBERSECURITY,
        "Chief Technology Officer",
        RiskStatus.MONITORING,
        "Customer-facing web application and merchant accounts",
        "Automated credential replay by financially motivated attackers using breach corpora.",
        "Password reuse by merchant users; sign-in endpoint reachable from any source address.",
        4, 4,
        2, 4,
        "AC-002 (MFA, tested effective) breaks the replay: a valid password alone no longer "
        "authenticates, dropping likelihood from 4 to 2. Impact stays at 4 because a "
        "successful takeover still exposes full merchant payout configuration — MFA changes "
        "who gets in, not what they reach once inside.",
        TreatmentDecision.MITIGATE,
        "MFA enforced for all merchant users; rate limiting and anomalous sign-in alerting "
        "in place via OP-002.",
        date(2025, 3, 11), date(2026, 6, 2), date(2026, 12, 2),
        (("AC-002", Basis.TESTED_EFFECTIVE), ("AC-001", Basis.TESTED_EFFECTIVE),
         ("OP-002", Basis.TESTED_EFFECTIVE)),
    ),
    RiskSpec(
        "RISK-002",
        "Unauthorised access to customer personal data in the production database",
        "An internal or compromised account reaches the production data store and reads "
        "personal data belonging to EU and Indian data subjects at scale.",
        RiskCategory.DATA_PRIVACY,
        "Data Protection Officer",
        RiskStatus.TREATMENT_IN_PROGRESS,
        "Production RDS cluster holding customer PII",
        "Compromised engineer credentials or abuse of standing database access.",
        "Broad read access historically granted to the platform team; elevation not yet "
        "fully time-bound.",
        3, 5,
        2, 5,
        f"{TODO} — name which control moved likelihood 3 to 2 (AC-003 is tested with "
        "exceptions, so say what the exceptions were), and state why impact remains 5 "
        "despite DP-001 encryption at rest.",
        TreatmentDecision.MITIGATE,
        "Time-bound elevation being rolled out; quarterly access review already operating.",
        date(2025, 1, 20), date(2026, 7, 14), date(2026, 10, 14),
        (("AC-003", Basis.TESTED_WITH_EXCEPTIONS), ("DP-001", Basis.TESTED_EFFECTIVE),
         ("OP-001", Basis.TESTED_EFFECTIVE), ("AC-004", Basis.TESTED_EFFECTIVE)),
    ),
    RiskSpec(
        "RISK-003",
        "Payment service provider outage halts transaction processing",
        "The third-party PSP suffers a sustained outage and FinFlow cannot process merchant "
        "transactions for the duration.",
        RiskCategory.THIRD_PARTY,
        "Chief Operating Officer",
        RiskStatus.MONITORING,
        "Payment processing pipeline and PSP integration",
        "Provider-side infrastructure failure or capacity exhaustion.",
        "Single PSP with no contracted failover; FinFlow holds no payment licence of its own.",
        3, 4,
        2, 4,
        "TP-002 (annual assurance review, tested effective) confirmed the provider operates "
        "a multi-region architecture with contractual availability commitments, lowering "
        "likelihood from 3 to 2. Impact stays at 4: FinFlow has no secondary PSP, so an "
        "outage of any length still stops processing entirely.",
        TreatmentDecision.ACCEPT,
        "Accepted at current scale. Secondary PSP integration is on the roadmap but not "
        "funded this year; see the risk acceptance register.",
        date(2025, 5, 6), date(2026, 6, 18), date(2026, 12, 18),
        (("TP-002", Basis.TESTED_EFFECTIVE), ("BC-001", Basis.DESIGN_ONLY),
         ("OP-006", Basis.TESTED_EFFECTIVE)),
    ),
    RiskSpec(
        "RISK-004",
        "Compromise of a privileged AWS account through incomplete MFA enforcement",
        "MFA is not enforced on every privileged path into the AWS production account. An "
        "attacker who obtains a privileged credential reaches production infrastructure and "
        "the customer data it holds.",
        RiskCategory.CYBERSECURITY,
        "Chief Technology Officer",
        RiskStatus.TREATMENT_IN_PROGRESS,
        "AWS production account (eu-west-1) and all customer data within it",
        "Credential theft through phishing or endpoint compromise, followed by privilege use.",
        "MFA enforcement on privileged roles is incomplete; some legacy access paths bypass "
        "the Okta sign-on policy.",
        4, 5,
        3, 5,
        "AC-002 is tested WITH EXCEPTIONS: MFA is enforced on 60% of privileged accounts, "
        "not all of them. Partial coverage earns a partial reduction — likelihood moves 4 "
        "to 3, not to the 2 that full enforcement would justify. OP-002 (tested effective) "
        "shortens detection time but does not prevent the initial access, so it does not "
        "move likelihood further. Impact remains 5 and cannot be reduced by an access "
        "control: a privileged compromise reaches the entire production estate regardless "
        "of how the attacker arrived.",
        TreatmentDecision.MITIGATE,
        "Remediation open to enforce MFA on the remaining 40% of privileged accounts and "
        "remove legacy bypass paths.",
        date(2025, 2, 4), date(2026, 7, 28), date(2026, 9, 28),
        (("AC-002", Basis.TESTED_WITH_EXCEPTIONS), ("AC-003", Basis.DESIGN_ONLY),
         ("OP-002", Basis.TESTED_EFFECTIVE), ("AC-004", Basis.TESTED_EFFECTIVE)),
    ),
    RiskSpec(
        "RISK-005",
        "Exploitation of an unpatched critical vulnerability in a public-facing service",
        "A known critical vulnerability in a dependency or base image remains unpatched "
        "beyond the remediation window and is exploited against an internet-facing service.",
        RiskCategory.TECHNOLOGY,
        "Chief Technology Officer",
        RiskStatus.MONITORING,
        "Public API and web application container images",
        "Opportunistic exploitation of a published CVE by automated scanning.",
        "Patch SLA is met inconsistently for medium-severity findings; some base images lag.",
        4, 4,
        2, 4,
        "OP-003 (image scanning, tested effective) blocks promotion of images carrying "
        "critical findings, and CM-004 (dependency alerting, tested effective) surfaces "
        "them within a day — together moving likelihood from 4 to 2. OP-004 was tested with "
        "exceptions on medium-severity SLAs, which is why likelihood does not go lower. "
        "Impact is unchanged at 4: a successful exploit on a public service reaches the same "
        "data whether it was patched late or not at all.",
        TreatmentDecision.MITIGATE,
        "Scanning gates in CI; medium-severity SLA adherence tracked as a KRI.",
        date(2025, 4, 22), date(2026, 6, 30), date(2026, 12, 30),
        (("OP-003", Basis.TESTED_EFFECTIVE), ("OP-004", Basis.TESTED_WITH_EXCEPTIONS),
         ("CM-004", Basis.TESTED_EFFECTIVE)),
    ),
    RiskSpec(
        "RISK-006",
        "Key person dependency in platform engineering",
        "Detailed knowledge of the payment ledger and its failure modes sits with two "
        "engineers. Their unavailability would stall incident response and delivery.",
        RiskCategory.OPERATIONAL,
        "Chief Operating Officer",
        RiskStatus.OPEN,
        "Payment ledger service and its operational knowledge",
        "Resignation, illness or extended unavailability of key engineers.",
        "Runbooks are incomplete; no formal cross-training programme.",
        3, 3,
        3, 3,
        "No reduction is claimed. GV-002 documents role accountability but does not spread "
        "operational knowledge, and it is assessed on design only. Until runbooks exist and "
        "cross-training has actually run, residual equals inherent — writing a lower number "
        "here would record an intention as an achievement.",
        TreatmentDecision.MITIGATE,
        "Runbook programme and cross-training scheduled; no credit taken until delivered.",
        date(2025, 9, 15), date(2026, 7, 1), date(2026, 10, 1),
        (("GV-002", Basis.DESIGN_ONLY),),
    ),
    RiskSpec(
        "RISK-007",
        "Extended AWS eu-west-1 regional outage",
        "A prolonged regional failure at the sole hosting region takes the product offline "
        "for longer than the committed recovery time objective.",
        RiskCategory.BUSINESS_CONTINUITY,
        "Chief Executive Officer",
        RiskStatus.MONITORING,
        "All production infrastructure in AWS eu-west-1",
        "Regional-scale provider failure affecting multiple availability zones.",
        "Single-region deployment; no warm standby in a second region.",
        2, 5,
        2, 4,
        f"{TODO} — this is the one risk where impact drops rather than likelihood. Explain "
        "why OP-005 cross-region backups reduce impact from 5 to 4, and why likelihood "
        "stays at 2 (nothing FinFlow does affects whether AWS loses a region).",
        TreatmentDecision.ACCEPT,
        "Single-region operation accepted at current scale; cross-region backup copies in "
        "place. Multi-region active-active is explicitly out of budget.",
        date(2025, 6, 30), date(2026, 6, 12), date(2026, 12, 12),
        (("OP-006", Basis.TESTED_EFFECTIVE), ("OP-005", Basis.TESTED_EFFECTIVE),
         ("BC-001", Basis.DESIGN_ONLY)),
    ),
    RiskSpec(
        "RISK-008",
        "Unlawful transfer of EU personal data to India-based support staff",
        "Support personnel located in India access personal data of EU data subjects "
        "without an adequate transfer mechanism in place.",
        RiskCategory.DATA_PRIVACY,
        "Data Protection Officer",
        RiskStatus.MONITORING,
        "Customer support tooling and the personal data reachable through it",
        "Routine support access constituting an international transfer under Chapter V GDPR.",
        "Support team is distributed across jurisdictions; transfer safeguards were "
        "originally undocumented.",
        3, 4,
        2, 4,
        "Re-scored after TEST-008. TP-003 (tested effective) put Standard Contractual "
        "Clauses and Article 28 terms in place, which moves likelihood from 3 to 2. The "
        "further reduction to 1 previously claimed here rested on DP-005 masking the "
        "records support staff actually see — and TEST-008 found the support tooling "
        "replica holding roughly 12,000 unmasked customer records. DP-005 is now tested "
        "INEFFECTIVE and earns no credit, so that reduction is withdrawn. Impact stays at 4: "
        "the regulatory exposure of an unlawful transfer is unchanged by the paperwork "
        "around it.",
        TreatmentDecision.MITIGATE,
        "SCCs executed and transfer impact assessment completed. Masked support views are "
        "deployed but do not cover the support replica; tracked as REM-017.",
        date(2025, 7, 8), date(2026, 8, 5), date(2026, 10, 20),
        (("DP-003", Basis.DESIGN_ONLY), ("TP-003", Basis.TESTED_EFFECTIVE),
         ("AC-004", Basis.TESTED_EFFECTIVE), ("DP-005", Basis.TESTED_INEFFECTIVE)),
    ),
    RiskSpec(
        "RISK-009",
        "ISO 27001 certification timeline missed, blocking enterprise deals",
        "The ISMS does not reach certification readiness in time, and enterprise prospects "
        "who require certification defer or withdraw.",
        RiskCategory.COMPLIANCE,
        "Head of Legal & Compliance",
        RiskStatus.TREATMENT_IN_PROGRESS,
        "The ISMS and the enterprise sales pipeline dependent on it",
        "Slippage in control implementation, internal audit or management review.",
        "Several Annex A controls remain partially implemented; internal audit programme is "
        "new and unproven.",
        3, 3,
        2, 3,
        "GV-001 (policy set approved, tested effective) removed the largest documentation "
        "gap and moved likelihood from 3 to 2. GV-003 is design-only, so the risk assessment "
        "cadence itself is not yet evidence. Impact stays at 3: the pipeline consequence of "
        "missing the date is the same regardless of how close the ISMS got.",
        TreatmentDecision.MITIGATE,
        "Certification readiness tracked against the SoA implementation percentage KRI.",
        date(2025, 11, 3), date(2026, 7, 30), date(2026, 9, 30),
        (("GV-001", Basis.TESTED_EFFECTIVE), ("GV-003", Basis.DESIGN_ONLY)),
    ),
    RiskSpec(
        "RISK-010",
        "Breach at a critical SaaS vendor exposes FinFlow data",
        "A vendor holding FinFlow or customer data suffers a breach, exposing data FinFlow "
        "remains accountable for as controller.",
        RiskCategory.THIRD_PARTY,
        "Chief Operating Officer",
        RiskStatus.OPEN,
        "Data held by critical SaaS vendors including the identity and support platforms",
        "Compromise of the vendor's own infrastructure or supply chain.",
        "FinFlow has no ability to test vendor controls directly and relies on assurance "
        "reports produced for the vendor's own purposes.",
        3, 4,
        3, 4,
        "No reduction is claimed, and this is deliberate. TP-001, TP-002 and TP-003 are all "
        "tested effective, but what they deliver is selection quality, contractual recourse "
        "and notification — not prevention. Reading a vendor's SOC 2 report does not make "
        "that vendor harder to breach. Scoring a reduction here would credit FinFlow for "
        "assurance activity that has no causal effect on the threat.",
        TreatmentDecision.TRANSFER,
        "Contractual liability and breach notification obligations placed on vendors; cyber "
        "insurance carries residual financial exposure.",
        date(2025, 8, 19), date(2026, 6, 25), date(2026, 12, 25),
        (("TP-001", Basis.TESTED_EFFECTIVE), ("TP-002", Basis.TESTED_EFFECTIVE),
         ("TP-003", Basis.TESTED_EFFECTIVE)),
    ),
    RiskSpec(
        "RISK-011",
        "Malicious or vulnerable third-party dependency introduced into the codebase",
        "A compromised or abandoned package enters the build and reaches production, "
        "executing attacker-controlled code inside the trust boundary.",
        RiskCategory.CYBERSECURITY,
        "Chief Technology Officer",
        RiskStatus.MONITORING,
        "Application source code and the CI/CD build pipeline",
        "Supply chain compromise of an upstream package or its maintainer account.",
        "Large transitive dependency tree; no pinned internal package mirror.",
        3, 4,
        2, 4,
        f"{TODO} — three controls here are all tested effective (CM-003, CM-004, OP-003). "
        "Say which of them actually reduces likelihood versus which only shortens detection "
        "time, and be precise about why impact is unchanged.",
        TreatmentDecision.MITIGATE,
        "SAST and dependency alerting in CI; critical findings block merge.",
        date(2025, 10, 27), date(2026, 7, 6), date(2026, 10, 6),
        (("CM-004", Basis.TESTED_EFFECTIVE), ("CM-003", Basis.TESTED_EFFECTIVE),
         ("OP-003", Basis.TESTED_EFFECTIVE)),
    ),
    RiskSpec(
        "RISK-012",
        "Misconfigured cloud resource exposes customer data publicly",
        "An S3 bucket, security group or database parameter is misconfigured such that "
        "customer data becomes reachable from the internet.",
        RiskCategory.OPERATIONAL,
        "Chief Operating Officer",
        RiskStatus.MONITORING,
        "AWS storage and network configuration in the production account",
        "Human error during infrastructure change, or drift from an approved baseline.",
        "Historically some resources were created through the console rather than code.",
        4, 4,
        2, 4,
        "CM-005 (infrastructure as code, tested effective) removed the console-change path "
        "that caused most historical misconfiguration, and OP-002 (tested effective) alerts "
        "on public-exposure findings within minutes — moving likelihood from 4 to 2. Impact "
        "stays at 4 because a misconfiguration that does occur exposes the same dataset; "
        "detection speed limits duration, not scope.",
        TreatmentDecision.MITIGATE,
        "All infrastructure changes flow through Terraform with review; drift detection "
        "alerting enabled.",
        date(2025, 3, 30), date(2026, 6, 9), date(2026, 12, 9),
        (("CM-005", Basis.TESTED_EFFECTIVE), ("OP-002", Basis.TESTED_EFFECTIVE),
         ("CM-002", Basis.TESTED_EFFECTIVE)),
    ),
    RiskSpec(
        "RISK-013",
        "Fraudulent transactions processed through the platform",
        "Fraudulent card transactions are processed and later charged back, creating direct "
        "financial loss and scheme scrutiny.",
        RiskCategory.FINANCIAL,
        "Chief Financial Officer",
        RiskStatus.MONITORING,
        "Transaction processing flow and the merchant settlement account",
        "Organised card fraud targeting merchants onboarded to the platform.",
        "FinFlow does not operate its own fraud scoring engine.",
        3, 4,
        2, 2,
        "This is a transfer, and the score reflects it. Fraud screening, chargeback handling "
        "and scheme liability all sit with the PSP under contract, which is why impact drops "
        "from 4 to 2 — FinFlow's retained exposure is the excess and the operational cost of "
        "dispute handling, not the transaction value. Likelihood moves 3 to 2 because "
        "TP-001 vendor selection weighted fraud capability. The residual is what FinFlow "
        "still carries, not what the ecosystem carries.",
        TreatmentDecision.TRANSFER,
        "Fraud liability contractually held by the PSP; FinFlow retains dispute-handling "
        "cost and the contractual excess.",
        date(2025, 5, 14), date(2026, 7, 2), date(2026, 10, 2),
        (("TP-002", Basis.TESTED_EFFECTIVE), ("TP-001", Basis.TESTED_EFFECTIVE)),
    ),
    RiskSpec(
        "RISK-014",
        "Breach of a customer availability SLA triggering contractual penalties",
        "Cumulative downtime exceeds the uptime commitment in enterprise contracts, "
        "triggering service credits and giving customers termination rights.",
        RiskCategory.LEGAL,
        "Head of Legal & Compliance",
        RiskStatus.MONITORING,
        "Enterprise customer contracts carrying uptime commitments",
        "Accumulated outages exceeding the contractual availability threshold.",
        "SLA commitments were agreed in sales negotiations without an engineering review of "
        "achievable uptime.",
        3, 3,
        2, 3,
        f"{TODO} — OP-006 multi-AZ is tested effective and OP-002 monitoring is tested "
        "effective. Decide which one justifies the likelihood move from 3 to 2, and note "
        "why service-credit exposure keeps impact at 3.",
        TreatmentDecision.MITIGATE,
        "Multi-AZ deployment and uptime monitoring; SLA terms under review at renewal.",
        date(2025, 12, 9), date(2026, 6, 16), date(2026, 12, 16),
        (("OP-006", Basis.TESTED_EFFECTIVE), ("OP-002", Basis.TESTED_EFFECTIVE)),
    ),
    RiskSpec(
        "RISK-015",
        "Employee endpoint compromised through a phishing campaign",
        "A staff member is phished, giving an attacker a foothold on a company laptop and "
        "access to whatever that user can reach.",
        RiskCategory.CYBERSECURITY,
        "Chief Technology Officer",
        RiskStatus.MONITORING,
        "Company-issued macOS laptops and the accounts held on them",
        "Targeted or commodity phishing against a fully remote workforce.",
        "No physical office perimeter; all staff work from personal networks.",
        4, 3,
        2, 3,
        "AC-002 (phishing-resistant MFA, tested effective) means a harvested password alone "
        "does not yield a session, and OP-007 (EDR, tested effective) detects and isolates "
        "post-compromise activity on the endpoint. Likelihood moves 4 to 2. Impact holds at "
        "3: a compromised endpoint still reaches that user's own data and mail, and no "
        "control in this set changes what a single user can see.",
        TreatmentDecision.MITIGATE,
        "Phishing-resistant MFA, managed endpoints with EDR, and annual awareness training.",
        date(2025, 2, 17), date(2026, 7, 10), date(2026, 10, 10),
        (("HR-002", Basis.TESTED_EFFECTIVE), ("OP-007", Basis.TESTED_EFFECTIVE),
         ("AC-002", Basis.TESTED_EFFECTIVE)),
    ),
    RiskSpec(
        "RISK-016",
        "Failure to fulfil data subject access requests within the statutory period",
        "A data subject request is not answered within one month, creating a reportable "
        "compliance failure and a supervisory authority complaint.",
        RiskCategory.DATA_PRIVACY,
        "Data Protection Officer",
        RiskStatus.MONITORING,
        "Personal data held across production systems and the DSAR handling process",
        "Volume or complexity of requests exceeding the manual handling capacity.",
        "Personal data is spread across several systems without a single retrieval path.",
        3, 3,
        1, 3,
        "DP-004 (retention schedule with automated deletion, tested effective) shrank the "
        "search surface by removing data past its retention period, and GV-001 (tested "
        "effective) established the documented DSAR procedure with named responsibility. "
        "Likelihood moves 3 to 1. Impact stays at 3 because a missed deadline is a "
        "reportable failure of the same severity however close FinFlow came to meeting it.",
        TreatmentDecision.MITIGATE,
        "Documented DSAR procedure with a named owner and tracked response clock.",
        date(2025, 6, 5), date(2026, 7, 22), date(2026, 10, 22),
        (("DP-003", Basis.DESIGN_ONLY), ("DP-004", Basis.TESTED_EFFECTIVE),
         ("GV-001", Basis.TESTED_EFFECTIVE)),
    ),
    RiskSpec(
        "RISK-017",
        "Data loss following a backup failure or an untested restore path",
        "Backups are present but unrestorable, or silently incomplete, and are discovered to "
        "be so only when a recovery is attempted.",
        RiskCategory.TECHNOLOGY,
        "Chief Technology Officer",
        RiskStatus.MONITORING,
        "Production database backups and point-in-time recovery capability",
        "Silent backup corruption, misconfigured retention, or an unexercised restore path.",
        "Restore testing was previously ad hoc rather than scheduled.",
        2, 5,
        1, 5,
        "OP-005 (tested effective) now covers scheduled restore exercises, not just backup "
        "completion — which is the distinction that matters, since a backup nobody has "
        "restored is an untested control. Likelihood moves 2 to 1. Impact remains 5 and "
        "cannot move: if a restore does fail, the ledger data is gone, and no control in "
        "this set reduces the consequence of that.",
        TreatmentDecision.MITIGATE,
        "Automated backups with cross-region copies and scheduled restore verification.",
        date(2025, 4, 8), date(2026, 6, 20), date(2026, 12, 20),
        (("OP-005", Basis.TESTED_EFFECTIVE), ("OP-006", Basis.TESTED_EFFECTIVE)),
    ),
    RiskSpec(
        "RISK-018",
        "Insider misuse of production data access by an engineer",
        "An engineer with legitimate production access views or extracts customer data for "
        "purposes unrelated to their role.",
        RiskCategory.OPERATIONAL,
        "Chief Operating Officer",
        RiskStatus.TREATMENT_IN_PROGRESS,
        "Production customer data and the engineering access paths to it",
        "Deliberate misuse by an authorised individual, or curiosity-driven browsing.",
        "Production access is broader than strictly necessary; monitoring is detective only.",
        3, 4,
        3, 4,
        f"{TODO} — the reduction previously claimed here has been withdrawn, and the "
        "paragraph needs writing to match. The position taken: no reduction is claimed. "
        "Four points to make in your own words. (1) The threat statement covers two modes "
        "— deliberate misuse and curiosity-driven browsing. (2) DP-005 masking was the only "
        "control addressing the second mode, and TEST-008 rated it INEFFECTIVE. (3) What "
        "remains either detects after the fact (OP-001) or manages access the engineer "
        "legitimately holds (AC-003, AC-004); deterrence is not credited, on the same "
        "reasoning that refuses credit to untested controls — it cannot be evidenced. "
        "(4) State what would justify a reduction later: REM-017 closing and masking being "
        "re-tested.",
        TreatmentDecision.MITIGATE,
        "Access logging and quarterly review operate, but the only preventive control over "
        "what an engineer can see is broken. Residual returns to inherent and the risk now "
        "sits above the Operational ceiling. Closing REM-017 and re-testing DP-005 is the "
        "route back; until then this needs treatment or a signed, expiring acceptance.",
        date(2025, 9, 1), date(2026, 8, 16), date(2026, 10, 18),
        (("AC-003", Basis.TESTED_WITH_EXCEPTIONS), ("OP-001", Basis.TESTED_EFFECTIVE),
         ("AC-004", Basis.TESTED_EFFECTIVE), ("DP-005", Basis.TESTED_INEFFECTIVE),
         ("HR-001", Basis.TESTED_EFFECTIVE)),
    ),
    RiskSpec(
        "RISK-019",
        "Undocumented processing activity discovered during a regulatory review",
        "A processing activity is found to be absent from the Record of Processing "
        "Activities, evidencing a failure of Article 30 compliance.",
        RiskCategory.COMPLIANCE,
        "Data Protection Officer",
        RiskStatus.OPEN,
        "The Record of Processing Activities and the processing it should describe",
        "Regulatory inspection or a data subject complaint triggering scrutiny.",
        "RoPA was compiled once and has no change trigger when new processing is introduced.",
        3, 3,
        3, 3,
        "No reduction is claimed and none is permitted. Both linked controls are untested: "
        "DP-003 classification has never been assessed, and GV-003's quarterly review "
        "cadence has not yet run a full cycle. An untested control is an intention, and the "
        "methodology does not allow intentions to move a residual score. This risk sits at "
        "its inherent level until the RoPA review actually operates and is tested.",
        TreatmentDecision.MITIGATE,
        "RoPA rebuild scheduled with a change trigger tied to the product launch process.",
        date(2026, 1, 12), date(2026, 7, 25), date(2026, 9, 25),
        (("DP-003", Basis.NOT_TESTED), ("GV-003", Basis.NOT_TESTED)),
    ),
    RiskSpec(
        "RISK-020",
        "Loss of the identity provider blocks all authentication",
        "An Okta outage or tenant lockout prevents every employee from authenticating to "
        "any system, including the tools needed to respond to the incident.",
        RiskCategory.BUSINESS_CONTINUITY,
        "Chief Executive Officer",
        RiskStatus.MONITORING,
        "Okta tenant and every application federated to it",
        "Provider outage, tenant misconfiguration, or administrative lockout.",
        "Single identity provider with limited break-glass access paths.",
        2, 5,
        2, 4,
        "IR-001 (tested effective) establishes documented break-glass credentials held "
        "offline and an out-of-band communication path, which is why impact falls from 5 to "
        "4 — the company can still coordinate and reach AWS directly during an outage. "
        "Likelihood stays at 2: nothing FinFlow operates affects whether Okta goes down. "
        "BC-001 is design-only and the identity-loss scenario has not yet been exercised, so "
        "no further credit is taken.",
        TreatmentDecision.MITIGATE,
        "Break-glass credentials held offline; identity-loss scenario to be added to the "
        "next continuity exercise.",
        date(2025, 11, 20), date(2026, 6, 5), date(2026, 12, 5),
        (("BC-001", Basis.DESIGN_ONLY), ("IR-001", Basis.TESTED_EFFECTIVE)),
    ),
]
