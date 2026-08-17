"""Asset register.

Twelve assets, concrete enough to point a RoPA entry or a BIA at. AST-007 and AST-008
are the two stores TEST-008 found holding unmasked customer data.
"""

from typing import NamedTuple


class AssetSpec(NamedTuple):
    ref: str
    name: str
    description: str
    asset_type: str
    classification: str
    owner_role: str
    hosting_location: str
    holds_personal_data: bool


ASSETS: list[AssetSpec] = [
    AssetSpec(
        "AST-001", "Production database cluster",
        "Multi-AZ PostgreSQL cluster holding merchant records, transaction metadata and "
        "cardholder references. Full card numbers are held by the payment service "
        "provider, not here.",
        "DATA_STORE", "RESTRICTED", "Head of Engineering", "AWS eu-west-1", True,
    ),
    AssetSpec(
        "AST-002", "Payment API service",
        "Public API accepting transaction requests from merchant integrations and "
        "forwarding them to the payment service provider.",
        "SYSTEM", "CONFIDENTIAL", "Head of Engineering", "AWS eu-west-1", True,
    ),
    AssetSpec(
        "AST-003", "Merchant web application",
        "Browser application through which merchants manage their account, view "
        "settlements and configure payout destinations.",
        "SYSTEM", "CONFIDENTIAL", "Head of Engineering", "AWS eu-west-1", True,
    ),
    AssetSpec(
        "AST-004", "Okta identity tenant",
        "Single source of workforce identity and the authentication path to every other "
        "system. Its loss blocks all staff access simultaneously.",
        "SAAS_SERVICE", "RESTRICTED", "Head of Engineering", "Okta (EU region)", True,
    ),
    AssetSpec(
        "AST-005", "GitHub organisation",
        "Source code, infrastructure definitions and CI pipelines for every FinFlow "
        "service.",
        "SAAS_SERVICE", "CONFIDENTIAL", "Head of Engineering", "GitHub (US)", False,
    ),
    AssetSpec(
        "AST-006", "AWS production account",
        "The eu-west-1 account containing all production compute, storage and networking.",
        "SYSTEM", "RESTRICTED", "Head of Engineering", "AWS eu-west-1", True,
    ),
    AssetSpec(
        "AST-007", "Analytics warehouse",
        "Reporting warehouse fed from production for product and commercial analysis. "
        "TEST-008 found approximately 180,000 unmasked customer records here.",
        "DATA_STORE", "RESTRICTED", "Head of Engineering", "AWS eu-west-1", True,
    ),
    AssetSpec(
        "AST-008", "Customer support tooling",
        "Ticketing platform used by the support team, including staff located in India. "
        "TEST-008 found approximately 12,000 unmasked customer records in its replica.",
        "SAAS_SERVICE", "RESTRICTED", "Chief Operating Officer", "Vendor SaaS (EU region)", True,
    ),
    AssetSpec(
        "AST-009", "Company macOS laptop fleet",
        "All issued endpoints, MDM-enrolled with disk encryption and endpoint detection. "
        "The only hardware FinFlow owns.",
        "DEVICE_FLEET", "CONFIDENTIAL", "Head of Engineering", "Distributed (remote staff)", True,
    ),
    AssetSpec(
        "AST-010", "Payment service provider integration",
        "The third-party PSP that performs card authorisation, settlement and fraud "
        "screening. Cardholder data lives here, not in FinFlow's estate.",
        "THIRD_PARTY_SERVICE", "RESTRICTED", "Chief Operating Officer", "PSP (EU)", True,
    ),
    AssetSpec(
        "AST-011", "HR information system",
        "Employee records, contracts and screening outcomes for all staff and contractors.",
        "SAAS_SERVICE", "CONFIDENTIAL", "Head of People", "Vendor SaaS (EU region)", True,
    ),
    AssetSpec(
        "AST-012", "Centralised logging account",
        "Dedicated AWS account receiving application, infrastructure and CloudTrail logs "
        "with 12-month retention and restricted access.",
        "DATA_STORE", "CONFIDENTIAL", "Head of Engineering", "AWS eu-west-1", True,
    ),
]
