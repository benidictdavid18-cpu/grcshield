"""Risk Register Report (PDF).

Audience: risk owners and the management review meeting.
Decision it supports: which risks exceed their category appetite and therefore need a
treatment decision or a formal, time-boxed acceptance.

The register is sorted by residual score descending, because the meeting only ever gets
through the top of the list.
"""

from datetime import date
from io import BytesIO

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.reports.common import (
    ALERT_BG,
    BAD_BG,
    HEADER_BG,
    RULE,
    p,
    page_furniture,
    styles,
)
from app.services.privacy_continuity import ExceptionStatus, exception_state
from app.services.risk_scoring import CATEGORY_LABELS

_TREATMENT = {
    "MITIGATE": "Mitigate", "ACCEPT": "Accept", "TRANSFER": "Transfer", "AVOID": "Avoid",
}


def render_risk_register(risks, thresholds, exceptions, as_of: date) -> bytes:
    s = styles()
    buffer = BytesIO()
    pagesize = landscape(A4)
    doc = BaseDocTemplate(
        buffer, pagesize=pagesize,
        leftMargin=16 * mm, rightMargin=16 * mm, topMargin=17 * mm, bottomMargin=14 * mm,
        title="FinFlow Technologies — Risk Register Report",
        author="GRCShield (portfolio project)",
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main",
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
    )
    doc.addPageTemplates([
        PageTemplate(
            id="all", frames=[frame],
            onPage=page_furniture("FinFlow Technologies (fictional) — Risk Register Report"),
        )
    ])

    ordered = sorted(risks, key=lambda r: r.residual_score, reverse=True)
    breaching = [r for r in ordered if r.exceeds(thresholds.get(r.category))]

    live_by_risk: dict[int, list] = {}
    for exception in exceptions:
        state = exception_state(exception.expiry_date, ExceptionStatus(exception.status), as_of)
        live_by_risk.setdefault(exception.risk_id, []).append((exception, state))

    story: list = [
        p("Risk Register Report", s["title"]),
        p(
            f"FinFlow Technologies · {len(risks)} risks · generated {as_of.isoformat()}",
            s["subtitle"],
        ),
        Spacer(1, 4 * mm),
        p(
            "Inherent and residual risk are scored independently: an analyst sets residual "
            "likelihood and impact directly and justifies them in writing, rather than "
            "deriving residual from inherent by applying a control-effectiveness "
            "percentage. Controls that have never been tested, or that failed their test, "
            "earn no residual reduction. Comparison against appetite is by band, not score.",
            s["body"],
        ),
        Spacer(1, 5 * mm),
    ]

    headline = [
        ["Risks", "Above appetite", "No live acceptance", "Justifications outstanding"],
        [
            str(len(risks)),
            str(len(breaching)),
            str(
                sum(
                    1
                    for r in breaching
                    if not any(
                        st in ("APPROVED", "PENDING", "EXPIRING_SOON")
                        for _, st in live_by_risk.get(r.id, [])
                    )
                )
            ),
            str(sum(1 for r in risks if "TODO AUTHOR:BENNY" in r.residual_justification)),
        ],
    ]
    table = Table(headline, colWidths=[46 * mm] * 4, hAlign="LEFT")
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7.2),
            ("FONTSIZE", (0, 1), (-1, 1), 14),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.4, RULE),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story += [table, Spacer(1, 6 * mm)]

    rows = [[
        p("Ref", s["th"]), p("Risk", s["th"]), p("Category", s["th"]), p("Owner", s["th"]),
        p("Inherent", s["th"]), p("Residual", s["th"]), p("Appetite", s["th"]),
        p("Treatment", s["th"]), p("Acceptance", s["th"]),
    ]]
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("GRID", (0, 0), (-1, -1), 0.35, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]

    for index, risk in enumerate(ordered, start=1):
        threshold = thresholds.get(risk.category)
        exceeds = risk.exceeds(threshold)
        acceptances = live_by_risk.get(risk.id, [])
        acceptance_text = (
            ", ".join(f"{e.exception_ref} ({st.replace('_', ' ').lower()})" for e, st in acceptances)
            or "—"
        )
        rows.append([
            p(risk.risk_ref, s["cell"]),
            p(risk.title, s["cell"]),
            p(CATEGORY_LABELS[risk.category], s["cell_muted"]),
            p(risk.owner_role, s["cell_muted"]),
            p(
                f"{risk.inherent_likelihood}x{risk.inherent_impact}={risk.inherent_score} "
                f"{risk.inherent_band.value.lower()}",
                s["cell"],
            ),
            p(
                f"{risk.residual_likelihood}x{risk.residual_impact}={risk.residual_score} "
                f"{risk.residual_band.value.lower()}",
                s["cell"],
            ),
            p(
                f"max {threshold.max_acceptable_band.value.lower()} — "
                + ("ABOVE" if exceeds else "within")
                if threshold
                else "not set",
                s["cell"],
            ),
            p(_TREATMENT[risk.treatment_decision.value], s["cell"]),
            p(acceptance_text, s["cell_muted"]),
        ])
        if exceeds:
            has_live = any(
                st in ("APPROVED", "PENDING", "EXPIRING_SOON") for _, st in acceptances
            )
            commands.append(
                ("BACKGROUND", (0, index), (-1, index), ALERT_BG if has_live else BAD_BG)
            )

    widths = [16 * mm, 74 * mm, 24 * mm, 32 * mm, 26 * mm, 26 * mm, 30 * mm, 20 * mm, 34 * mm]
    register = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    register.setStyle(TableStyle(commands))
    story += [
        p("Register, ordered by residual score", s["h2"]),
        p(
            "Shaded rows exceed their category appetite. Rows shaded red have no live "
            "acceptance covering them — an exposure being carried without anyone having "
            "decided to carry it.",
            s["body"],
        ),
        Spacer(1, 3 * mm),
        register,
        PageBreak(),
    ]

    story.append(p("Risks above appetite — the decisions required", s["h2"]))
    for risk in breaching:
        threshold = thresholds.get(risk.category)
        acceptances = live_by_risk.get(risk.id, [])
        block = [
            p(f"{risk.risk_ref} · {risk.title}", s["h3"]),
            p(
                f"Residual {risk.residual_score} ({risk.residual_band.value.lower()}) against a "
                f"ceiling of {threshold.max_acceptable_band.value.lower()} for "
                f"{CATEGORY_LABELS[risk.category]}. Owner: {risk.owner_role}. Appetite is "
                f"approved by the {threshold.approver_role}.",
                s["body"],
            ),
            p("Residual justification", s["th"]),
            p(risk.residual_justification, s["body"]),
            p("Treatment", s["th"]),
            p(risk.treatment_summary, s["body"]),
        ]
        if acceptances:
            block.append(p("Acceptance", s["th"]))
            for exception, state in acceptances:
                block.append(
                    p(
                        f"{exception.exception_ref} — {state.replace('_', ' ').lower()}, "
                        f"approved by {exception.approver_role}, expires "
                        f"{exception.expiry_date}. {exception.decision_note or ''}",
                        s["body"],
                    )
                )
        else:
            block.append(
                p(
                    "No acceptance on record. This risk is above the limit the business "
                    "set and nobody has signed to carry it.",
                    s["body"],
                )
            )
        story.append(KeepTogether(block))
        story.append(Spacer(1, 4 * mm))

    story.append(Spacer(1, 6 * mm))
    story.append(
        KeepTogether([
            p("Limitations", s["h2"]),
            p(
                "FinFlow Technologies is a fictional company created for a portfolio "
                "project. No certification body or audit firm has assessed this data, no "
                "audit has been performed, and all ratings are illustrative. Several "
                "residual justifications are marked TODO AUTHOR:BENNY and are deliberately "
                "incomplete pending the author's own analysis.",
                s["body"],
            ),
        ])
    )

    doc.build(story)
    return buffer.getvalue()
