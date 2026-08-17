"""Shared PDF furniture, so all three reports look like one product."""

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph

from app.core.config import get_settings

INK = colors.HexColor("#1a1d24")
MUTED = colors.HexColor("#5b6470")
RULE = colors.HexColor("#c8cdd6")
HEADER_BG = colors.HexColor("#eceff4")
ALERT_BG = colors.HexColor("#fdf3e3")
BAD_BG = colors.HexColor("#fbeaea")
GOOD_BG = colors.HexColor("#eaf4ec")


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontSize=18, leading=22, textColor=INK,
            alignment=TA_LEFT, spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"], fontSize=9.5, leading=13, textColor=MUTED,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontSize=13, leading=16, textColor=INK,
            spaceBefore=14, spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "h3", parent=base["Heading3"], fontSize=10.5, leading=13, textColor=INK,
            spaceBefore=9, spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontSize=9.5, leading=13.5, textColor=INK,
        ),
        "lead": ParagraphStyle(
            "lead", parent=base["Normal"], fontSize=11, leading=15.5, textColor=INK,
            spaceAfter=6,
        ),
        "cell": ParagraphStyle(
            "cell", parent=base["Normal"], fontSize=7.6, leading=9.6, textColor=INK,
        ),
        "cell_muted": ParagraphStyle(
            "cell_muted", parent=base["Normal"], fontSize=7.6, leading=9.6, textColor=MUTED,
        ),
        "th": ParagraphStyle(
            "th", parent=base["Normal"], fontSize=7.2, leading=9.2, textColor=MUTED,
            fontName="Helvetica-Bold",
        ),
    }


def escape(text) -> str:
    return (
        str(text if text is not None else "—")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def p(text, style) -> Paragraph:
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


def page_furniture(footer_label: str):
    """Stamp the portfolio disclaimer on every page of every report."""

    def _draw(canvas, doc):
        canvas.saveState()
        width, height = doc.pagesize
        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(colors.HexColor("#8a6d1f"))
        canvas.drawString(16 * mm, height - 10 * mm, get_settings().data_disclaimer)
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.4)
        canvas.line(16 * mm, height - 12.5 * mm, width - 16 * mm, height - 12.5 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(16 * mm, 9 * mm, footer_label)
        canvas.drawRightString(width - 16 * mm, 9 * mm, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    return _draw
