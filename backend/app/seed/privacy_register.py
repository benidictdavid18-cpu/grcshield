"""GDPR records: Article 30 RoPA and Article 35 DPIAs.

Six processing activities and two DPIAs. DPIA-001 is the one worth reading: its
mitigation rested on DP-005 masking support data, and TEST-008 found that control
ineffective — so the assessment's residual rating no longer holds and its review is
overdue. A DPIA that is never revisited is a snapshot of an argument nobody checked.
"""

from datetime import date
from typing import NamedTuple


class RopaSpec(NamedTuple):
    ref: str
    processing_activity: str
    purpose: str
    lawful_basis: str
    legitimate_interests_assessment: str | None
    data_subject_categories: str
    personal_data_categories: str
    special_category_data: bool
    recipients: str
    transfers_outside_eea: bool
    transfer_detail: str | None
    transfer_safeguard: str
    retention_period: str
    security_measures_summary: str
    controller_role: str
    owner_role: str
    last_reviewed: date
    assets: tuple[str, ...]
    risks: tuple[str, ...]
    controls: tuple[str, ...]


ROPA_ENTRIES: list[RopaSpec] = [
    RopaSpec(
        "ROPA-001", "Merchant onboarding and identity verification",
        "Verify the identity and beneficial ownership of businesses applying to process "
        "payments, and screen them against sanctions and politically exposed persons "
        "lists, before granting access to the platform.",
        "LEGAL_OBLIGATION", None,
        "Directors, beneficial owners and authorised signatories of applicant merchant "
        "businesses.",
        "Name, date of birth, residential address, nationality, government identity "
        "document images, company role, sanctions and PEP screening results.",
        False,
        "Identity verification provider (processor); the payment service provider; "
        "regulated financial crime authorities on lawful request.",
        False, None, "NOT_APPLICABLE",
        "Five years from the end of the business relationship, as required by anti-money "
        "laundering recordkeeping obligations. Deleted by scheduled job thereafter.",
        "Encryption at rest with customer-managed keys, role-restricted access limited to "
        "the onboarding team, and full access logging.",
        "FinFlow Technologies Ltd (controller)", "Head of Legal & Compliance",
        date(2026, 7, 20),
        ("AST-001", "AST-003"), ("RISK-002",), ("DP-001", "AC-003", "OP-001", "DP-004"),
    ),
    RopaSpec(
        "ROPA-002", "Payment transaction processing",
        "Accept, route and reconcile card payment transactions initiated by merchants' "
        "customers, and make settlement payments to merchants.",
        "CONTRACT", None,
        "Customers of FinFlow's merchants (data subjects of the underlying transactions), "
        "and merchant staff initiating refunds.",
        "Transaction amount and timestamp, tokenised card reference, merchant identifier, "
        "partial card number (last four digits), billing country. Full card numbers are "
        "never held by FinFlow — they are captured directly by the payment service "
        "provider.",
        False,
        "The payment service provider (processor); card schemes and acquiring banks "
        "through the provider; merchants receiving settlement reporting.",
        False, None, "NOT_APPLICABLE",
        "Seven years from transaction date, to satisfy financial recordkeeping and "
        "chargeback dispute windows.",
        "TLS 1.2+ in transit, encryption at rest, network segregation between environments, "
        "and centralised logging of all access.",
        "FinFlow Technologies Ltd (controller)", "Chief Operating Officer",
        date(2026, 7, 20),
        ("AST-001", "AST-002", "AST-010"), ("RISK-002", "RISK-013"),
        ("DP-001", "DP-002", "CM-002", "OP-001"),
    ),
    RopaSpec(
        "ROPA-003", "Customer support ticket handling",
        "Investigate and resolve merchant queries about transactions, settlements and "
        "account configuration, including access to transaction records where needed to "
        "answer the question.",
        "LEGITIMATE_INTERESTS",
        "FinFlow has a legitimate interest in resolving merchant queries accurately and "
        "quickly, and merchants expect support to be able to see the transactions they "
        "are asking about, so the processing is within their reasonable expectations. The "
        "balancing test turns on minimisation: support staff should see masked records by "
        "default and raw data only where the query cannot be answered otherwise. Note that "
        "TEST-008 found the support replica holding unmasked records, which means the "
        "minimisation this assessment relies on is not currently operating. The balance is "
        "therefore weaker in practice than as designed, and is being corrected under "
        "REM-017.",
        "Merchant staff raising tickets, and the customers of merchants whose transactions "
        "are discussed in those tickets.",
        "Name, business email address, ticket correspondence, transaction identifiers and "
        "partial card numbers referenced in the query.",
        False,
        "Support tooling vendor (processor); FinFlow support staff located in the EU and "
        "in India.",
        True,
        "Support staff located in India access the tooling to resolve tickets during "
        "Asia-Pacific hours. The transfer is to FinFlow's own personnel rather than a "
        "separate legal entity, and is covered by Standard Contractual Clauses with a "
        "completed transfer impact assessment.",
        "STANDARD_CONTRACTUAL_CLAUSES",
        "Twenty-four months from ticket closure, then deleted by scheduled job.",
        "Role-restricted access, masked views for routine queries (currently incomplete — "
        "see REM-017), access logging, and Standard Contractual Clauses covering the "
        "transfer.",
        "FinFlow Technologies Ltd (controller)", "Data Protection Officer",
        date(2026, 8, 5),
        ("AST-008", "AST-001"), ("RISK-008", "RISK-018"),
        ("DP-005", "AC-004", "TP-003", "OP-001"),
    ),
    RopaSpec(
        "ROPA-004", "Product analytics and usage telemetry",
        "Understand how merchants use the platform in order to prioritise product work, "
        "identify friction in onboarding, and forecast capacity.",
        "LEGITIMATE_INTERESTS",
        "FinFlow has a legitimate interest in improving a product its merchants depend on, "
        "and aggregate usage analysis is a normal expectation of a SaaS relationship. The "
        "balance holds because the analysis is at account level rather than about "
        "individuals, no automated decision with legal or similarly significant effect is "
        "taken, and merchants can object. The weakness in the balance is that the "
        "warehouse currently receives more identifying data than the purpose requires "
        "(TEST-008), which is a minimisation failure rather than a purpose failure.",
        "Merchant staff using the web application.",
        "User identifier, account identifier, page and feature interaction events, session "
        "timestamps, coarse geographic region derived from IP address.",
        False,
        "No external recipients. Data remains within FinFlow's AWS estate.",
        False, None, "NOT_APPLICABLE",
        "Event-level data retained for thirteen months; aggregate metrics retained "
        "indefinitely in non-identifying form.",
        "Access restricted to the product and engineering teams, encryption at rest, and "
        "intended pseudonymisation before loading (currently incomplete — see REM-017).",
        "FinFlow Technologies Ltd (controller)", "Data Protection Officer",
        date(2026, 8, 5),
        ("AST-007", "AST-003"), ("RISK-002",), ("DP-001", "DP-005", "AC-003"),
    ),
    RopaSpec(
        "ROPA-005", "Employee and contractor records",
        "Administer employment, run payroll, verify right to work, complete pre-employment "
        "screening, and manage system access through the joiner-mover-leaver process.",
        "CONTRACT", None,
        "Employees, contractors and job applicants.",
        "Name, contact details, date of birth, national insurance or equivalent identifier, "
        "bank details for payroll, right-to-work documentation, employment history, "
        "screening outcomes, emergency contact.",
        False,
        "Payroll provider (processor); background screening provider (processor); tax "
        "authorities as required by law; pension provider.",
        False, None, "NOT_APPLICABLE",
        "Six years from the end of employment for core records, in line with statutory "
        "limitation periods. Unsuccessful applicant records deleted after twelve months.",
        "Access restricted to the People team and the individual, vendor assessed under "
        "TP-001, and provisioning driven by the identity lifecycle in AC-005.",
        "FinFlow Technologies Ltd (controller)", "Head of People",
        date(2026, 6, 30),
        ("AST-011",), ("RISK-018",), ("HR-001", "AC-005", "TP-001", "HR-003"),
    ),
    RopaSpec(
        "ROPA-006", "Marketing communications to prospective merchants",
        "Send product announcements, onboarding guidance and event invitations to "
        "individuals who have asked to hear from FinFlow.",
        "CONSENT", None,
        "Prospective merchant contacts who have subscribed, and existing merchant contacts "
        "who have opted in.",
        "Name, business email address, company name, job title, subscription preferences "
        "and email engagement events.",
        False,
        "Email delivery platform (processor).",
        False, None, "NOT_APPLICABLE",
        "Until consent is withdrawn, or after twenty-four months of no engagement, "
        "whichever comes first. Withdrawal is honoured within 72 hours.",
        "Vendor assessed under TP-001, suppression list maintained for withdrawn consent, "
        "and access limited to the marketing function.",
        "FinFlow Technologies Ltd (controller)", "Data Protection Officer",
        date(2026, 6, 30),
        (), (), ("TP-001", "TP-003"),
    ),
]


class DpiaSpec(NamedTuple):
    ref: str
    title: str
    ropa_ref: str | None
    trigger_reason: str
    processing_description: str
    necessity_and_proportionality: str
    risks_to_data_subjects: str
    mitigating_measures: str
    residual_risk: str
    residual_risk_note: str
    dpo_consulted: bool
    dpo_advice: str | None
    supervisory_authority_consulted: bool
    data_subjects_consulted: bool
    outcome: str
    assessed_by: str
    assessment_date: date
    review_date: date | None
    assets: tuple[str, ...]
    risks: tuple[str, ...]


DPIAS: list[DpiaSpec] = [
    DpiaSpec(
        "DPIA-001",
        "Customer support access to transaction data from outside the EEA",
        "ROPA-003",
        "Article 35(1): the processing involves routine access to financial transaction "
        "data by staff outside the EEA, at a scale covering the whole merchant base. "
        "Financial data and international transfer together placed this above the "
        "threshold for a full assessment.",
        "Support staff in the EU and in India access the ticketing platform, which "
        "surfaces merchant contact details and the transaction records referenced in a "
        "ticket. Access is continuous during working hours rather than incident-driven, "
        "and covers every merchant rather than a defined subset.",
        "Support cannot resolve transaction queries without seeing the transaction, so "
        "some access is necessary. Proportionality turns entirely on minimisation: the "
        "assessment concluded that masked views satisfy the large majority of queries and "
        "that raw access should be exceptional and logged. Follow-the-sun coverage was "
        "judged necessary because merchants operate across time zones and a 12-hour "
        "support gap would itself harm them.",
        "Excessive exposure of transaction detail to a wider group of staff than the "
        "purpose requires; unlawful transfer if the Chapter V mechanism fails or is found "
        "inadequate; loss of confidentiality through a compromised support account, which "
        "would expose data across the whole merchant base rather than a single account.",
        "Standard Contractual Clauses executed with a completed transfer impact assessment "
        "(TP-003). Masked views for routine queries so that raw transaction data is not "
        "the default (DP-005). All support access logged and retained for twelve months "
        "(OP-001). Quarterly review of support entitlements (AC-004). Phishing-resistant "
        "MFA on all support accounts (AC-002).",
        "HIGH",
        "Originally assessed as MEDIUM with an outcome of 'proceed with measures', on the "
        "basis that DP-005 masking would keep raw transaction data out of routine support "
        "workflows. TEST-008 found the support replica holding approximately 12,000 "
        "unmasked customer records, which means the measure this assessment depended on "
        "was not operating. The residual rating was raised to HIGH on 5 August 2026. "
        "Because Article 36(1) requires prior consultation where a DPIA indicates high "
        "residual risk, the outcome was changed with it — FinFlow cannot decide alone to "
        "continue processing at this residual level. Consultation with the supervisory "
        "authority is being prepared; the assessment returns to 'proceed with measures' "
        "only once REM-017 closes and masking is re-tested.",
        True,
        "The Data Protection Officer advised that the transfer is defensible only while "
        "minimisation actually operates, and that the masking control should be treated as "
        "a condition of the transfer rather than an enhancement to it. Following TEST-008 "
        "the DPO has recorded that the condition is not currently met, and that the "
        "residual rating change carries an Article 36 consequence rather than being a "
        "presentational adjustment.",
        False, False,
        "CONSULT_SUPERVISORY_AUTHORITY",
        "Data Protection Officer", date(2026, 2, 18), date(2026, 8, 1),
        ("AST-008", "AST-001"), ("RISK-008", "RISK-002"),
    ),
    DpiaSpec(
        "DPIA-002",
        "Product analytics profiling of merchant platform usage",
        "ROPA-004",
        "Article 35(3)(a): systematic and extensive evaluation of personal aspects based "
        "on automated processing. The assessment was performed because the analytics "
        "programme was scoped to include per-user behavioural profiling before that scope "
        "was reduced.",
        "Usage events are collected from the merchant web application and loaded into an "
        "analytics warehouse for product and capacity analysis. Analysis is performed at "
        "account level; the per-user profiling originally proposed was removed during this "
        "assessment.",
        "Aggregate usage analysis is necessary to prioritise product work on a platform "
        "merchants depend on, and is within the reasonable expectations of a business "
        "customer. The per-user behavioural profiling originally proposed was judged "
        "disproportionate: it would have supported no decision that account-level analysis "
        "could not, while creating a profile of individual employees' working patterns "
        "that no merchant had agreed to. It was removed rather than mitigated.",
        "Creation of profiles of individual merchant staff working patterns; function "
        "creep, where analytics data collected for product improvement is later used for "
        "commercial targeting or account management decisions; over-collection of "
        "identifying data into a store with a wider access group than production.",
        "Per-user profiling removed from scope. Analysis restricted to account-level "
        "aggregates. Purpose limitation stated in the processing record and enforced by "
        "restricting warehouse access to the product and engineering teams (AC-003). "
        "Thirteen-month retention on event-level data with scheduled deletion (DP-004). "
        "Pseudonymisation before load specified as a requirement (DP-005).",
        "MEDIUM",
        "Medium rather than low because the pseudonymisation requirement is specified but "
        "not operating — TEST-008 found identifying records in the warehouse. The residual "
        "does not reach HIGH because the analysis genuinely operates at account level and "
        "no decision with legal or similarly significant effect is taken about any "
        "individual, so the harm from the minimisation failure is exposure rather than "
        "consequential decision-making.",
        True,
        "The Data Protection Officer supported removing per-user profiling rather than "
        "seeking a basis for it, on the grounds that a purpose which cannot be explained "
        "to the data subject in a sentence is usually one that should not proceed.",
        False, False,
        "PROCEED_WITH_MEASURES",
        "Data Protection Officer", date(2026, 4, 9), date(2027, 4, 9),
        ("AST-007", "AST-003"), ("RISK-002",),
    ),
]
