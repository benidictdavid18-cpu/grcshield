"""Read-only drill-down projections for existing records; no scoring or write rules."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.audit import AuditFinding, ControlTest
from app.models.risk import Control, RiskControl
from app.models.soa import Evidence, RemediationItem
from app.services.assurance import snapshot

router = APIRouter(tags=["Record drill-down"])


@router.get("/records/{kind}/{ref}")
def record(kind: str, ref: str, db: Session = Depends(get_db)):
    models = {"evidence": (Evidence, Evidence.evidence_ref),
              "remediation": (RemediationItem, RemediationItem.remediation_ref)}
    if kind not in models:
        raise HTTPException(404, "Unknown record type")
    model, column = models[kind]
    row = db.scalar(select(model).where(column == ref))
    if row is None:
        raise HTTPException(404, "Record not found")
    return dict(snapshot(row), disclaimer="Sample / Portfolio Assessment")


@router.get("/internal-controls/{ref}/trace")
def trace(ref: str, db: Session = Depends(get_db)):
    control = db.scalar(select(Control).where(Control.control_id == ref))
    if control is None:
        raise HTTPException(404, "Control not found")
    links = db.scalars(select(RiskControl).where(RiskControl.control_id == control.id)).all()
    tests = db.scalars(select(ControlTest).where(ControlTest.control_id == control.id)).all()
    findings = db.scalars(select(AuditFinding).where(AuditFinding.control_id == control.id)).all()
    return {
        "control_ref": ref,
        "design_effectiveness": control.design_effectiveness,
        "operating_effectiveness": control.operating_effectiveness,
        "risks": [{"risk_ref": link.risk.risk_ref, "title": link.risk.title,
                   "basis": link.effectiveness_basis, "note": link.note,
                   "credits_reduction": link.credits_reduction} for link in links],
        "tests": [{"test_ref": test.test_ref, "conclusion": test.conclusion,
                   "finding_ref": test.linked_finding.finding_ref if test.linked_finding else None}
                  for test in tests],
        "findings": [{"finding_ref": finding.finding_ref, "title": finding.title,
                      "status": finding.status,
                      "remediation": [{"remediation_ref": item.remediation_ref,
                                       "title": item.title, "status": item.status}
                                      for item in finding.linked_remediation]}
                     for finding in findings],
        "disclaimer": "Sample / Portfolio Assessment",
    }
