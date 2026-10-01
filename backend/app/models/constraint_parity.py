"""Named checks already deployed by migrations; shared by metadata-built test databases."""

from sqlalchemy import CheckConstraint

from app.db.base import Base

LEGACY_CHECKS = [
    (
        "risks",
        "ck_risks_residual_justification_present",
        "length(trim(residual_justification)) > 0",
    ),
    ("evidence", "ck_evidence_validity_window", "valid_until >= valid_from"),
    ("remediation_items", "ck_remediation_owner_present", "length(trim(owner)) > 0"),
    (
        "soa_entries",
        "ck_soa_justification_matches_applicability",
        "(applicable AND length(trim(coalesce(justification_inclusion, ''))) > 0) OR (NOT applicable AND length(trim(coalesce(justification_exclusion, ''))) > 0)",
    ),
    (
        "soa_entries",
        "ck_soa_excluded_not_implemented",
        "applicable OR implementation_status = 'NOT_IMPLEMENTED'",
    ),
    ("control_tests", "ck_control_tests_population", "population_size >= 1"),
    ("control_tests", "ck_control_tests_sample_min", "sample_size >= 1"),
    (
        "control_tests",
        "ck_control_tests_sample_within_population",
        "sample_size <= population_size",
    ),
    (
        "control_tests",
        "ck_control_tests_exceptions_within_sample",
        "exceptions_count >= 0 AND exceptions_count <= sample_size",
    ),
    ("control_tests", "ck_control_tests_rationale_present", "length(trim(sampling_rationale)) > 0"),
    ("control_tests", "ck_control_tests_period", "period_covered_end >= period_covered_start"),
    (
        "control_tests",
        "ck_control_tests_conclusion_matches_exceptions",
        "(exceptions_count = 0 AND conclusion <> 'PASS_WITH_EXCEPTIONS') OR (exceptions_count > 0 AND conclusion <> 'PASS')",
    ),
    (
        "nonconformities",
        "ck_nonconformity_closed_needs_effectiveness_check",
        "status <> 'CLOSED' OR length(trim(coalesce(effectiveness_check_result, ''))) > 0",
    ),
    (
        "risk_exceptions",
        "ck_exception_expiry_after_approval",
        "approval_date IS NULL OR expiry_date > approval_date",
    ),
    ("risk_exceptions", "ck_exception_review_trigger_present", "length(trim(review_trigger)) > 0"),
    (
        "ropa_entries",
        "ck_ropa_transfer_safeguard_matches",
        "(transfers_outside_eea AND transfer_safeguard <> 'NOT_APPLICABLE') OR (NOT transfers_outside_eea AND transfer_safeguard = 'NOT_APPLICABLE')",
    ),
    ("ropa_entries", "ck_ropa_retention_present", "length(trim(retention_period)) > 0"),
    (
        "dpias",
        "ck_dpia_high_residual_requires_consultation",
        "residual_risk <> 'HIGH' OR outcome NOT IN ('PROCEED', 'PROCEED_WITH_MEASURES') OR supervisory_authority_consulted",
    ),
    ("business_impact_analyses", "ck_bia_rto_within_mtpd", "rto_hours <= mtpd_hours"),
    ("business_impact_analyses", "ck_bia_rpo_within_mtpd", "rpo_hours <= mtpd_hours"),
    (
        "business_impact_analyses",
        "ck_bia_non_negative",
        "rto_hours >= 0 AND rpo_hours >= 0 AND mtpd_hours >= 0",
    ),
    ("kri_definitions", "ck_kri_formula_present", "length(trim(formula_description)) > 0"),
]

LEGACY_CHECKS.extend([('controls', 'ck_controls_design_caps_operating', "NOT (design_effectiveness = 'DEFICIENT' AND operating_effectiveness = 'EFFECTIVE')"), ('remediation_items', 'ck_remediation_raised_before_completed', 'raised_date IS NULL OR completed_date IS NULL OR completed_date >= raised_date'), ('risks', 'ck_risks_inherent_impact', 'inherent_impact BETWEEN 1 AND 5'), ('risks', 'ck_risks_inherent_likelihood', 'inherent_likelihood BETWEEN 1 AND 5'), ('risks', 'ck_risks_residual_impact', 'residual_impact BETWEEN 1 AND 5'), ('risks', 'ck_risks_residual_likelihood', 'residual_likelihood BETWEEN 1 AND 5')])

for table, name, expression in LEGACY_CHECKS:
    if name not in {c.name for c in Base.metadata.tables[table].constraints}:
        Base.metadata.tables[table].append_constraint(CheckConstraint(expression, name=name))
