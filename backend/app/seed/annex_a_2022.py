"""ISO/IEC 27001:2022 Annex A control set.

93 controls across four themes:
    A.5 Organizational   37
    A.6 People            8
    A.7 Physical         14
    A.8 Technological    34

Control identifiers and titles are the official Annex A references. Nothing here is
invented; if a control is not in this list it is not in Annex A.

Scope decisions (``in_scope`` / ``scope_note``) are PROVISIONAL. They record the
initial scoping pass so that SOC 2 mappings are only generated for controls FinFlow
actually operates. The authoritative applicability record is the Statement of
Applicability (Clause 6.1.3 d), built in Phase 3, which carries the formal
inclusion/exclusion justifications.
"""

from typing import NamedTuple

THEME_ORGANIZATIONAL = "A.5"
THEME_PEOPLE = "A.6"
THEME_PHYSICAL = "A.7"
THEME_TECHNOLOGICAL = "A.8"

THEME_TITLES = {
    THEME_ORGANIZATIONAL: "Organizational controls",
    THEME_PEOPLE: "People controls",
    THEME_PHYSICAL: "Physical controls",
    THEME_TECHNOLOGICAL: "Technological controls",
}


class AnnexAControl(NamedTuple):
    ref: str
    title: str
    theme: str


ANNEX_A_CONTROLS: list[AnnexAControl] = [
    # --- A.5 Organizational controls (37) ---------------------------------
    AnnexAControl("A.5.1", "Policies for information security", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.2", "Information security roles and responsibilities", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.3", "Segregation of duties", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.4", "Management responsibilities", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.5", "Contact with authorities", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.6", "Contact with special interest groups", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.7", "Threat intelligence", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.8", "Information security in project management", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.9", "Inventory of information and other associated assets", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.10", "Acceptable use of information and other associated assets", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.11", "Return of assets", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.12", "Classification of information", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.13", "Labelling of information", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.14", "Information transfer", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.15", "Access control", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.16", "Identity management", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.17", "Authentication information", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.18", "Access rights", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.19", "Information security in supplier relationships", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.20", "Addressing information security within supplier agreements", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.21", "Managing information security in the ICT supply chain", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.22", "Monitoring, review and change management of supplier services", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.23", "Information security for use of cloud services", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.24", "Information security incident management planning and preparation", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.25", "Assessment and decision on information security events", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.26", "Response to information security incidents", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.27", "Learning from information security incidents", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.28", "Collection of evidence", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.29", "Information security during disruption", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.30", "ICT readiness for business continuity", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.31", "Legal, statutory, regulatory and contractual requirements", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.32", "Intellectual property rights", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.33", "Protection of records", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.34", "Privacy and protection of PII", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.35", "Independent review of information security", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.36", "Compliance with policies, rules and standards for information security", THEME_ORGANIZATIONAL),
    AnnexAControl("A.5.37", "Documented operating procedures", THEME_ORGANIZATIONAL),
    # --- A.6 People controls (8) ------------------------------------------
    AnnexAControl("A.6.1", "Screening", THEME_PEOPLE),
    AnnexAControl("A.6.2", "Terms and conditions of employment", THEME_PEOPLE),
    AnnexAControl("A.6.3", "Information security awareness, education and training", THEME_PEOPLE),
    AnnexAControl("A.6.4", "Disciplinary process", THEME_PEOPLE),
    AnnexAControl("A.6.5", "Responsibilities after termination or change of employment", THEME_PEOPLE),
    AnnexAControl("A.6.6", "Confidentiality or non-disclosure agreements", THEME_PEOPLE),
    AnnexAControl("A.6.7", "Remote working", THEME_PEOPLE),
    AnnexAControl("A.6.8", "Information security event reporting", THEME_PEOPLE),
    # --- A.7 Physical controls (14) ---------------------------------------
    AnnexAControl("A.7.1", "Physical security perimeters", THEME_PHYSICAL),
    AnnexAControl("A.7.2", "Physical entry", THEME_PHYSICAL),
    AnnexAControl("A.7.3", "Securing offices, rooms and facilities", THEME_PHYSICAL),
    AnnexAControl("A.7.4", "Physical security monitoring", THEME_PHYSICAL),
    AnnexAControl("A.7.5", "Protecting against physical and environmental threats", THEME_PHYSICAL),
    AnnexAControl("A.7.6", "Working in secure areas", THEME_PHYSICAL),
    AnnexAControl("A.7.7", "Clear desk and clear screen", THEME_PHYSICAL),
    AnnexAControl("A.7.8", "Equipment siting and protection", THEME_PHYSICAL),
    AnnexAControl("A.7.9", "Security of assets off-premises", THEME_PHYSICAL),
    AnnexAControl("A.7.10", "Storage media", THEME_PHYSICAL),
    AnnexAControl("A.7.11", "Supporting utilities", THEME_PHYSICAL),
    AnnexAControl("A.7.12", "Cabling security", THEME_PHYSICAL),
    AnnexAControl("A.7.13", "Equipment maintenance", THEME_PHYSICAL),
    AnnexAControl("A.7.14", "Secure disposal or re-use of equipment", THEME_PHYSICAL),
    # --- A.8 Technological controls (34) ----------------------------------
    AnnexAControl("A.8.1", "User endpoint devices", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.2", "Privileged access rights", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.3", "Information access restriction", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.4", "Access to source code", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.5", "Secure authentication", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.6", "Capacity management", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.7", "Protection against malware", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.8", "Management of technical vulnerabilities", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.9", "Configuration management", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.10", "Information deletion", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.11", "Data masking", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.12", "Data leakage prevention", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.13", "Information backup", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.14", "Redundancy of information processing facilities", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.15", "Logging", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.16", "Monitoring activities", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.17", "Clock synchronization", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.18", "Use of privileged utility programs", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.19", "Installation of software on operational systems", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.20", "Networks security", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.21", "Security of network services", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.22", "Segregation of networks", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.23", "Web filtering", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.24", "Use of cryptography", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.25", "Secure development life cycle", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.26", "Application security requirements", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.27", "Secure system architecture and engineering principles", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.28", "Secure coding", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.29", "Security testing in development and acceptance", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.30", "Outsourced development", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.31", "Separation of development, test and production environments", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.32", "Change management", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.33", "Test information", THEME_TECHNOLOGICAL),
    AnnexAControl("A.8.34", "Protection of information systems during audit testing", THEME_TECHNOLOGICAL),
]

# Provisional out-of-scope set, derived from FinFlow's operating profile:
# fully remote, no owned or leased premises, all production infrastructure in AWS
# eu-west-1, no outsourced software development.
#
# The note records WHERE THE RISK WENT, not merely that the control does not apply.
# Phase 3 expands each of these into a formal justification_exclusion on the SoA.
PROVISIONAL_EXCLUSIONS: dict[str, str] = {
    "A.7.1": (
        "FinFlow holds no owned or leased premises. Perimeter risk for production "
        "systems sits with AWS under the shared responsibility model and is assured "
        "via the provider's SOC 2 Type II report."
    ),
    "A.7.2": (
        "No company-controlled entry points exist. Physical entry risk for production "
        "systems is transferred to AWS and assured via their SOC 2 Type II report."
    ),
    "A.7.3": (
        "No offices, rooms or facilities are operated by FinFlow. Home-working risk is "
        "addressed by A.6.7 (Remote working) and A.7.9 (Security of assets off-premises)."
    ),
    "A.7.4": (
        "No premises exist to monitor. Monitoring of the production estate is logical, "
        "not physical, and is covered by A.8.16 (Monitoring activities)."
    ),
    "A.7.5": (
        "Physical and environmental threat protection for production infrastructure is "
        "an AWS responsibility under the shared responsibility model; availability risk "
        "is retained and managed through A.8.14 (Redundancy)."
    ),
    "A.7.6": (
        "FinFlow operates no secure areas. Equivalent restriction of sensitive work is "
        "enforced logically through A.8.3 (Information access restriction)."
    ),
    "A.7.11": (
        "Supporting utilities (power, cooling) for production systems are provided and "
        "assured by AWS under the shared responsibility model."
    ),
    "A.7.12": (
        "FinFlow owns no cabling infrastructure. Data-in-transit risk is retained and "
        "addressed by A.8.24 (Use of cryptography)."
    ),
    "A.8.30": (
        "All software is developed in-house by FinFlow engineers. No development is "
        "outsourced, so there is no supplier development risk to manage."
    ),
}
