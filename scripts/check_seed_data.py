"""Static integrity checks on the seed data. No database required.

Run from grc/backend:   python ../scripts/check_seed_data.py
Or from grc:            python scripts/check_seed_data.py

Catches the failure modes that matter for this project: a miscounted Annex A theme,
an invented control identifier, a mapping pointing at an excluded control, or a
mapping into a Trust Services category FinFlow has not elected.
"""

import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.seed.annex_a_2022 import ANNEX_A_CONTROLS, PROVISIONAL_EXCLUSIONS  # noqa: E402
from app.seed.asset_register import ASSETS  # noqa: E402
from app.seed.continuity_register import BIA_PROCESSES  # noqa: E402
from app.seed.exception_register import RISK_EXCEPTIONS  # noqa: E402
from app.seed.privacy_register import DPIAS, ROPA_ENTRIES  # noqa: E402
from app.seed.control_tests import (  # noqa: E402
    AUDIT_FINDINGS,
    CONTROL_TESTS,
    INTERNAL_AUDITS,
    MANAGEMENT_REVIEWS,
    NONCONFORMITIES,
)
from app.seed.evidence_register import EVIDENCE  # noqa: E402
from app.seed.internal_controls import EFFECTIVENESS, INTERNAL_CONTROLS  # noqa: E402
from app.seed.iso_soc2_mappings import ISO_TO_SOC2  # noqa: E402
from app.seed.remediation_register import REMEDIATION_ITEMS  # noqa: E402
from app.seed.risk_register import APPETITE_THRESHOLDS, RISKS, TODO  # noqa: E402
from app.seed.soa_register import SOA_ENTRIES  # noqa: E402
from app.seed.soc2_tsc import ELECTED_CATEGORIES, TSC_CRITERIA  # noqa: E402
from app.services.control_testing import (  # noqa: E402
    CONCLUSION_TO_OPERATING,
    DesignEffectiveness,
    OperatingEffectiveness,
    SampleSelectionMethod,
    TestConclusion,
    basis_supported_by_control,
    requires_finding,
    validate_effectiveness,
    validate_test,
)
from app.services.privacy_continuity import (  # noqa: E402
    DpiaOutcome,
    ExceptionStatus,
    LawfulBasis,
    ResidualRiskLevel,
    TransferSafeguard,
    exception_state,
    validate_bia,
    validate_dpia,
    validate_exception,
    validate_ropa,
)
from app.services.risk_scoring import (  # noqa: E402
    ControlEffectivenessBasis,
    RiskCategory,
    band_for,
    basis_credits_reduction,
    exceeds_appetite,
    score,
)

EXPECTED_THEME_COUNTS = {"A.5": 37, "A.6": 8, "A.7": 14, "A.8": 34}

failures: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


# --- Annex A completeness --------------------------------------------------
theme_counts = Counter(c.theme for c in ANNEX_A_CONTROLS)
for theme, expected in EXPECTED_THEME_COUNTS.items():
    check(
        theme_counts[theme] == expected,
        f"{theme}: expected {expected} controls, found {theme_counts[theme]}",
    )
check(len(ANNEX_A_CONTROLS) == 93, f"Annex A total: expected 93, found {len(ANNEX_A_CONTROLS)}")

refs = [c.ref for c in ANNEX_A_CONTROLS]
duplicates = [ref for ref, n in Counter(refs).items() if n > 1]
check(not duplicates, f"Duplicate Annex A refs: {duplicates}")

# Identifiers must be contiguous within each theme -- a gap means a control was dropped.
for theme, expected in EXPECTED_THEME_COUNTS.items():
    numbers = sorted(int(c.ref.rsplit(".", 1)[1]) for c in ANNEX_A_CONTROLS if c.theme == theme)
    check(
        numbers == list(range(1, expected + 1)),
        f"{theme}: identifiers are not contiguous 1..{expected} -- got {numbers}",
    )

# --- Exclusions ------------------------------------------------------------
ref_set = set(refs)
unknown_exclusions = set(PROVISIONAL_EXCLUSIONS) - ref_set
check(not unknown_exclusions, f"Exclusions reference unknown controls: {sorted(unknown_exclusions)}")
check(
    5 <= len(PROVISIONAL_EXCLUSIONS) <= 10,
    f"Exclusion count {len(PROVISIONAL_EXCLUSIONS)} is outside the 5-10 target band",
)
for excluded_ref, note in PROVISIONAL_EXCLUSIONS.items():
    check(
        len(note.split()) >= 15,
        f"{excluded_ref}: exclusion note is too thin to explain where the risk went",
    )

# --- SOC 2 criteria --------------------------------------------------------
tsc_refs = {c.ref for c in TSC_CRITERIA}
common_criteria = [c for c in TSC_CRITERIA if c.category.startswith("CC")]
check(len(common_criteria) == 33, f"Common Criteria: expected 33, found {len(common_criteria)}")
tsc_dupes = [ref for ref, n in Counter(c.ref for c in TSC_CRITERIA).items() if n > 1]
check(not tsc_dupes, f"Duplicate TSC refs: {tsc_dupes}")

elected_refs = {
    c.ref
    for c in TSC_CRITERIA
    if c.category.startswith("CC") or ELECTED_CATEGORIES.get(c.category, False)
}

# --- Mappings --------------------------------------------------------------
in_scope_iso = ref_set - set(PROVISIONAL_EXCLUSIONS)
for iso_ref, tsc_ref, relationship in ISO_TO_SOC2:
    check(iso_ref in ref_set, f"Mapping uses unknown ISO control '{iso_ref}'")
    check(tsc_ref in tsc_refs, f"Mapping uses unknown TSC criterion '{tsc_ref}'")
    check(
        iso_ref in in_scope_iso,
        f"Mapping '{iso_ref}' -> '{tsc_ref}' starts from an out-of-scope ISO control",
    )
    check(
        tsc_ref in elected_refs,
        f"Mapping '{iso_ref}' -> '{tsc_ref}' targets a category FinFlow has not elected",
    )
    check(
        relationship in {"EQUIVALENT", "PARTIAL", "SUPPORTING"},
        f"Mapping '{iso_ref}' -> '{tsc_ref}' has unknown relationship '{relationship}'",
    )

pair_dupes = [p for p, n in Counter((a, b) for a, b, _ in ISO_TO_SOC2).items() if n > 1]
check(not pair_dupes, f"Duplicate mapping pairs: {pair_dupes}")

mapped_iso = {a for a, _, _ in ISO_TO_SOC2}
unmapped = sorted(in_scope_iso - mapped_iso)

# --- Internal control library ------------------------------------------------
internal_ids = {c.control_id for c in INTERNAL_CONTROLS}
internal_dupes = [i for i, n in Counter(c.control_id for c in INTERNAL_CONTROLS).items() if n > 1]
check(not internal_dupes, f"Duplicate internal control ids: {internal_dupes}")
for control in INTERNAL_CONTROLS:
    unknown_refs = set(control.annex_a_refs) - ref_set
    check(not unknown_refs, f"{control.control_id} maps to unknown Annex A refs: {sorted(unknown_refs)}")
    excluded_refs = set(control.annex_a_refs) & set(PROVISIONAL_EXCLUSIONS)
    check(
        not excluded_refs,
        f"{control.control_id} maps to out-of-scope Annex A control(s) {sorted(excluded_refs)}",
    )
    check(bool(control.owner_role), f"{control.control_id} has no owner")

# --- Risk appetite -------------------------------------------------------------
appetite = {a.category: a for a in APPETITE_THRESHOLDS}
check(
    set(appetite) == set(RiskCategory),
    f"Appetite is missing categories: {sorted(c.value for c in set(RiskCategory) - set(appetite))}",
)
for spec in APPETITE_THRESHOLDS:
    # Risk acceptance is a business decision; the security function must not appear.
    check(
        "security" not in spec.approver_role.lower(),
        f"{spec.category.value} appetite is approved by '{spec.approver_role}' -- risk "
        "acceptance is a business decision, not a security decision",
    )
    check(
        len(spec.rationale.split()) >= 15,
        f"{spec.category.value} appetite rationale is too thin to defend",
    )

# --- Risk register ---------------------------------------------------------------
check(len(RISKS) == 20, f"Expected 20 risks, found {len(RISKS)}")
risk_refs = [r.risk_ref for r in RISKS]
check(
    risk_refs == [f"RISK-{n:03d}" for n in range(1, len(RISKS) + 1)],
    "Risk references are not a contiguous RISK-001.. sequence",
)
check(
    len({r.category for r in RISKS}) == len(RiskCategory),
    "Not every risk category is represented in the register",
)

todo_risks = [r.risk_ref for r in RISKS if TODO in r.residual_justification]
check(len(todo_risks) == 5, f"Expected 5 author-written justifications outstanding, found {len(todo_risks)}")

breaching: list[str] = []
for risk in RISKS:
    control_ids = [ref for ref, _ in risk.controls]
    unknown_controls = set(control_ids) - internal_ids
    check(not unknown_controls, f"{risk.risk_ref} links unknown controls: {sorted(unknown_controls)}")
    check(control_ids, f"{risk.risk_ref} has no linked controls")
    check(
        len(control_ids) == len(set(control_ids)),
        f"{risk.risk_ref} links the same control more than once",
    )

    inherent = score(risk.inherent_likelihood, risk.inherent_impact)
    residual = score(risk.residual_likelihood, risk.residual_impact)
    check(
        residual <= inherent,
        f"{risk.risk_ref} residual ({residual}) exceeds inherent ({inherent}) -- controls "
        "cannot make a risk worse under this model",
    )

    # The rule the API enforces on writes must hold for shipped seed data too.
    if residual < inherent:
        creditable = [b for _, b in risk.controls if basis_credits_reduction(b)]
        check(
            bool(creditable),
            f"{risk.risk_ref} claims a reduction ({inherent} -> {residual}) but every linked "
            "control is untested or tested ineffective",
        )

    if TODO not in risk.residual_justification:
        check(
            len(risk.residual_justification.split()) >= 25,
            f"{risk.risk_ref} justification is too thin to defend in review",
        )

    ceiling = appetite.get(risk.category)
    if ceiling and exceeds_appetite(band_for(residual), ceiling.max_acceptable_band):
        breaching.append(risk.risk_ref)

# --- Evidence and remediation --------------------------------------------------
AS_OF = date(2026, 8, 15)

evidence_refs = {e.ref for e in EVIDENCE}
check(
    len(evidence_refs) == len(EVIDENCE),
    "Duplicate evidence references in the evidence register",
)
for artifact in EVIDENCE:
    check(
        artifact.valid_until >= artifact.valid_from,
        f"{artifact.ref} expires before it becomes valid",
    )
    if artifact.control_ref is not None:
        check(
            artifact.control_ref in internal_ids,
            f"{artifact.ref} references unknown control '{artifact.control_ref}'",
        )
expired_evidence = sorted(e.ref for e in EVIDENCE if e.valid_until < AS_OF)

remediation_refs = {r.ref for r in REMEDIATION_ITEMS}
check(
    len(remediation_refs) == len(REMEDIATION_ITEMS),
    "Duplicate remediation references",
)
for item in REMEDIATION_ITEMS:
    check(bool(item.owner.strip()), f"{item.ref} has no owner")
    check(item.due_date is not None, f"{item.ref} has no due date")
    check(
        (item.status == "COMPLETED") == (item.completed_date is not None),
        f"{item.ref}: completed status and completion date disagree",
    )
open_remediation = [r for r in REMEDIATION_ITEMS if r.status not in ("COMPLETED", "CANCELLED")]
overdue = sorted(r.ref for r in open_remediation if r.due_date < AS_OF)

# --- Statement of Applicability ---------------------------------------------------
soa_refs = [s.ref for s in SOA_ENTRIES]
check(len(SOA_ENTRIES) == 93, f"SoA has {len(SOA_ENTRIES)} entries, expected 93")
check(len(set(soa_refs)) == len(soa_refs), "Duplicate SoA entries")
check(set(soa_refs) == ref_set, "SoA does not cover exactly the Annex A control set")

soa_excluded = sorted(s.ref for s in SOA_ENTRIES if not s.applicable)
check(
    set(soa_excluded) == set(PROVISIONAL_EXCLUSIONS),
    "SoA exclusions disagree with the Phase 1 scope decision: "
    f"SoA={soa_excluded} vs scope={sorted(PROVISIONAL_EXCLUSIONS)}",
)

soa_todo = sorted(s.ref for s in SOA_ENTRIES if s.inclusion and TODO in s.inclusion)
check(len(soa_todo) == 8, f"Expected 8 author-written SoA justifications, found {len(soa_todo)}")

soa_gaps: list[str] = []
for entry in SOA_ENTRIES:
    if entry.applicable:
        check(bool(entry.inclusion), f"{entry.ref} is applicable with no inclusion justification")
        check(
            entry.exclusion is None,
            f"{entry.ref} is applicable but carries an exclusion justification",
        )
        if TODO not in (entry.inclusion or ""):
            check(
                bool(entry.risks) or entry.inclusion is not None,
                f"{entry.ref} inclusion justification names no driver",
            )
        if entry.status != "IMPLEMENTED":
            soa_gaps.append(entry.ref)
            live = [
                r for r in entry.remediation
                if r in remediation_refs
                and next(x for x in REMEDIATION_ITEMS if x.ref == r).status != "CANCELLED"
            ]
            check(
                bool(live),
                f"{entry.ref} is a gap ({entry.status}) with no live remediation item",
            )
    else:
        check(bool(entry.exclusion), f"{entry.ref} is excluded with no exclusion justification")
        check(
            entry.inclusion is None,
            f"{entry.ref} is excluded but carries an inclusion justification",
        )
        check(
            entry.status == "NOT_IMPLEMENTED",
            f"{entry.ref} is excluded but claims status {entry.status}",
        )
        check(
            len(entry.exclusion.split()) >= 20,
            f"{entry.ref} exclusion justification is too thin to say where the risk went",
        )

    for label, refs, known in (
        ("control", entry.controls, internal_ids),
        ("risk", entry.risks, set(risk_refs)),
        ("evidence", entry.evidence, evidence_refs),
        ("remediation", entry.remediation, remediation_refs),
    ):
        unknown_links = set(refs) - known
        check(not unknown_links, f"{entry.ref} links unknown {label}(s): {sorted(unknown_links)}")

applicable_entries = [s for s in SOA_ENTRIES if s.applicable]
implemented_entries = [s for s in applicable_entries if s.status == "IMPLEMENTED"]
percent_implemented = round(100 * len(implemented_entries) / len(applicable_entries), 1)

# --- Control effectiveness ---------------------------------------------------
check(
    set(EFFECTIVENESS) == internal_ids,
    "Effectiveness ratings do not cover exactly the internal control library",
)
for control_id, (design, operating, _note) in EFFECTIVENESS.items():
    violations = validate_effectiveness(
        DesignEffectiveness(design), OperatingEffectiveness(operating)
    )
    check(not violations, f"{control_id}: {violations[0].message if violations else ''}")

# A risk link may not claim a tested basis for a control the library says was never
# tested. This is the rule that ties Phase 2's register to Phase 4's workpapers.
for risk in RISKS:
    for control_ref, basis in risk.controls:
        if control_ref not in EFFECTIVENESS:
            continue
        _design, operating, _ = EFFECTIVENESS[control_ref]
        check(
            basis_supported_by_control(
                ControlEffectivenessBasis(basis.value), OperatingEffectiveness(operating)
            ),
            f"{risk.risk_ref} claims basis {basis.value} for {control_ref}, which the control "
            "library records as never tested",
        )

# --- Control tests ---------------------------------------------------------------
test_refs = {t.ref for t in CONTROL_TESTS}
check(len(test_refs) == len(CONTROL_TESTS), "Duplicate control test references")
check(len(CONTROL_TESTS) == 12, f"Expected 12 control tests, found {len(CONTROL_TESTS)}")

finding_refs = {f.ref for f in AUDIT_FINDINGS}
test_todo = sorted(t.ref for t in CONTROL_TESTS if TODO in t.sampling_rationale)
check(len(test_todo) == 4, f"Expected 4 author-written sampling rationales, found {len(test_todo)}")

for spec in CONTROL_TESTS:
    check(spec.control_ref in internal_ids, f"{spec.ref} tests unknown control '{spec.control_ref}'")
    errors = validate_test(
        population_size=spec.population_size,
        sample_size=spec.sample_size,
        sample_selection_method=SampleSelectionMethod(spec.method),
        sampling_rationale=spec.sampling_rationale,
        exceptions_count=spec.exceptions_count,
        conclusion=TestConclusion(spec.conclusion),
        exception_details=spec.exception_details,
        tester=spec.tester,
        reviewed_by=spec.reviewed_by,
        period_covered_start=spec.period_start,
        period_covered_end=spec.period_end,
    )
    check(not errors, f"{spec.ref}: {errors[0].message if errors else ''}")

    needs = requires_finding(TestConclusion(spec.conclusion))
    check(
        needs == (spec.finding_ref is not None),
        f"{spec.ref} concluded {spec.conclusion} but "
        f"{'raises no finding' if needs else 'links a finding anyway'}",
    )
    if spec.finding_ref:
        check(spec.finding_ref in finding_refs, f"{spec.ref} links unknown finding")
    unknown_ev = set(spec.evidence) - evidence_refs
    check(not unknown_ev, f"{spec.ref} links unknown evidence: {sorted(unknown_ev)}")
    if TODO not in spec.sampling_rationale:
        check(
            len(spec.sampling_rationale.split()) >= 20,
            f"{spec.ref} sampling rationale is too thin to defend",
        )

# The control library rating must match the worst outstanding test on that control.
tests_by_control: dict[str, list] = {}
for spec in CONTROL_TESTS:
    tests_by_control.setdefault(spec.control_ref, []).append(spec)
for control_ref, specs in tests_by_control.items():
    worst = min(specs, key=lambda s: ["FAIL", "PASS_WITH_EXCEPTIONS", "PASS"].index(s.conclusion))
    expected = CONCLUSION_TO_OPERATING[TestConclusion(worst.conclusion)]
    _design, operating, _ = EFFECTIVENESS[control_ref]
    check(
        OperatingEffectiveness(operating) == expected,
        f"{control_ref} is rated {operating} but its worst test ({worst.ref}) implies "
        f"{expected.value}",
    )

# --- Findings and ISMS records -------------------------------------------------------
for finding in AUDIT_FINDINGS:
    check(bool(finding.remediation), f"{finding.ref} has no remediation; a finding without a plan")
    unknown_rem = set(finding.remediation) - remediation_refs
    check(not unknown_rem, f"{finding.ref} links unknown remediation: {sorted(unknown_rem)}")
    if finding.control_ref:
        check(
            finding.control_ref in internal_ids,
            f"{finding.ref} references unknown control '{finding.control_ref}'",
        )

for audit in INTERNAL_AUDITS:
    check(
        len(audit.independence_note.split()) >= 25,
        f"{audit.ref} independence note is too thin -- Clause 9.2.2 c) needs a real basis",
    )
    check(audit.planned_end >= audit.planned_start, f"{audit.ref} planned end precedes start")

for review in MANAGEMENT_REVIEWS:
    for marker in ("(a)", "(b)", "(c)", "(d)", "(e)", "(f)"):
        check(
            marker in review.inputs_considered,
            f"{review.ref} does not record Clause 9.3.2 input {marker}",
        )

for nc in NONCONFORMITIES:
    check(bool(nc.immediate_correction), f"{nc.ref} records no immediate correction")
    if nc.status == "CLOSED":
        # Clause 10.2 d): closure requires evidence the corrective action worked.
        check(
            bool(nc.effectiveness_check_result),
            f"{nc.ref} is closed with no effectiveness check result",
        )
        check(bool(nc.root_cause_analysis), f"{nc.ref} is closed with no root cause analysis")
        check(bool(nc.corrective_action), f"{nc.ref} is closed with no corrective action")
    if nc.finding_ref:
        check(nc.finding_ref in finding_refs, f"{nc.ref} links unknown finding")

conclusions = Counter(t.conclusion for t in CONTROL_TESTS)

# --- Assets, acceptance, GDPR and continuity ------------------------------------------
asset_refs = {a.ref for a in ASSETS}
check(len(asset_refs) == len(ASSETS), "Duplicate asset references")

risk_owner = {r.risk_ref: r.owner_role for r in RISKS}
exception_states: list[str] = []
for spec in RISK_EXCEPTIONS:
    check(spec.risk_ref in risk_owner, f"{spec.ref} references unknown risk '{spec.risk_ref}'")
    if spec.risk_ref not in risk_owner:
        continue
    errors = validate_exception(
        approver_role=spec.approver_role,
        risk_owner_role=risk_owner[spec.risk_ref],
        expiry_date=spec.expiry_date,
        approval_date=spec.approval_date,
        business_justification=spec.business_justification,
        review_trigger=spec.review_trigger,
        status=ExceptionStatus(spec.status),
    )
    check(not errors, f"{spec.ref}: {errors[0].message if errors else ''}")
    check(
        len(spec.business_justification.split()) >= 25,
        f"{spec.ref} business justification is too thin to defend",
    )
    exception_states.append(exception_state(spec.expiry_date, ExceptionStatus(spec.status), AS_OF))

check(
    "EXPIRED" in exception_states,
    "The acceptance register has no expired entry -- expiry handling is untested by the data",
)

ropa_refs = {r.ref for r in ROPA_ENTRIES}
check(len(ROPA_ENTRIES) == 6, f"Expected 6 RoPA entries, found {len(ROPA_ENTRIES)}")
for spec in ROPA_ENTRIES:
    errors = validate_ropa(
        transfers_outside_eea=spec.transfers_outside_eea,
        transfer_safeguard=TransferSafeguard(spec.transfer_safeguard),
        transfer_detail=spec.transfer_detail,
        retention_period=spec.retention_period,
        lawful_basis=LawfulBasis(spec.lawful_basis),
        legitimate_interests_assessment=spec.legitimate_interests_assessment,
    )
    check(not errors, f"{spec.ref}: {errors[0].message if errors else ''}")
    for label, refs, known in (
        ("asset", spec.assets, asset_refs),
        ("risk", spec.risks, set(risk_refs)),
        ("control", spec.controls, internal_ids),
    ):
        unknown_links = set(refs) - known
        check(not unknown_links, f"{spec.ref} links unknown {label}(s): {sorted(unknown_links)}")

check(len(DPIAS) == 2, f"Expected 2 DPIAs, found {len(DPIAS)}")
for spec in DPIAS:
    errors = validate_dpia(
        outcome=DpiaOutcome(spec.outcome),
        residual_risk=ResidualRiskLevel(spec.residual_risk),
        dpo_consulted=spec.dpo_consulted,
        supervisory_authority_consulted=spec.supervisory_authority_consulted,
        mitigating_measures=spec.mitigating_measures,
        review_date=spec.review_date,
    )
    check(not errors, f"{spec.ref}: {errors[0].message if errors else ''}")
    if spec.ropa_ref:
        check(spec.ropa_ref in ropa_refs, f"{spec.ref} references unknown RoPA '{spec.ropa_ref}'")
    unknown_links = set(spec.assets) - asset_refs
    check(not unknown_links, f"{spec.ref} links unknown assets: {sorted(unknown_links)}")
    unknown_links = set(spec.risks) - set(risk_refs)
    check(not unknown_links, f"{spec.ref} links unknown risks: {sorted(unknown_links)}")

check(len(BIA_PROCESSES) == 5, f"Expected 5 BIA processes, found {len(BIA_PROCESSES)}")
for spec in BIA_PROCESSES:
    errors = validate_bia(
        rto_hours=spec.rto_hours, rpo_hours=spec.rpo_hours, mtpd_hours=spec.mtpd_hours
    )
    check(not errors, f"{spec.ref}: {errors[0].message if errors else ''}")
    check(
        spec.impact_1w >= spec.impact_24h >= spec.impact_1h,
        f"{spec.ref} financial impact does not increase with outage duration",
    )
    for label, refs, known in (
        ("asset", spec.assets, asset_refs),
        ("control", spec.controls, internal_ids),
        ("risk", spec.risks, set(risk_refs)),
    ):
        unknown_links = set(refs) - known
        check(not unknown_links, f"{spec.ref} links unknown {label}(s): {sorted(unknown_links)}")

# --- Report ----------------------------------------------------------------
print(f"Annex A controls      : {len(ANNEX_A_CONTROLS)}  {dict(sorted(theme_counts.items()))}")
print(f"Provisional exclusions: {len(PROVISIONAL_EXCLUSIONS)}  {sorted(PROVISIONAL_EXCLUSIONS)}")
print(f"SOC 2 criteria        : {len(TSC_CRITERIA)}  ({len(common_criteria)} Common Criteria)")
print(f"Elected TSC criteria  : {len(elected_refs)}")
print(f"ISO -> SOC 2 mappings : {len(ISO_TO_SOC2)}  covering {len(mapped_iso)} ISO controls")
if unmapped:
    print(f"In-scope but unmapped : {unmapped}")
print(f"Internal controls     : {len(INTERNAL_CONTROLS)}")
print(f"Appetite thresholds   : {len(APPETITE_THRESHOLDS)}")
print(f"Risks                 : {len(RISKS)}")
print(f"Above appetite        : {len(breaching)}  {breaching}")
print(f"Risk justifications TODO: {len(todo_risks)}  {todo_risks}")
print(f"Evidence artifacts    : {len(EVIDENCE)}  ({len(expired_evidence)} expired: {expired_evidence})")
print(f"Remediation items     : {len(REMEDIATION_ITEMS)}  ({len(open_remediation)} open, {len(overdue)} overdue: {overdue})")
print(f"SoA entries           : {len(SOA_ENTRIES)}  ({len(applicable_entries)} applicable, {len(soa_excluded)} excluded)")
print(f"SoA implemented       : {len(implemented_entries)} of {len(applicable_entries)} applicable = {percent_implemented}%")
print(f"SoA gaps              : {len(soa_gaps)}")
print(f"SoA justifications TODO: {len(soa_todo)}  {soa_todo}")
print(f"Control tests         : {len(CONTROL_TESTS)}  {dict(conclusions)}")
print(f"Test rationales TODO  : {len(test_todo)}  {test_todo}")
print(f"Audit findings        : {len(AUDIT_FINDINGS)}")
print(
    f"Design deficient      : "
    f"{sorted(k for k, v in EFFECTIVENESS.items() if v[0] == 'DEFICIENT')}"
)
print(
    f"Never tested          : "
    f"{sorted(k for k, v in EFFECTIVENESS.items() if v[1] == 'NOT_TESTED')}"
)
print(
    f"ISMS records          : {len(INTERNAL_AUDITS)} audits, "
    f"{len(MANAGEMENT_REVIEWS)} reviews, {len(NONCONFORMITIES)} nonconformities"
)
print(f"Assets                : {len(ASSETS)}")
print(f"Risk exceptions       : {len(RISK_EXCEPTIONS)}  {dict(Counter(exception_states))}")
print(
    f"RoPA entries          : {len(ROPA_ENTRIES)}  "
    f"({sum(1 for r in ROPA_ENTRIES if r.transfers_outside_eea)} with third-country transfers)"
)
print(
    f"DPIAs                 : {len(DPIAS)}  "
    f"({sum(1 for d in DPIAS if d.residual_risk == 'HIGH')} high residual)"
)
print(f"BIA processes         : {len(BIA_PROCESSES)}")

if failures:
    print(f"\nFAILED ({len(failures)}):")
    for failure in failures:
        print(f"  - {failure}")
    sys.exit(1)

print("\nAll seed-data checks passed.")
