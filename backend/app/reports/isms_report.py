"""ISMS records export (PDF): Clause 9.2, 9.3 and 10.2.

A records export, not one of the three reports. See the docstring on
``app.api.routes.isms.isms_records_pdf`` for why that distinction is kept.
"""

from datetime import date
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
)

from app.core.config import get_settings

_INK = colors.HexColor("#1a1d24")
_MUTED = colors.HexColor("#5b6470")
_RULE = colors.HexColor("#c8cdd6")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontSize=17, leading=21, textColor=_INK,
            alignment=TA_LEFT, spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"], fontSize=9, leading=12, textColor=_MUTED,
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontSize=13, leading=16, textColor=_INK,
            spaceBefore=14, spaceAfter=4,
        ),
        "h3": ParagraphStyle(
            "h3", parent=base["Heading3"], fontSize=10.5, leading=13, textColor=_INK,
            spaceBefore=10, spaceAfter=3,
        ),
        "label": ParagraphStyle(
            "label", parent=base["Normal"], fontSize=7.5, leading=10, textColor=_MUTED,
            fontName="Helvetica-Bold", spaceBefore=5,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontSize=8.8, leading=12, textColor=_INK,
        ),
    }


def _page_furniture(canvas, doc):
    canvas.saveState()
    width, height = doc.pagesize
    canvas.setFont("Helvetica-Bold", 7)
    canvas.setFillColor(colors.HexColor("#8a6d1f"))
    canvas.drawString(16 * mm, height - 10 * mm, get_settings().data_disclaimer)
    canvas.setStrokeColor(_RULE)
    canvas.setLineWidth(0.4)
    canvas.line(16 * mm, height - 12.5 * mm, width - 16 * mm, height - 12.5 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(_MUTED)
    canvas.drawString(16 * mm, 9 * mm, "FinFlow Technologies (fictional) — ISMS records")
    canvas.drawRightString(width - 16 * mm, 9 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def _p(text, style) -> Paragraph:
    escaped = (
        str(text or "—").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    # Preserve the paragraph breaks used in the seeded clause 9.3 inputs.
    return Paragraph(escaped.replace("\n", "<br/>"), style)


def _field(label: str, value, styles) -> list:
    return [_p(label.upper(), styles["label"]), _p(value, styles["body"])]


def render_isms_records(audits, reviews, nonconformities) -> bytes:
    styles = _styles()
    buffer = BytesIO()
    doc = BaseDocTemplate(
        buffer, pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm, topMargin=17 * mm, bottomMargin=14 * mm,
        title="FinFlow Technologies — ISMS records (Clauses 9.2, 9.3, 10.2)",
        author="GRCShield (portfolio project)",
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main",
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
    )
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=_page_furniture)])

    story: list = [
        _p("ISMS records", styles["title"]),
        _p(
            "FinFlow Technologies · ISO/IEC 27001:2022 Clauses 9.2 (internal audit), "
            f"9.3 (management review) and 10.2 (nonconformity and corrective action) · "
            f"generated {date.today().isoformat()}",
            styles["subtitle"],
        ),
    ]

    story.append(_p("Clause 9.2 — Internal audit programme", styles["h2"]))
    for audit in audits:
        block = [_p(f"{audit.audit_ref} · {audit.title}", styles["h3"])]
        block += _field("Status", audit.status.value.replace("_", " ").title(), styles)
        block += _field(
            "Planned",
            f"{audit.planned_start} to {audit.planned_end}"
            + (
                f" · actual {audit.actual_start} to {audit.actual_end or 'ongoing'}"
                if audit.actual_start
                else ""
            ),
            styles,
        )
        block += _field("Scope", audit.scope, styles)
        block += _field("Objectives", audit.objectives, styles)
        block += _field("Audit criteria", audit.criteria, styles)
        block += _field("Auditor", audit.auditor, styles)
        block += _field("Independence (Clause 9.2.2 c)", audit.independence_note, styles)
        if audit.outcome_summary:
            block += _field("Outcome", audit.outcome_summary, styles)
        story.append(KeepTogether(block))
        story.append(Spacer(1, 4 * mm))

    story.append(PageBreak())
    story.append(_p("Clause 9.3 — Management review", styles["h2"]))
    for review in reviews:
        block = [_p(f"{review.review_ref} · {review.review_date}", styles["h3"])]
        block += _field("Chair", review.chair, styles)
        block += _field("Attendees", review.attendees, styles)
        block += _field("Inputs considered (Clause 9.3.2)", review.inputs_considered, styles)
        block += _field("Decisions", review.decisions, styles)
        block += _field("Actions", review.actions, styles)
        block += _field("Next review", review.next_review_date, styles)
        story.append(KeepTogether(block))
        story.append(Spacer(1, 5 * mm))

    story.append(PageBreak())
    story.append(_p("Clause 10.2 — Nonconformity and corrective action", styles["h2"]))
    story.append(
        _p(
            "Correction and corrective action are recorded separately and deliberately. A "
            "correction fixes the instance; corrective action eliminates the cause so it "
            "does not recur. Clause 10.2 requires both, plus a review of whether the action "
            "worked — which is why a nonconformity cannot be closed here without an "
            "effectiveness check result.",
            styles["body"],
        )
    )
    for nc in nonconformities:
        block = [_p(f"{nc.nc_ref} · {nc.status.value.replace('_', ' ').title()}", styles["h3"])]
        block += _field("Description", nc.description, styles)
        block += _field(
            "Identified", f"{nc.identified_date} by {nc.identified_by} · owner {nc.owner}", styles
        )
        if nc.finding:
            block += _field("Source finding", nc.finding.finding_ref, styles)
        block += _field("Correction (immediate)", nc.immediate_correction, styles)
        block += _field("Root cause analysis", nc.root_cause_analysis, styles)
        block += _field("Corrective action (eliminates the cause)", nc.corrective_action, styles)
        block += _field("Target date", nc.target_date, styles)
        block += _field(
            "Effectiveness check",
            (
                f"{nc.effectiveness_check_date}: {nc.effectiveness_check_result}"
                if nc.effectiveness_check_result
                else (
                    f"Scheduled {nc.effectiveness_check_date}"
                    if nc.effectiveness_check_date
                    else "Not yet scheduled"
                )
            ),
            styles,
        )
        if nc.closure_date:
            block += _field("Closed", nc.closure_date, styles)
        story.append(KeepTogether(block))
        story.append(Spacer(1, 5 * mm))

    story.append(Spacer(1, 6 * mm))
    story.append(
        KeepTogether([
            _p("Limitations", styles["h2"]),
            _p(
                "FinFlow Technologies is a fictional company created for a portfolio "
                "project. No certification body or audit firm has assessed this data, no "
                "audit has been performed, and all records are illustrative.",
                styles["body"],
            ),
        ])
    )

    doc.build(story)
    return buffer.getvalue()
