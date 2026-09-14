"""Executive Summary Report (PDF).

Audience: founders and the board.
Decision it supports: where to spend the next quarter of security budget and headcount.

Written for a reader who does not know what Annex A is and should not have to. No
control identifiers in the prose, no band names used as nouns, and every recommendation
says who does it and what it buys.
"""

from datetime import date
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.reports.common import (
    BAD_BG,
    GOOD_BG,
    HEADER_BG,
    RULE,
    p,
    page_furniture,
    styles,
)


def render_executive_summary(summary: dict, kris: list, as_of: date) -> bytes:
    s = styles()
    buffer = BytesIO()
    doc = BaseDocTemplate(
        buffer, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=17 * mm, bottomMargin=14 * mm,
        title="FinFlow Technologies — Executive Summary",
        author="GRCShield (portfolio project)",
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main",
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
    )
    doc.addPageTemplates([
        PageTemplate(
            id="all", frames=[frame],
            onPage=page_furniture("FinFlow Technologies (fictional) — Executive Summary"),
        )
    ])

    story: list = [
        p("Security and compliance — executive summary", s["title"]),
        p(f"FinFlow Technologies · {as_of.isoformat()}", s["subtitle"]),
        Spacer(1, 5 * mm),
        p(summary["posture_statement"], s["lead"]),
        Spacer(1, 3 * mm),
    ]

    headline = [
        ["Protections in place", "Exposures beyond agreed limits", "Carried without a decision",
         "Overdue work"],
        [
            f"{summary['safeguards_percent']}%",
            str(summary["risks_beyond_agreed_limit"]),
            str(summary["risks_carried_without_a_decision"]),
            str(summary["remediation_overdue"]),
        ],
        [
            f"{summary['safeguards_in_place']} of {summary['safeguards_required']} required",
            f"of {summary['risks_total']} tracked",
            "need a decision from a named owner",
            f"of {summary['remediation_open']} open items",
        ],
    ]
    table = Table(headline, colWidths=[43 * mm] * 4, hAlign="LEFT")
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7.5),
            ("FONTSIZE", (0, 1), (-1, 1), 17),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 2), (-1, 2), 7.5),
            ("TEXTCOLOR", (0, 2), (-1, 2), RULE),
            ("GRID", (0, 0), (-1, -1), 0.4, RULE),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    story += [table, Spacer(1, 7 * mm)]

    # --- Priorities first. This is what the reader is here for. -------------
    story.append(p("What we recommend doing next", s["h2"]))
    for index, priority in enumerate(summary["priorities"], start=1):
        story.append(
            KeepTogether([
                p(f"{index}. {priority.headline}", s["h3"]),
                p(priority.why, s["body"]),
                p(f"Owner: {priority.owner} · Target: {priority.by_when}", s["cell_muted"]),
                Spacer(1, 2 * mm),
            ])
        )

    # --- Top risks -----------------------------------------------------------
    story.append(p("The five exposures that matter most", s["h2"]))
    rows = [[p("What could go wrong", s["th"]), p("Assessment", s["th"]), p("Owner", s["th"])]]
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("GRID", (0, 0), (-1, -1), 0.35, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]
    for index, risk in enumerate(summary["top_risks"], start=1):
        note = risk.what_could_happen
        if risk.beyond_agreed_limit:
            note += " This is beyond the limit the business agreed to carry."
        rows.append([
            p(risk.plain_title, s["cell"]),
            p(note, s["cell_muted"]),
            p(risk.who_owns_it, s["cell_muted"]),
        ])
        if risk.beyond_agreed_limit:
            commands.append(("BACKGROUND", (0, index), (-1, index), BAD_BG))
    top = Table(rows, colWidths=[74 * mm, 66 * mm, 34 * mm], repeatRows=1, hAlign="LEFT")
    top.setStyle(TableStyle(commands))
    story += [top, Spacer(1, 5 * mm)]

    # --- Gaps ----------------------------------------------------------------
    story.append(p("Where the biggest protection gaps are", s["h2"]))
    gap_rows = [[
        p("Protection not yet fully in place", s["th"]),
        p("Exposures relying on it", s["th"]),
        p("Owner", s["th"]),
    ]]
    for gap in summary["top_gaps"]:
        gap_rows.append([
            p(gap["what_is_missing"], s["cell"]),
            p(str(gap["risks_depending_on_it"]), s["cell"]),
            p(gap["owner"], s["cell_muted"]),
        ])
    gaps = Table(gap_rows, colWidths=[110 * mm, 30 * mm, 34 * mm], repeatRows=1, hAlign="LEFT")
    gaps.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("GRID", (0, 0), (-1, -1), 0.35, RULE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    story += [gaps, Spacer(1, 5 * mm)]

    # --- Findings and suppliers ------------------------------------------------
    severity_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    counts = summary["open_findings_by_severity"]
    story.append(
        KeepTogether([
            p("Issues found by our own checks", s["h2"]),
            p(
                f"{summary['open_findings_total']} issues are open from internal testing: "
                + ", ".join(
                    f"{counts.get(level, 0)} {level.lower()}"
                    for level in severity_order
                    if counts.get(level, 0)
                )
                + ". Each one has an owner and a date. Finding them ourselves is the system "
                "working; leaving them open past their date is not.",
                s["body"],
            ),
        ])
    )
    story.append(
        KeepTogether([
            p("Suppliers", s["h2"]),
            p(summary["third_party"]["summary"], s["body"]),
        ])
    )

    # --- Indicators ------------------------------------------------------------
    story.append(p("The numbers we watch", s["h2"]))
    kri_rows = [[
        p("Indicator", s["th"]), p("Now", s["th"]), p("Target", s["th"]),
        p("Direction of travel", s["th"]),
    ]]
    kri_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("GRID", (0, 0), (-1, -1), 0.35, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]
    movement_words = {
        "IMPROVING": "improving", "DETERIORATING": "getting worse",
        "FLAT": "unchanged", "NO_TREND": "not enough history",
    }
    unit_suffix = {"PERCENT": "%", "DAYS": " days", "COUNT": ""}
    for index, kri in enumerate(kris, start=1):
        suffix = unit_suffix[kri.unit.value]
        now = "not measured" if kri.current_value is None else f"{kri.current_value}{suffix}"
        target = (
            f"at least {kri.green_threshold}{suffix}"
            if kri.direction.value == "HIGHER_IS_BETTER"
            else f"no more than {kri.green_threshold}{suffix}"
        )
        kri_rows.append([
            p(kri.name, s["cell"]),
            p(now, s["cell"]),
            p(target, s["cell_muted"]),
            p(movement_words[kri.movement], s["cell_muted"]),
        ])
        if kri.current_band.value == "RED":
            kri_commands.append(("BACKGROUND", (0, index), (-1, index), BAD_BG))
        elif kri.current_band.value == "GREEN":
            kri_commands.append(("BACKGROUND", (0, index), (-1, index), GOOD_BG))
    kri_table = Table(
        kri_rows, colWidths=[78 * mm, 26 * mm, 36 * mm, 34 * mm], repeatRows=1, hAlign="LEFT"
    )
    kri_table.setStyle(TableStyle(kri_commands))
    story += [kri_table, Spacer(1, 6 * mm)]

    story.append(
        KeepTogether([
            p("What this assessment is, and is not", s["h2"]),
            p(
                "FinFlow Technologies is a fictional company created for a portfolio "
                "project. No certification body or audit firm has assessed this data and no "
                "audit has been performed. Every figure is illustrative. Where a judgment "
                "has not yet been made, the record says so rather than filling the gap with "
                "something plausible.",
                s["body"],
            ),
        ])
    )

    doc.build(story)
    return buffer.getvalue()
