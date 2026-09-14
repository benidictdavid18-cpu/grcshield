"""The business date, from one place.

Every register computes something from "today": whether an evidence artifact is still
inside its validity window, whether a risk acceptance has expired, whether a remediation
item is overdue, which six months a KRI trend covers. The seed data is a snapshot of
FinFlow as of a particular date, so against the real calendar the demo silently changes
shape as time passes -- EXC-001 flipped from EXPIRING_SOON to EXPIRED on 2026-09-05 and
took three tests with it, none of which had changed.

``AS_OF_DATE`` pins the business date. Unset, the real calendar is used, which is what a
live deployment wants. The demo compose file and the test suite pin it, so the numbers in
the README and the assertions in the tests describe a fixed snapshot rather than
whatever today happens to be.

Only the *business* date goes through here. Token expiry and interaction timestamps
are wall-clock facts and keep using ``datetime.now``.
"""

from datetime import date

from app.core.config import get_settings


def today() -> date:
    pinned = get_settings().as_of_date
    return pinned if pinned is not None else date.today()
