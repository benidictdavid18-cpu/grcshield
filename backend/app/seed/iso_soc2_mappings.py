"""ISO/IEC 27001:2022 Annex A  ->  SOC 2 Trust Services Criteria mappings.

Direction matters. ISO is the primary framework: FinFlow assesses itself against
Annex A, and SOC 2 coverage is *derived* from that assessment. Mapping the other
way round would imply a SOC 2 engagement that does not exist.

Only controls that are in scope per ``annex_a_2022.PROVISIONAL_EXCLUSIONS`` are
mapped -- an excluded control has no operating evidence, so claiming it satisfies a
Trust Services criterion would be false.

Only ELECTED SOC 2 categories are mapped (CC, A1, C1). Privacy (P) and Processing
Integrity (PI1) are not elected, so ISO controls whose natural counterpart sits in
those categories -- notably A.5.34 -- carry no mapping. That gap is intentional and
visible rather than papered over.

Relationship semantics:
    EQUIVALENT   The ISO control substantially satisfies the criterion on its own.
    PARTIAL      The ISO control satisfies part of the criterion; other controls are
                 needed to cover the rest.
    SUPPORTING   The ISO control contributes evidence but is not the primary control
                 an auditor would test for that criterion.
"""

EQUIVALENT = "EQUIVALENT"
PARTIAL = "PARTIAL"
SUPPORTING = "SUPPORTING"

# (iso_ref, tsc_ref, relationship)
ISO_TO_SOC2: list[tuple[str, str, str]] = [
    # --- A.5 Organizational --------------------------------------------------
    ("A.5.1", "CC5.3", EQUIVALENT),
    ("A.5.1", "CC1.1", SUPPORTING),
    ("A.5.2", "CC1.3", EQUIVALENT),
    ("A.5.2", "CC1.5", PARTIAL),
    ("A.5.3", "CC1.3", PARTIAL),
    ("A.5.3", "CC6.3", PARTIAL),
    ("A.5.4", "CC1.1", PARTIAL),
    ("A.5.4", "CC1.5", EQUIVALENT),
    ("A.5.5", "CC2.3", PARTIAL),
    ("A.5.6", "CC2.3", SUPPORTING),
    ("A.5.7", "CC3.2", PARTIAL),
    ("A.5.7", "CC7.1", SUPPORTING),
    ("A.5.8", "CC8.1", PARTIAL),
    ("A.5.8", "CC3.4", SUPPORTING),
    ("A.5.9", "CC6.1", PARTIAL),
    ("A.5.9", "CC3.2", SUPPORTING),
    ("A.5.10", "CC5.3", PARTIAL),
    ("A.5.10", "CC1.1", SUPPORTING),
    ("A.5.11", "CC6.5", PARTIAL),
    ("A.5.12", "CC3.2", PARTIAL),
    ("A.5.12", "C1.1", PARTIAL),
    ("A.5.13", "C1.1", SUPPORTING),
    ("A.5.14", "CC6.7", EQUIVALENT),
    ("A.5.15", "CC6.1", PARTIAL),
    ("A.5.15", "CC6.2", PARTIAL),
    ("A.5.15", "CC6.3", PARTIAL),
    ("A.5.16", "CC6.1", PARTIAL),
    ("A.5.16", "CC6.2", EQUIVALENT),
    ("A.5.17", "CC6.1", PARTIAL),
    ("A.5.18", "CC6.2", PARTIAL),
    ("A.5.18", "CC6.3", EQUIVALENT),
    ("A.5.19", "CC9.2", PARTIAL),
    ("A.5.20", "CC9.2", PARTIAL),
    ("A.5.21", "CC9.2", PARTIAL),
    ("A.5.22", "CC9.2", PARTIAL),
    ("A.5.22", "CC4.1", SUPPORTING),
    ("A.5.23", "CC9.2", PARTIAL),
    ("A.5.23", "CC6.1", SUPPORTING),
    ("A.5.24", "CC7.3", PARTIAL),
    ("A.5.24", "CC7.4", PARTIAL),
    ("A.5.25", "CC7.3", EQUIVALENT),
    ("A.5.26", "CC7.4", EQUIVALENT),
    ("A.5.27", "CC7.5", PARTIAL),
    ("A.5.27", "CC4.2", SUPPORTING),
    ("A.5.28", "CC7.4", SUPPORTING),
    ("A.5.29", "CC9.1", PARTIAL),
    ("A.5.29", "A1.2", SUPPORTING),
    ("A.5.30", "A1.2", PARTIAL),
    ("A.5.30", "A1.3", EQUIVALENT),
    ("A.5.31", "CC3.1", PARTIAL),
    ("A.5.31", "CC2.3", SUPPORTING),
    ("A.5.32", "CC1.1", SUPPORTING),
    ("A.5.33", "C1.1", PARTIAL),
    # A.5.34 (Privacy and protection of PII) -- no mapping: the SOC 2 Privacy
    # category is not elected. Covered instead by the GDPR RoPA/DPIA modules.
    ("A.5.35", "CC4.1", EQUIVALENT),
    ("A.5.36", "CC4.1", PARTIAL),
    ("A.5.36", "CC5.3", SUPPORTING),
    ("A.5.37", "CC5.3", PARTIAL),
    # --- A.6 People ------------------------------------------------------------
    ("A.6.1", "CC1.4", PARTIAL),
    ("A.6.2", "CC1.4", PARTIAL),
    ("A.6.2", "CC1.1", SUPPORTING),
    ("A.6.3", "CC1.4", PARTIAL),
    ("A.6.3", "CC2.2", EQUIVALENT),
    ("A.6.4", "CC1.5", PARTIAL),
    ("A.6.5", "CC6.2", PARTIAL),
    ("A.6.5", "CC1.4", SUPPORTING),
    ("A.6.6", "C1.1", PARTIAL),
    ("A.6.6", "CC9.2", SUPPORTING),
    ("A.6.7", "CC6.6", PARTIAL),
    ("A.6.7", "CC6.7", SUPPORTING),
    ("A.6.8", "CC2.2", PARTIAL),
    ("A.6.8", "CC7.2", SUPPORTING),
    # --- A.7 Physical (in-scope subset only) -----------------------------------
    ("A.7.7", "CC6.4", SUPPORTING),
    ("A.7.8", "CC6.4", SUPPORTING),
    ("A.7.9", "CC6.4", PARTIAL),
    ("A.7.9", "CC6.7", SUPPORTING),
    ("A.7.10", "CC6.7", PARTIAL),
    ("A.7.10", "CC6.5", SUPPORTING),
    ("A.7.13", "A1.1", SUPPORTING),
    ("A.7.14", "CC6.5", EQUIVALENT),
    ("A.7.14", "C1.2", PARTIAL),
    # --- A.8 Technological -------------------------------------------------------
    ("A.8.1", "CC6.6", PARTIAL),
    ("A.8.1", "CC6.8", PARTIAL),
    ("A.8.2", "CC6.1", PARTIAL),
    ("A.8.2", "CC6.3", PARTIAL),
    ("A.8.3", "CC6.1", PARTIAL),
    ("A.8.3", "CC6.3", PARTIAL),
    ("A.8.4", "CC6.1", SUPPORTING),
    ("A.8.4", "CC8.1", PARTIAL),
    ("A.8.5", "CC6.1", EQUIVALENT),
    ("A.8.6", "A1.1", EQUIVALENT),
    ("A.8.7", "CC6.8", EQUIVALENT),
    ("A.8.8", "CC7.1", EQUIVALENT),
    ("A.8.9", "CC7.1", PARTIAL),
    ("A.8.9", "CC8.1", PARTIAL),
    ("A.8.10", "CC6.5", PARTIAL),
    ("A.8.10", "C1.2", EQUIVALENT),
    ("A.8.11", "C1.1", PARTIAL),
    ("A.8.12", "CC6.7", EQUIVALENT),
    ("A.8.13", "A1.2", EQUIVALENT),
    ("A.8.14", "A1.2", PARTIAL),
    ("A.8.15", "CC7.2", PARTIAL),
    ("A.8.16", "CC7.2", EQUIVALENT),
    ("A.8.16", "CC4.1", SUPPORTING),
    ("A.8.17", "CC7.2", SUPPORTING),
    ("A.8.18", "CC6.1", SUPPORTING),
    ("A.8.18", "CC6.8", PARTIAL),
    ("A.8.19", "CC6.8", PARTIAL),
    ("A.8.19", "CC8.1", SUPPORTING),
    ("A.8.20", "CC6.6", PARTIAL),
    ("A.8.21", "CC6.6", PARTIAL),
    ("A.8.22", "CC6.6", PARTIAL),
    ("A.8.23", "CC6.6", SUPPORTING),
    ("A.8.23", "CC6.8", SUPPORTING),
    ("A.8.24", "CC6.1", SUPPORTING),
    ("A.8.24", "CC6.7", PARTIAL),
    ("A.8.24", "C1.1", PARTIAL),
    ("A.8.25", "CC8.1", PARTIAL),
    ("A.8.26", "CC8.1", PARTIAL),
    ("A.8.27", "CC8.1", SUPPORTING),
    ("A.8.28", "CC8.1", PARTIAL),
    ("A.8.29", "CC8.1", PARTIAL),
    ("A.8.29", "CC7.1", SUPPORTING),
    # A.8.30 (Outsourced development) -- excluded from scope, so not mapped.
    ("A.8.31", "CC8.1", PARTIAL),
    ("A.8.32", "CC8.1", EQUIVALENT),
    ("A.8.33", "CC8.1", SUPPORTING),
    ("A.8.33", "C1.1", SUPPORTING),
    ("A.8.34", "CC4.1", SUPPORTING),
]
