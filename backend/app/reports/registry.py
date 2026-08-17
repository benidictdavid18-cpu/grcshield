"""The report set.

Deliberately three reports, not seven. Each one has a named audience and a decision
it supports. A report that nobody would act on is a chart with a cover page, and it
costs more to keep honest than it returns.

Renderers are added in the phase that supplies their underlying data:
    RISK_REGISTER      -- Phase 2 (risk engine)
    SOA_GAP_ANALYSIS   -- Phase 3 (Statement of Applicability)
    EXECUTIVE_SUMMARY  -- Phase 6 (KRIs and executive view)
"""

import enum
from typing import NamedTuple


class ReportCode(str, enum.Enum):
    RISK_REGISTER = "RISK_REGISTER"
    SOA_GAP_ANALYSIS = "SOA_GAP_ANALYSIS"
    EXECUTIVE_SUMMARY = "EXECUTIVE_SUMMARY"


class ReportDefinition(NamedTuple):
    code: ReportCode
    title: str
    audience: str
    decision_supported: str
    available_from_phase: int
    implemented: bool
    endpoint: str | None = None


REPORTS: list[ReportDefinition] = [
    ReportDefinition(
        code=ReportCode.RISK_REGISTER,
        title="Risk Register Report",
        audience="Risk owners and the management review meeting",
        decision_supported=(
            "Which risks exceed their category appetite and therefore need a treatment "
            "decision or a formal, time-boxed acceptance."
        ),
        available_from_phase=2,
        implemented=True,
        endpoint="/reports/risk-register.pdf",
    ),
    ReportDefinition(
        code=ReportCode.SOA_GAP_ANALYSIS,
        title="SoA + Gap Analysis Report",
        audience="Certification auditor and the ISMS manager",
        decision_supported=(
            "Whether every Annex A control has a defensible applicability decision, and "
            "where applicable-but-not-implemented controls need remediation with an owner "
            "and a due date."
        ),
        available_from_phase=3,
        implemented=True,
        endpoint="/soa/report.pdf",
    ),
    ReportDefinition(
        code=ReportCode.EXECUTIVE_SUMMARY,
        title="Executive Summary Report",
        audience="Founders and the board",
        decision_supported=(
            "Where to spend the next quarter of security budget and headcount, stated "
            "without control identifiers or jargon."
        ),
        available_from_phase=6,
        implemented=True,
        endpoint="/reports/executive-summary.pdf",
    ),
]

REPORTS_BY_CODE = {r.code: r for r in REPORTS}
