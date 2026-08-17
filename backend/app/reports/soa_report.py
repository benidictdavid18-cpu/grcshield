"""SoA + Gap Analysis Report (PDF).

One of the three reports GRCShield produces. Audience: a certification auditor and the
ISMS manager. The decision it supports: whether every Annex A control has a defensible
applicability decision, and where applicable-but-not-implemented controls need
remediation with an owner and a due date.

The portfolio disclaimer is stamped on every page. This is a fictional company's
assessment and the report must never be separable from that fact.
"""

from datetime import date
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
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
    Table,
    TableStyle,
)

from app.core.config import get_settings
from app.models.soa import ImplementationStatus, SoAEntry

_INK = colors.HexColor("#1a1d24")
_MUTED = colors.HexColor("#5b6470")
_RULE = colors.HexColor("#c8cdd6")
_HEADER_BG = colors.HexColor("#eceff4")
_GAP_BG = colors.HexColor("#fdf3e3")
_EXCLUDED_BG = colors.HexColor("#f2f3f5")

_STATUS_LABEL = {
    ImplementationStatus.IMPLEMENTED: "Implemented",
    ImplementationStatus.PARTIALLY_IMPLEMENTED: "Partial",
    ImplementationStatus.NOT_IMPLEMENTED: "Not implemented",
}


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontSize=18, leading=22, textColor=_INK,
            alignment=TA_LEFT, spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"], fontSize=9.5, leading=13, textColor=_MUTED,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontSize=12, leading=15, textColor=_INK,
            spaceBefore=12, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontSize=8.5, leading=11, textColor=_INK,
        ),
        "cell": ParagraphStyle(
            "cell", parent=base["Normal"], fontSize=7.2, leading=9, textColor=_INK,
        ),
        "cell_muted": ParagraphStyle(
            "cell_muted", parent=base["Normal"], fontSize=7.2, leading=9, textColor=_MUTED,
        ),
        "th": ParagraphStyle(
            "th", parent=base["Normal"], fontSize=7, leading=9, textColor=_MUTED,
            fontName="Helvetica-Bold",
        ),
    }


def _page_furniture(canvas, doc):
    canvas.saveState()
    width, height = doc.pagesize
    disclaimer = get_settings().data_disclaimer

    canvas.setFont("Helvetica-Bold", 7)
    canvas.setFillColor(colors.HexColor("#8a6d1f"))
    canvas.drawString(14 * mm, height - 10 * mm, disclaimer)

    canvas.setStrokeColor(_RULE)
    canvas.setLineWidth(0.4)
    canvas.line(14 * mm, height - 12.5 * mm, width - 14 * mm, height - 12.5 * mm)

    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(_MUTED)
    canvas.drawString(
        14 * mm, 9 * mm,
        "FinFlow Technologies (fictional) — Statement of Applicability and Gap Analysis",
    )
    canvas.drawRightString(width - 14 * mm, 9 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    escaped = (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return Paragraph(escaped, style)


def _overview_block(overview, styles, as_of: date) -> list:
    story = [
        # _p() escapes for ReportLab's mini-HTML, so pass plain text here.
        _p("Statement of Applicability & Gap Analysis", styles["title"]),
        _p(
            f"FinFlow Technologies · version {overview.version} · approved by "
            f"{overview.approved_by or 'not approved'} on "
            f"{overview.approved_date or '—'} · generated {as_of.isoformat()}",
            styles["subtitle"],
        ),
        Spacer(1, 4 * mm),
        _p(
            "Prepared against ISO/IEC 27001:2022 Annex A. Clause 6.1.3 d) requires an "
            "applicability decision and a justification for every one of the 93 controls. "
            "Percent implemented is calculated over applicable controls only — excluded "
            "controls are not in scope, so counting them either way would misstate readiness.",
            styles["body"],
        ),
        Spacer(1, 5 * mm),
    ]

    headline = [
        ["Controls", "Applicable", "Excluded", "Implemented", "Partial", "Not impl.", "% implemented"],
        [
            str(overview.total_controls), str(overview.applicable), str(overview.excluded),
            str(overview.implemented), str(overview.partially_implemented),
            str(overview.not_implemented), f"{overview.percent_implemented}%",
        ],
    ]
    table = Table(headline, colWidths=[36 * mm] * 7, hAlign="LEFT")
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), _MUTED),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7),
            ("FONTSIZE", (0, 1), (-1, 1), 13),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
            ("TEXTCOLOR", (0, 1), (-1, 1), _INK),
            ("GRID", (0, 0), (-1, -1), 0.4, _RULE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story += [table, Spacer(1, 6 * mm)]

    quality = [
        ["Assurance quality signals", ""],
        ["Gaps (applicable, not fully implemented)", str(overview.gaps)],
        ["Open remediation items", str(overview.open_remediation)],
        ["Overdue remediation items", str(overview.overdue_remediation)],
        ["Implemented controls carrying no evidence", str(overview.implemented_without_evidence)],
        ["Expired evidence artifacts", str(overview.expired_evidence)],
        ["Justifications outstanding (author to complete)", str(overview.justifications_outstanding)],
    ]
    quality_table = Table(quality, colWidths=[90 * mm, 25 * mm], hAlign="LEFT")
    quality_table.setStyle(
        TableStyle([
            ("SPAN", (0, 0), (1, 0)),
            ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, _RULE),
            ("ALIGN", (1, 1), (1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story += [quality_table, Spacer(1, 6 * mm)]

    theme_rows = [["Theme", "Total", "Applicable", "Excluded", "Implemented", "Partial", "Not impl."]]
    for theme in overview.themes:
        theme_rows.append([
            f"{theme.theme} {theme.theme_title}", str(theme.total), str(theme.applicable),
            str(theme.excluded), str(theme.implemented), str(theme.partially_implemented),
            str(theme.not_implemented),
        ])
    theme_table = Table(theme_rows, colWidths=[70 * mm] + [22 * mm] * 6, hAlign="LEFT")
    theme_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, _RULE),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story += [_p("Coverage by theme", styles["h2"]), theme_table]
    return story


def _soa_table(entries: list[SoAEntry], styles, as_of: date) -> Table:
    header = [
        _p("Control", styles["th"]), _p("Title", styles["th"]),
        _p("Applicable", styles["th"]), _p("Status", styles["th"]),
        _p("Justification", styles["th"]), _p("Linked risks", styles["th"]),
        _p("Evidence", styles["th"]), _p("Remediation", styles["th"]),
        _p("Owner", styles["th"]),
    ]
    rows = [header]
    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("GRID", (0, 0), (-1, -1), 0.35, _RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]

    for index, entry in enumerate(entries, start=1):
        justification = (
            entry.justification_inclusion if entry.applicable else entry.justification_exclusion
        ) or ""
        risks = ", ".join(risk.risk_ref for risk in entry.linked_risks) or "—"
        evidence_parts = []
        for item in entry.linked_evidence:
            evidence_parts.append(
                f"{item.evidence_ref} (expired)" if item.is_expired(as_of) else item.evidence_ref
            )
        remediation_parts = []
        for item in entry.linked_remediation:
            suffix = " (overdue)" if item.is_overdue(as_of) else ""
            if item.status.value == "COMPLETED":
                suffix = " (done)"
            remediation_parts.append(f"{item.remediation_ref}{suffix}")

        rows.append([
            _p(entry.control_ref, styles["cell"]),
            _p(entry.control_title, styles["cell"]),
            _p("Yes" if entry.applicable else "No", styles["cell"]),
            _p(_STATUS_LABEL[entry.implementation_status], styles["cell"]),
            _p(justification, styles["cell_muted"]),
            _p(risks, styles["cell"]),
            _p(", ".join(evidence_parts) or "—", styles["cell"]),
            _p(", ".join(remediation_parts) or "—", styles["cell"]),
            _p(entry.owner, styles["cell_muted"]),
        ])

        if not entry.applicable:
            style_commands.append(("BACKGROUND", (0, index), (-1, index), _EXCLUDED_BG))
        elif entry.is_gap:
            style_commands.append(("BACKGROUND", (0, index), (-1, index), _GAP_BG))

    widths = [14 * mm, 46 * mm, 14 * mm, 20 * mm, 78 * mm, 22 * mm, 26 * mm, 26 * mm, 24 * mm]
    table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle(style_commands))
    return table


def _gap_section(entries: list[SoAEntry], styles, as_of: date) -> list:
    gaps = [entry for entry in entries if entry.is_gap]
    story = [
        _p("Gap analysis", styles["h2"]),
        _p(
            f"{len(gaps)} applicable controls are not fully implemented. Each carries at "
            "least one remediation item with a named owner and a due date — that linkage is "
            "enforced by the application and cannot be bypassed.",
            styles["body"],
        ),
        Spacer(1, 3 * mm),
    ]

    rows = [[
        _p("Control", styles["th"]), _p("Status", styles["th"]),
        _p("What is missing", styles["th"]), _p("Remediation", styles["th"]),
        _p("Owner", styles["th"]), _p("Due", styles["th"]),
    ]]
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("GRID", (0, 0), (-1, -1), 0.35, _RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]

    for index, entry in enumerate(gaps, start=1):
        live = [item for item in entry.linked_remediation if item.is_open]
        overdue = any(item.is_overdue(as_of) for item in live)
        rows.append([
            _p(entry.control_ref, styles["cell"]),
            _p(_STATUS_LABEL[entry.implementation_status], styles["cell"]),
            _p(entry.implementation_description or "—", styles["cell_muted"]),
            _p(", ".join(item.remediation_ref for item in live) or "—", styles["cell"]),
            _p(", ".join(sorted({item.owner for item in live})) or "—", styles["cell"]),
            _p(
                ", ".join(item.due_date.isoformat() for item in live) or "—",
                styles["cell"],
            ),
        ])
        if overdue:
            commands.append(("BACKGROUND", (0, index), (-1, index), _GAP_BG))

    table = Table(
        rows, colWidths=[16 * mm, 22 * mm, 108 * mm, 30 * mm, 44 * mm, 50 * mm],
        repeatRows=1, hAlign="LEFT",
    )
    table.setStyle(TableStyle(commands))
    story.append(table)
    return story


def render_soa_gap_report(entries: list[SoAEntry], overview, as_of: date) -> bytes:
    """Render the report and return PDF bytes."""
    styles = _styles()
    buffer = BytesIO()

    pagesize = landscape(A4)
    doc = BaseDocTemplate(
        buffer, pagesize=pagesize,
        leftMargin=14 * mm, rightMargin=14 * mm, topMargin=17 * mm, bottomMargin=14 * mm,
        title="FinFlow Technologies — Statement of Applicability and Gap Analysis",
        author="GRCShield (portfolio project)",
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main",
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
    )
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=_page_furniture)])

    story: list = []
    story += _overview_block(overview, styles, as_of)
    story.append(PageBreak())
    story.append(_p("Statement of Applicability — all 93 Annex A controls", styles["h2"]))
    story.append(
        _p(
            "Shaded rows are gaps (applicable, not fully implemented). Grey rows are "
            "excluded controls; each exclusion states where the risk went.",
            styles["body"],
        )
    )
    story.append(Spacer(1, 3 * mm))
    story.append(_soa_table(entries, styles, as_of))
    story.append(PageBreak())
    story += _gap_section(entries, styles, as_of)

    story.append(Spacer(1, 8 * mm))
    story.append(
        KeepTogether([
            _p("Limitations", styles["h2"]),
            _p(
                "FinFlow Technologies is a fictional company created for a portfolio "
                "project. No certification body or audit firm has assessed this data, no "
                "audit has been performed, and all ratings are illustrative. Several "
                "justifications are marked TODO AUTHOR:BENNY and are deliberately "
                "incomplete pending the author's own analysis.",
                styles["body"],
            ),
        ])
    )

    doc.build(story)
    return buffer.getvalue()
