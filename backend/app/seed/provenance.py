"""Bind only workpapers that exist; never invent proof for library-only claims."""
from sqlalchemy import select
from app.models.risk import RiskControl
from app.services.provenance import BASIS_RANK, TEST_RANK, TODO

def seed_proofs(db, tests):
    for link in db.scalars(select(RiskControl)):
        if link.effectiveness_basis.value not in BASIS_RANK or link.supporting_test_id is not None:
            continue
        candidates = [t for t in tests.values() if t.control_id == link.control_id and TEST_RANK[t.conclusion.value] == BASIS_RANK[link.effectiveness_basis.value]]
        if len(candidates) == 1:
            test = candidates[0]
            link.supporting_test_id = test.id
            link.proof_note = f"Sample / Portfolio Assessment. Existing authored basis matches {test.test_ref}; population: {test.population_description}"
        else:
            link.proof_note = TODO
    db.flush()
