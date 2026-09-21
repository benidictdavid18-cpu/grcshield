"""The sample is initialization data, not a restart-time source of truth."""
from sqlalchemy import select
from app.models.bootstrap import SampleBootstrap
from app.db.base import Base
from app.models.audit_trail import AuditEvent

def prepare(db, *, reapply=False, reason=None, operator=None):
    row = db.scalar(select(SampleBootstrap).where(SampleBootstrap.id == 1).with_for_update())
    if reapply:
        if not reason or not reason.strip() or not operator:
            raise ValueError("Sample reapplication requires an explicit operator and reason.")
        if row is None:
            row = SampleBootstrap(id=1,status="REAPPLIED",reason=reason.strip())
            db.add(row)
        else:
            row.status,row.reason="REAPPLIED",reason.strip()
        db.add(AuditEvent(actor_username=operator[:64],actor_role="LOCAL_OPERATOR",action="SAMPLE_REAPPLIED",record_type="SAMPLE",record_ref="FINFLOW",before=None,
            after={"reason":reason.strip()},summary="Operator explicitly requested reapplication of authored fictional sample data."))
        db.flush()
        return True
    if row:
        return False
    populated = any(
        db.execute(select(table).limit(1)).first() is not None
        for table in Base.metadata.sorted_tables
        if table.name != "sample_bootstrap"
    )
    row = SampleBootstrap(id=1,status="PRESERVED" if populated else "INITIALIZED",
        reason="Existing records preserved without sample reapplication." if populated else "Empty database initialized once with the authored fictional sample.")
    db.add(row)
    # The singleton key also prevents two simultaneous initializers from committing.
    db.flush()
    return not populated
