"""The documentation states numbers. These check them against what they describe.

G21 asks an auditor's question: *which description is current?* The repository could
not answer it. README claimed 419 tests against a real 543, and the documents quoted
four different smoke-check counts — 65, 69, 79 and 83 — none of which matched the 104
the script actually reports.

Correcting those figures by hand fixes today and nothing else, because the next change
to the suite makes them wrong again, silently. So the figures are asserted here instead.
A number in prose that no test reads is a claim; a number a test compares against its
source is a fact with an expiry date attached.

``docs/GAP_PROGRESS.md`` is deliberately out of scope. It is a dated log of what passed
at each checkpoint, so its older counts are correct history rather than stale claims.
"""

import re
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.models.risk import Risk

REPO = Path(__file__).resolve().parents[2]
README = REPO / "README.md"
METRICS = REPO / "docs" / "METRICS.md"
MIGRATIONS = REPO / "backend" / "alembic" / "versions"

# Below this, the run is a subset rather than the whole suite, and comparing a
# documented total against it would fail for the wrong reason.
FULL_RUN_FLOOR = 400


def _claims(pattern: str, *paths: Path) -> list[tuple[str, int]]:
    """Every (file, number) a pattern matches across the given documents."""
    found: list[tuple[str, int]] = []
    for path in paths:
        for match in re.finditer(pattern, path.read_text(encoding="utf-8")):
            found.append((path.name, int(match.group(1))))
    return found


def test_the_documented_test_count_is_the_real_one(request):
    """README states a test total. It has to be the total pytest just collected."""
    collected = len(request.session.items)
    if collected < FULL_RUN_FLOOR:
        pytest.skip(f"partial run ({collected} tests); a total is only meaningful in full")

    claims = _claims(r"(\d{3,4})\s+tests\b", README)
    assert claims, "README no longer states a test count; this check has nothing to guard"
    for name, stated in claims:
        assert stated == collected, (
            f"{name} says {stated} tests, pytest collected {collected}. "
            "Update the document, or delete the number rather than let it rot."
        )


def test_every_document_agrees_on_the_smoke_check_count():
    """The documents once quoted four different totals for the same script."""
    claims = _claims(r"(\d{2,4})\s+(?:smoke\s+)?checks\b", README, METRICS)
    assert claims, "no smoke-check count is stated anywhere"
    counts = {stated for _, stated in claims}
    assert len(counts) == 1, (
        "documents disagree about the smoke-check count: "
        f"{sorted(f'{n}={c}' for n, c in claims)}. "
        "The script reports its own total; state one number, once, verified live."
    )


def test_the_documented_migration_count_matches_the_chain():
    """A migration count is checkable by counting migrations."""
    actual = len(list(MIGRATIONS.glob("[0-9]*.py")))
    claims = _claims(r"(\d{1,3})\s+migrations\b", README)
    assert claims, "README no longer states a migration count"
    for name, stated in claims:
        assert stated == actual, f"{name} says {stated} migrations, the chain has {actual}"


def test_the_documented_risk_count_matches_the_register(db_session):
    """The register is the source; the README repeats it."""
    actual = db_session.scalar(select(func.count(Risk.id)))
    claims = _claims(r"\|\s*Risks\s*\|\s*(\d{1,3})\s*\|", README)
    assert claims, "README no longer tabulates the risk count"
    for name, stated in claims:
        assert stated == actual, f"{name} says {stated} risks, the register holds {actual}"
