"""Controlled context builders.

The lazy way to give a model context is to hand it the database. That is wrong here for
three separate reasons, and each on its own would be enough:

1. **Privacy.** The ISMS holds RoPA entries, DPIA findings and a business impact
   analysis with revenue figures in it. None of that belongs in a prompt about whether
   a control test needs a follow-up question.
2. **Security.** Password hashes and configuration live in the same database. A
   whole-database context is one refactor away from putting them in a prompt.
3. **Quality.** A model given everything answers about the wrong thing. The most
   reliable way to get a useful suggestion about RISK-004 is to send RISK-004 and the
   things RISK-004 actually depends on.

So context is assembled per task, from an explicit list of fields, by a function whose
whole job is to decide what is relevant. Every builder returns the same shape, and that
shape carries the list of what was included — which is what the UI renders under
"Based on", and what makes the suggestion reviewable rather than magic.
"""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.audit import AuditFinding, ControlTest, ControlTestEvidenceLink
from app.models.framework import Framework, FrameworkControl
from app.models.risk import Control, ControlAnnexALink, Risk, RiskAppetiteThreshold, RiskControl
from app.models.soa import RemediationItem, SoAEntry
from app.services.ai.guardrails import fence, neutralise, scrub
from app.services.ai.provider import AiError
from app.services.risk_scoring import CATEGORY_LABELS

# The seeded ISO/IEC 27001:2022 framework row. Named here rather than imported from
# the seed package, because a service must not depend on the loader that populated
# the database; a test asserts the catalogue lookup actually returns 93 rows, which
# is what would catch this constant going stale.
ISO_FRAMEWORK_CODE = "ISO27001_2022"

# Per-field ceiling. A single description should not be able to crowd out the rest of
# the record; the whole-context ceiling is applied separately and is configurable.
FIELD_MAX_CHARS = 1_500


class ContextNotFound(AiError):
    """The record the request named does not exist. Surfaces as a 404."""


@dataclass(frozen=True)
class ContextItem:
    """One line of "here is what the model was given", for the explainability panel."""

    label: str
    value: str


@dataclass(frozen=True)
class RecordContext:
    entity_type: str | None
    entity_ref: str | None
    headline: str
    items: list[ContextItem] = field(default_factory=list)
    # label -> body. Rendered into the fenced data block in insertion order.
    sections: dict[str, str] = field(default_factory=dict)

    def render(self, *, max_chars: int) -> str:
        """The fenced data block that goes into the user message.

        Truncation is reported inside the prompt rather than done silently, so a model
        working from a clipped record can say its information was incomplete instead of
        confidently answering from half a record.
        """
        blocks: list[str] = []
        used = 0
        for label, body in self.sections.items():
            cleaned = neutralise(body, max_chars=FIELD_MAX_CHARS * 6)
            if used + len(cleaned) > max_chars:
                remaining = max(0, max_chars - used)
                if remaining > 200:
                    blocks.append(fence(label, cleaned[:remaining]))
                blocks.append(
                    "[Context truncated: the remaining record sections exceeded the "
                    "configured context limit. Treat your information as incomplete.]"
                )
                break
            blocks.append(fence(label, cleaned))
            used += len(cleaned)
        return "\n\n".join(blocks)


def _kv(pairs: list[tuple[str, object]]) -> str:
    """Render a record as labelled lines. Deliberately not JSON: a model asked to read
    JSON and emit JSON has a habit of echoing the input structure back."""
    lines = []
    for label, value in pairs:
        if value is None or value == "":
            lines.append(f"{label}: not recorded")
        else:
            lines.append(f"{label}: {neutralise(str(value), max_chars=FIELD_MAX_CHARS)}")
    return "\n".join(lines)


# --- Risk ---------------------------------------------------------------------


def _risk_query():
    return select(Risk).options(
        selectinload(Risk.control_links)
        .selectinload(RiskControl.control)
        .selectinload(Control.annex_a_links)
        .selectinload(ControlAnnexALink.framework_control)
    )


def load_risk(db: Session, risk_ref: str) -> Risk:
    risk = db.scalar(_risk_query().where(Risk.risk_ref == risk_ref.strip().upper()))
    if risk is None:
        raise ContextNotFound(f"Unknown risk '{risk_ref}'")
    return risk


def risk_context(db: Session, risk_ref: str) -> RecordContext:
    """Everything an assistant needs about one risk, and nothing else.

    The linked controls carry their *basis* and the control library's own effectiveness
    ratings, because without them a model will happily suggest that an untested control
    reduces residual risk -- which is the single rule this application exists to enforce.
    """
    risk = load_risk(db, risk_ref)
    threshold = db.scalar(
        select(RiskAppetiteThreshold).where(RiskAppetiteThreshold.category == risk.category)
    )
    exceeds = risk.exceeds(threshold)

    core = _kv(
        [
            ("Reference", risk.risk_ref),
            ("Title", risk.title),
            ("Category", CATEGORY_LABELS[risk.category]),
            ("Owner role", risk.owner_role),
            ("Status", risk.status.value),
            ("Description", risk.description),
            ("Asset at risk", risk.asset),
            ("Threat", risk.threat),
            ("Vulnerability", risk.vulnerability),
            (
                "Inherent assessment",
                f"likelihood {risk.inherent_likelihood} x impact {risk.inherent_impact} "
                f"= {risk.inherent_score} ({risk.inherent_band.value})",
            ),
            (
                "Residual assessment",
                f"likelihood {risk.residual_likelihood} x impact {risk.residual_impact} "
                f"= {risk.residual_score} ({risk.residual_band.value})",
            ),
            ("Residual justification recorded by the analyst", risk.residual_justification),
            ("Treatment decision", risk.treatment_decision.value),
            ("Treatment summary", risk.treatment_summary),
            (
                "Category risk appetite",
                (
                    f"maximum acceptable band {threshold.max_acceptable_band.value}, "
                    f"set by the {threshold.approver_role}"
                )
                if threshold
                else "no appetite threshold is defined for this category",
            ),
            (
                "Against appetite",
                "above appetite"
                if exceeds
                else ("within appetite" if exceeds is False else "cannot be determined"),
            ),
            ("Date identified", risk.date_identified),
            ("Last reviewed", risk.last_reviewed),
            ("Next review", risk.next_review),
        ]
    )

    control_lines = []
    for link in sorted(risk.control_links, key=lambda item: item.control.control_id):
        control = link.control
        control_lines.append(
            _kv(
                [
                    ("Control", f"{control.control_id} — {control.title}"),
                    ("Control family", control.control_family),
                    ("Control owner", control.owner_role),
                    ("Annex A references", ", ".join(control.annex_a_refs) or "none recorded"),
                    ("Recorded effectiveness basis on this risk", link.effectiveness_basis.value),
                    (
                        "May this control be credited with a residual reduction",
                        "yes" if link.credits_reduction else "no",
                    ),
                    ("Control library design effectiveness", control.design_effectiveness.value),
                    (
                        "Control library operating effectiveness",
                        control.operating_effectiveness.value,
                    ),
                    ("Last tested", control.last_tested),
                    ("Note on the link", link.note),
                ]
            )
        )

    items = [
        ContextItem("Risk record", f"{risk.risk_ref} — {risk.title}"),
        ContextItem(
            "Assessment",
            f"inherent {risk.inherent_score} ({risk.inherent_band.value}), "
            f"residual {risk.residual_score} ({risk.residual_band.value})",
        ),
        ContextItem(
            "Linked controls",
            ", ".join(link.control.control_id for link in risk.control_links) or "none",
        ),
        ContextItem(
            "Appetite",
            f"{threshold.max_acceptable_band.value} ceiling for "
            f"{CATEGORY_LABELS[risk.category]}"
            if threshold
            else "no threshold defined",
        ),
    ]

    sections = {"risk record": core}
    if control_lines:
        sections["controls linked to this risk"] = "\n\n".join(control_lines)

    return RecordContext(
        entity_type="RISK",
        entity_ref=risk.risk_ref,
        headline=f"{risk.risk_ref} — {risk.title}",
        items=items,
        sections=sections,
    )


# --- Annex A catalogue --------------------------------------------------------


def annex_a_catalogue(db: Session) -> tuple[str, dict[str, str]]:
    """The real ISO/IEC 27001:2022 Annex A list, rendered for a prompt.

    Supplied in full for control mapping. The alternative -- asking the model to recall
    Annex A from training -- reliably produces 2013 identifiers, because there is an
    enormous amount of 2013 text in the world and comparatively little 2022 text.
    Giving it the actual catalogue turns recall into selection.

    Returns the rendered block and a ``{ref: title}`` map used afterwards to check that
    every identifier the model returned is one that was actually offered to it.
    """
    rows = db.scalars(
        select(FrameworkControl)
        .join(Framework)
        .where(Framework.code == ISO_FRAMEWORK_CODE, FrameworkControl.control_ref.like("A.%"))
        .order_by(FrameworkControl.sort_order)
    ).all()
    catalogue = {row.control_ref: row.title for row in rows}
    rendered = "\n".join(f"{ref} {title}" for ref, title in catalogue.items())
    return rendered, catalogue


def control_mapping_context(db: Session, risk_ref: str) -> tuple[RecordContext, dict[str, str]]:
    """Risk context plus the Annex A catalogue and what the SoA already says.

    The SoA state matters: a suggestion to "consider A.8.5" is not useful when A.8.5 is
    already applicable, already linked to this risk and already has a remediation item
    against it. Including the current position turns the answer from a list of controls
    into a list of controls the analyst has not already considered.
    """
    base = risk_context(db, risk_ref)
    rendered, catalogue = annex_a_catalogue(db)

    risk = load_risk(db, risk_ref)
    already = sorted(
        {ref for link in risk.control_links for ref in link.control.annex_a_refs}
    )

    soa_rows = db.scalars(
        select(SoAEntry).where(SoAEntry.control_ref.in_(already))
    ).all() if already else []
    soa_lines = [
        f"{row.control_ref}: "
        f"{'applicable' if row.applicable else 'excluded'}, "
        f"{row.implementation_status.value}, owner {row.owner}"
        for row in sorted(soa_rows, key=lambda r: r.control_ref)
    ]

    sections = dict(base.sections)
    sections["annex a controls already linked to this risk"] = (
        "\n".join(soa_lines) if soa_lines else "None. No Annex A control is linked to this risk yet."
    )
    sections["iso iec 27001 2022 annex a catalogue (the only valid identifiers)"] = rendered

    items = [
        *base.items,
        ContextItem("Annex A catalogue", f"{len(catalogue)} controls, ISO/IEC 27001:2022"),
        ContextItem("Already linked", ", ".join(already) or "none"),
    ]
    return (
        RecordContext(
            entity_type=base.entity_type,
            entity_ref=base.entity_ref,
            headline=base.headline,
            items=items,
            sections=sections,
        ),
        catalogue,
    )


# --- Control test -------------------------------------------------------------


def _test_query():
    return select(ControlTest).options(
        selectinload(ControlTest.control),
        selectinload(ControlTest.linked_finding),
        selectinload(ControlTest.evidence_links).selectinload(ControlTestEvidenceLink.evidence),
    )


def load_test(db: Session, test_ref: str) -> ControlTest:
    test = db.scalar(_test_query().where(ControlTest.test_ref == test_ref.strip().upper()))
    if test is None:
        raise ContextNotFound(f"Unknown control test '{test_ref}'")
    return test


def control_test_context(db: Session, test_ref: str) -> RecordContext:
    """One workpaper, its control, and the evidence it rests on.

    Evidence is described, not reproduced: reference, title, type, source system and
    validity window. The artifacts themselves are not in this database and are not sent
    anywhere -- which is also why the assistant is told it cannot examine evidence, only
    reason about how it was described.
    """
    test = load_test(db, test_ref)
    control = test.control

    core = _kv(
        [
            ("Reference", test.test_ref),
            ("Control tested", f"{control.control_id} — {control.title}"),
            ("Control description", control.description),
            ("Control owner", control.owner_role),
            ("Tester", test.tester),
            ("Test date", test.test_date),
            ("Period covered", f"{test.period_covered_start} to {test.period_covered_end}"),
            ("Objective", test.test_objective),
            ("Procedure performed", test.test_procedure),
            ("Population description", test.population_description),
            ("Population size", test.population_size),
            ("Sample size", test.sample_size),
            ("Sample selection method", test.sample_selection_method.value),
            ("Sampling rationale", test.sampling_rationale),
            ("Results summary", test.results_summary),
            ("Exceptions found", test.exceptions_count),
            ("Exception detail", test.exception_details),
            ("Conclusion recorded by the tester", test.conclusion.value),
            ("Reviewed by", test.reviewed_by),
            ("Review date", test.review_date),
            (
                "Linked finding",
                test.linked_finding.finding_ref if test.linked_finding else None,
            ),
            ("Control library design effectiveness", control.design_effectiveness.value),
            ("Control library operating effectiveness", control.operating_effectiveness.value),
        ]
    )

    evidence_lines = [
        _kv(
            [
                ("Evidence reference", item.evidence_ref),
                ("Title", item.title),
                ("Description", item.description),
                ("Type", item.evidence_type.value),
                ("Source system", item.source_system),
                ("Collected by", item.collected_by),
                ("Collected", item.collected_date),
                ("Valid from", item.valid_from),
                ("Valid until", item.valid_until),
            ]
        )
        for item in test.linked_evidence
    ]

    sections = {"control test workpaper": core}
    sections["evidence linked to this test (descriptions only; the artifacts themselves "
             "are not available to you)"] = (
        "\n\n".join(evidence_lines) if evidence_lines else "No evidence is linked to this test."
    )

    return RecordContext(
        entity_type="CONTROL_TEST",
        entity_ref=test.test_ref,
        headline=f"{test.test_ref} — {control.control_id} {control.title}",
        items=[
            ContextItem("Workpaper", f"{test.test_ref} against {control.control_id}"),
            ContextItem(
                "Sampling",
                f"{test.sample_size} of {test.population_size}, "
                f"{test.sample_selection_method.value.lower().replace('_', ' ')}",
            ),
            ContextItem(
                "Result",
                f"{test.exceptions_count} exception(s), concluded {test.conclusion.value}",
            ),
            ContextItem(
                "Evidence",
                ", ".join(item.evidence_ref for item in test.linked_evidence) or "none linked",
            ),
        ],
        sections=sections,
    )


# --- Findings and remediation --------------------------------------------------


def _finding_query():
    return select(AuditFinding).options(selectinload(AuditFinding.control))


def load_finding(db: Session, finding_ref: str) -> AuditFinding:
    finding = db.scalar(
        _finding_query().where(AuditFinding.finding_ref == finding_ref.strip().upper())
    )
    if finding is None:
        raise ContextNotFound(f"Unknown finding '{finding_ref}'")
    return finding


def finding_draft_context(db: Session, test_ref: str) -> RecordContext:
    """A finding is drafted from the test that produced it, not from thin air.

    This is why the input is a test reference rather than free text: the workflow in
    this application is test → draft finding → human review → final finding, and a
    draft that was not derived from a workpaper has skipped the first step.
    """
    base = control_test_context(db, test_ref)
    test = load_test(db, test_ref)
    existing = test.linked_finding

    sections = dict(base.sections)
    if existing:
        sections["finding already raised from this test"] = _kv(
            [
                ("Reference", existing.finding_ref),
                ("Title", existing.title),
                ("Description", existing.description),
                ("Severity", existing.severity.value),
                ("Status", existing.status.value),
                ("Owner", existing.owner),
            ]
        )

    return RecordContext(
        entity_type="CONTROL_TEST",
        entity_ref=test.test_ref,
        headline=base.headline,
        items=[
            *base.items,
            ContextItem(
                "Existing finding",
                existing.finding_ref if existing else "none raised from this test yet",
            ),
        ],
        sections=sections,
    )


def remediation_context(db: Session, finding_ref: str) -> RecordContext:
    """A finding, its control, and any remediation already planned against it."""
    finding = load_finding(db, finding_ref)
    control = finding.control

    core = _kv(
        [
            ("Reference", finding.finding_ref),
            ("Title", finding.title),
            ("Description", finding.description),
            ("Severity", finding.severity.value),
            ("Status", finding.status.value),
            ("Source", finding.source.value),
            ("Identified", finding.identified_date),
            ("Identified by", finding.identified_by),
            ("Owner", finding.owner),
            (
                "Control concerned",
                f"{control.control_id} — {control.title}" if control else None,
            ),
            ("Control description", control.description if control else None),
            ("Control owner", control.owner_role if control else None),
            (
                "Control library design effectiveness",
                control.design_effectiveness.value if control else None,
            ),
            (
                "Control library operating effectiveness",
                control.operating_effectiveness.value if control else None,
            ),
        ]
    )

    planned = db.scalars(
        select(RemediationItem).where(
            RemediationItem.id.in_(
                [link.remediation_id for link in finding.remediation_links] or [-1]
            )
        )
    ).all()
    planned_lines = [
        _kv(
            [
                ("Reference", item.remediation_ref),
                ("Title", item.title),
                ("Description", item.description),
                ("Owner", item.owner),
                ("Raised", item.raised_date),
                ("Due", item.due_date),
                ("Status", item.status.value),
                ("Priority", item.priority.value),
            ]
        )
        for item in sorted(planned, key=lambda item: item.remediation_ref)
    ]

    sections = {"audit finding": core}
    sections["remediation already planned against this finding"] = (
        "\n\n".join(planned_lines)
        if planned_lines
        else "No remediation item is linked to this finding yet."
    )

    return RecordContext(
        entity_type="FINDING",
        entity_ref=finding.finding_ref,
        headline=f"{finding.finding_ref} — {finding.title}",
        items=[
            ContextItem("Finding", f"{finding.finding_ref} ({finding.severity.value})"),
            ContextItem(
                "Control", f"{control.control_id} — {control.title}" if control else "none linked"
            ),
            ContextItem(
                "Existing remediation",
                ", ".join(item.remediation_ref for item in planned) or "none",
            ),
        ],
        sections=sections,
    )


# --- Policy drafting -----------------------------------------------------------


def policy_context(
    db: Session, *, topic: str, document_type: str, annex_a_refs: list[str]
) -> RecordContext:
    """Organisation facts plus, optionally, the Annex A controls the document supports.

    The scope description is included because a policy written without it produces the
    generic template that says "physical access to data centres is controlled" for a
    company with no premises. FinFlow's actual shape -- fully remote, no offices, one
    cloud region, a third-party payment processor -- is what makes a draft usable.
    """
    refs = [ref.strip().upper() for ref in annex_a_refs if ref.strip()]
    rows = (
        db.scalars(
            select(FrameworkControl)
            .join(Framework)
            .where(Framework.code == ISO_FRAMEWORK_CODE, FrameworkControl.control_ref.in_(refs))
            .order_by(FrameworkControl.sort_order)
        ).all()
        if refs
        else []
    )
    soa_rows = (
        db.scalars(select(SoAEntry).where(SoAEntry.control_ref.in_(refs))).all() if refs else []
    )
    soa_by_ref = {row.control_ref: row for row in soa_rows}

    control_lines = []
    for row in rows:
        entry = soa_by_ref.get(row.control_ref)
        control_lines.append(
            _kv(
                [
                    ("Annex A control", f"{row.control_ref} {row.title}"),
                    (
                        "Statement of Applicability position",
                        (
                            f"{'applicable' if entry.applicable else 'excluded'}, "
                            f"{entry.implementation_status.value}, owner {entry.owner}"
                        )
                        if entry
                        else "no Statement of Applicability entry found",
                    ),
                    (
                        "Recorded inclusion justification",
                        entry.justification_inclusion if entry else None,
                    ),
                ]
            )
        )

    unknown = sorted(set(refs) - {row.control_ref for row in rows})

    sections = {
        "the organisation this document is for": ORGANISATION_PROFILE,
        "what the analyst asked for": _kv(
            [
                ("Document type", document_type),
                ("Topic", topic),
                ("Annex A controls named by the analyst", ", ".join(refs) or "none"),
            ]
        ),
    }
    if control_lines:
        sections["annex a controls this document is intended to support"] = "\n\n".join(
            control_lines
        )
    if unknown:
        sections["identifiers the analyst supplied that are not in the catalogue"] = ", ".join(
            unknown
        )

    return RecordContext(
        entity_type="POLICY",
        entity_ref=None,
        headline=f"{document_type}: {topic}",
        items=[
            ContextItem("Document type", document_type),
            ContextItem("Topic", topic),
            ContextItem("Organisation profile", "FinFlow Technologies, from the ISMS scope"),
            ContextItem("Annex A controls", ", ".join(refs) or "none named"),
        ],
        sections=sections,
    )


# The scope facts, held here rather than fetched, because they are the ISMS scope
# statement and they change through a documented scope review, not through a database
# write. Copied from docs/SCOPE.md; the seed data is consistent with it.
ORGANISATION_PROFILE = """\
FinFlow Technologies is a fictional cloud-native FinTech company used for a portfolio
assessment. Nothing here has been assessed by a certification body or an audit firm.

Approximately 40 employees, fully remote, with no offices, no data centres and no
physical premises of its own.
Product: a business-to-business software-as-a-service payments platform.
Cardholder data is handled by a third-party payment service provider, not by FinFlow.
All production infrastructure runs in one AWS region, eu-west-1.
Customers are in the EU and in India, so the GDPR is in scope.
Identity and single sign-on is Okta. Source control and CI is GitHub.
Company-managed macOS laptops. Development is not outsourced.
The ISMS is pre-certification: controls are being implemented and tested, and the
Statement of Applicability records gaps openly rather than claiming coverage."""


def scrubbed(payload: dict) -> dict:
    """Convenience wrapper so callers do not have to import the guardrail module."""
    return scrub(payload)
