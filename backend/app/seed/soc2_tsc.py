"""AICPA SOC 2 Trust Services Criteria (2017, with 2022 points of focus revision).

SOC 2 is the SECONDARY framework in GRCShield. It is not assessed independently;
it is reached by mapping from the ISO/IEC 27001:2022 Annex A controls FinFlow
operates. See ``iso_soc2_mappings.py``.

The criteria reference numbers (CC1.1, A1.2, P6.3 ...) are the real AICPA
identifiers. The ``title`` strings are short plain-English descriptions written for
this project -- they are NOT the verbatim AICPA criteria text, which is copyrighted.
Anyone using this for real work should read the criteria from the AICPA publication.

Category counts:
    CC  Common Criteria     33   (required in every SOC 2 engagement)
    A   Availability         3
    C   Confidentiality      2
    PI  Processing Integrity 5
    P   Privacy             18
"""

from typing import NamedTuple


class TrustServicesCriterion(NamedTuple):
    ref: str
    title: str
    category: str
    category_title: str


_COMMON = "Common Criteria"

TSC_CRITERIA: list[TrustServicesCriterion] = [
    # --- CC1 Control Environment ------------------------------------------
    TrustServicesCriterion("CC1.1", "Commitment to integrity and ethical values", "CC1", "Control Environment"),
    TrustServicesCriterion("CC1.2", "Board independence and oversight of internal control", "CC1", "Control Environment"),
    TrustServicesCriterion("CC1.3", "Organizational structure, reporting lines and authority", "CC1", "Control Environment"),
    TrustServicesCriterion("CC1.4", "Commitment to attracting, developing and retaining competent people", "CC1", "Control Environment"),
    TrustServicesCriterion("CC1.5", "Individuals held accountable for internal control responsibilities", "CC1", "Control Environment"),
    # --- CC2 Communication and Information ---------------------------------
    TrustServicesCriterion("CC2.1", "Quality information obtained and used to support internal control", "CC2", "Communication and Information"),
    TrustServicesCriterion("CC2.2", "Internal communication of control objectives and responsibilities", "CC2", "Communication and Information"),
    TrustServicesCriterion("CC2.3", "External communication with relevant outside parties", "CC2", "Communication and Information"),
    # --- CC3 Risk Assessment ------------------------------------------------
    TrustServicesCriterion("CC3.1", "Objectives specified with sufficient clarity to assess risk", "CC3", "Risk Assessment"),
    TrustServicesCriterion("CC3.2", "Risks to objectives identified and analysed", "CC3", "Risk Assessment"),
    TrustServicesCriterion("CC3.3", "Potential for fraud considered in assessing risk", "CC3", "Risk Assessment"),
    TrustServicesCriterion("CC3.4", "Changes that could affect internal control identified and assessed", "CC3", "Risk Assessment"),
    # --- CC4 Monitoring Activities ------------------------------------------
    TrustServicesCriterion("CC4.1", "Ongoing and separate evaluations of control operation", "CC4", "Monitoring Activities"),
    TrustServicesCriterion("CC4.2", "Control deficiencies evaluated and communicated for corrective action", "CC4", "Monitoring Activities"),
    # --- CC5 Control Activities ---------------------------------------------
    TrustServicesCriterion("CC5.1", "Control activities selected and developed to mitigate risk", "CC5", "Control Activities"),
    TrustServicesCriterion("CC5.2", "Control activities over technology selected and developed", "CC5", "Control Activities"),
    TrustServicesCriterion("CC5.3", "Control activities deployed through policies and procedures", "CC5", "Control Activities"),
    # --- CC6 Logical and Physical Access Controls ---------------------------
    TrustServicesCriterion("CC6.1", "Logical access security software and infrastructure restrict access", "CC6", "Logical and Physical Access Controls"),
    TrustServicesCriterion("CC6.2", "User registration, authorisation and de-registration", "CC6", "Logical and Physical Access Controls"),
    TrustServicesCriterion("CC6.3", "Access to data and functions granted on least privilege and reviewed", "CC6", "Logical and Physical Access Controls"),
    TrustServicesCriterion("CC6.4", "Physical access to facilities and protected assets restricted", "CC6", "Logical and Physical Access Controls"),
    TrustServicesCriterion("CC6.5", "Data and media rendered unreadable on disposal or decommissioning", "CC6", "Logical and Physical Access Controls"),
    TrustServicesCriterion("CC6.6", "Security measures applied against threats from outside system boundaries", "CC6", "Logical and Physical Access Controls"),
    TrustServicesCriterion("CC6.7", "Transmission, movement and removal of information restricted and protected", "CC6", "Logical and Physical Access Controls"),
    TrustServicesCriterion("CC6.8", "Controls to prevent or detect unauthorised or malicious software", "CC6", "Logical and Physical Access Controls"),
    # --- CC7 System Operations -----------------------------------------------
    TrustServicesCriterion("CC7.1", "Configuration standards and vulnerability detection", "CC7", "System Operations"),
    TrustServicesCriterion("CC7.2", "Monitoring of system components for anomalies and security events", "CC7", "System Operations"),
    TrustServicesCriterion("CC7.3", "Security events evaluated to determine whether they are incidents", "CC7", "System Operations"),
    TrustServicesCriterion("CC7.4", "Response to identified security incidents", "CC7", "System Operations"),
    TrustServicesCriterion("CC7.5", "Recovery from identified security incidents", "CC7", "System Operations"),
    # --- CC8 Change Management ------------------------------------------------
    TrustServicesCriterion("CC8.1", "Changes to infrastructure, data, software and procedures are authorised, designed, tested and approved", "CC8", "Change Management"),
    # --- CC9 Risk Mitigation --------------------------------------------------
    TrustServicesCriterion("CC9.1", "Risk mitigation activities for business disruptions", "CC9", "Risk Mitigation"),
    TrustServicesCriterion("CC9.2", "Risks arising from vendors and business partners assessed and managed", "CC9", "Risk Mitigation"),
    # --- A1 Availability -------------------------------------------------------
    TrustServicesCriterion("A1.1", "Capacity demand managed to meet availability objectives", "A1", "Availability"),
    TrustServicesCriterion("A1.2", "Backup, recovery and environmental protection support availability objectives", "A1", "Availability"),
    TrustServicesCriterion("A1.3", "Recovery plan procedures tested to support availability objectives", "A1", "Availability"),
    # --- C1 Confidentiality ----------------------------------------------------
    TrustServicesCriterion("C1.1", "Confidential information identified and protected through its lifecycle", "C1", "Confidentiality"),
    TrustServicesCriterion("C1.2", "Confidential information disposed of when no longer required", "C1", "Confidentiality"),
    # --- PI1 Processing Integrity ----------------------------------------------
    TrustServicesCriterion("PI1.1", "Information about processing objectives and data quality communicated", "PI1", "Processing Integrity"),
    TrustServicesCriterion("PI1.2", "System inputs are complete, accurate and timely", "PI1", "Processing Integrity"),
    TrustServicesCriterion("PI1.3", "Processing is complete, accurate, timely and authorised", "PI1", "Processing Integrity"),
    TrustServicesCriterion("PI1.4", "System outputs are complete, accurate and delivered as specified", "PI1", "Processing Integrity"),
    TrustServicesCriterion("PI1.5", "Stored information is retained completely, accurately and in a timely manner", "PI1", "Processing Integrity"),
    # --- P Privacy ---------------------------------------------------------------
    TrustServicesCriterion("P1.1", "Privacy notice provided about collection, use, retention and disclosure", "P1", "Notice and Communication of Objectives"),
    TrustServicesCriterion("P2.1", "Consent and choice communicated and obtained where required", "P2", "Choice and Consent"),
    TrustServicesCriterion("P3.1", "Personal information collected consistently with objectives", "P3", "Collection"),
    TrustServicesCriterion("P3.2", "Explicit consent obtained for sensitive personal information", "P3", "Collection"),
    TrustServicesCriterion("P4.1", "Personal information used only for stated purposes", "P4", "Use, Retention and Disposal"),
    TrustServicesCriterion("P4.2", "Personal information retained only as long as necessary", "P4", "Use, Retention and Disposal"),
    TrustServicesCriterion("P4.3", "Personal information securely disposed of when no longer needed", "P4", "Use, Retention and Disposal"),
    TrustServicesCriterion("P5.1", "Data subjects can access their personal information", "P5", "Access"),
    TrustServicesCriterion("P5.2", "Data subjects can correct, amend or append their personal information", "P5", "Access"),
    TrustServicesCriterion("P6.1", "Personal information disclosed to third parties only with consent or authority", "P6", "Disclosure and Notification"),
    TrustServicesCriterion("P6.2", "Record kept of authorised disclosures of personal information", "P6", "Disclosure and Notification"),
    TrustServicesCriterion("P6.3", "Record kept of unauthorised disclosures of personal information", "P6", "Disclosure and Notification"),
    TrustServicesCriterion("P6.4", "Third parties obtain commitments to protect disclosed personal information", "P6", "Disclosure and Notification"),
    TrustServicesCriterion("P6.5", "Notification obtained from third parties of unauthorised disclosure", "P6", "Disclosure and Notification"),
    TrustServicesCriterion("P6.6", "Affected data subjects, regulators and others notified of breaches", "P6", "Disclosure and Notification"),
    TrustServicesCriterion("P6.7", "Accounting of personal information held and disclosed provided on request", "P6", "Disclosure and Notification"),
    TrustServicesCriterion("P7.1", "Personal information collected and maintained is accurate and complete", "P7", "Quality"),
    TrustServicesCriterion("P8.1", "Privacy complaints and disputes handled and resolved", "P8", "Monitoring and Enforcement"),
]

# Categories other than CC are only in scope for a SOC 2 report if the service
# organisation elects them. FinFlow's illustrative election:
ELECTED_CATEGORIES = {
    "CC": True,   # mandatory
    "A1": True,   # SaaS payments product with uptime commitments
    "C1": True,   # customer financial data
    "PI1": False, # not elected -- see docs/SCOPE.md
    "P1": False, "P2": False, "P3": False, "P4": False,
    "P5": False, "P6": False, "P7": False, "P8": False,
}
