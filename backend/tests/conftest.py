"""Test fixtures.

The suite runs against in-memory SQLite rather than PostgreSQL so it stays a plain
`pytest` away with no container running. Tables are built from the models via
``create_all``; the Alembic migration is verified separately by actually starting the
stack. Keep that distinction in mind: these tests prove the models, seed logic and
API contract, not the migration.

Seeding happens once. Each test then runs inside a transaction that is rolled back
afterwards, so tests that exercise write endpoints cannot leak state into the tests
that assert on seeded values.
"""

import os

# Must be set before app.core.config is imported -- the settings object is cached and
# the engine is constructed at import time from whatever URL it sees.
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
# The seed is a snapshot of FinFlow as of this date, and the assertions below describe
# that snapshot: EXC-001 is expiring soon, not expired; one acceptance has lapsed, not
# two. Pinned so the suite does not start failing on the day a seeded date passes.
os.environ["AS_OF_DATE"] = "2026-09-04"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event, select  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402,F401  -- registers tables on Base.metadata
from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402  (aliased: `app` is the package)
from app.models.risk import Risk  # noqa: E402
from app.seed import run_seed  # noqa: E402
from app.services.ai.provider import (  # noqa: E402
    AiProvider,
    Completion,
    ProviderStatus,
)
from app.services.ai.service import AIService, get_ai_service  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    # StaticPool keeps every connection pointed at the same in-memory database.
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _configure_connection(dbapi_connection, _record):
        # SQLite does not enforce foreign keys unless asked, and the SoA link tables
        # lean on them heavily enough that silent non-enforcement would hide real bugs.
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        # pysqlite emits its own implicit BEGIN, which breaks SAVEPOINT and therefore
        # breaks the rollback-per-test isolation below. Handing transaction control
        # back to SQLAlchemy is the fix documented in the SQLAlchemy pysqlite notes.
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _emit_begin(conn):
        conn.exec_driver_sql("BEGIN")

    Base.metadata.create_all(engine)

    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as db:
        iso = run_seed.seed_iso(db)
        soc2 = run_seed.seed_soc2(db)
        run_seed.seed_roadmap_frameworks(db)
        run_seed.seed_mappings(db, iso, soc2)
        controls = run_seed.seed_internal_controls(db, iso)
        run_seed.seed_appetite(db)
        run_seed.seed_risks(db, controls)
        risk_map = {r.risk_ref: r for r in db.scalars(select(Risk)).all()}
        evidence = run_seed.seed_evidence(db, controls)
        remediation = run_seed.seed_remediation(db)
        run_seed.seed_soa(db, iso, controls, risk_map, evidence, remediation)
        findings = run_seed.seed_findings(db, controls, remediation)
        run_seed.seed_control_tests(db, controls, evidence, findings)
        run_seed.check_risk_bases_against_control_library(db)
        run_seed.seed_isms_records(db, findings)
        assets = run_seed.seed_assets(db)
        run_seed.seed_risk_exceptions(db, risk_map)
        ropa = run_seed.seed_ropa(db, assets, risk_map, controls)
        run_seed.seed_dpias(db, assets, risk_map, ropa)
        run_seed.seed_bia(db, assets, controls, risk_map)
        run_seed.seed_users(db)
        run_seed.seed_kris(db)
        db.commit()

    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(engine):
    """A session whose writes are discarded when the test ends.

    ``join_transaction_mode="create_savepoint"`` turns the application's own
    ``commit()`` calls into savepoint releases, so route handlers behave normally
    while the outer transaction still rolls everything back.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def anon_client(db_session):
    """A client with no credentials. Used to prove that reads are actually refused."""
    def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


def _authenticate(test_client: TestClient, username: str, password: str) -> TestClient:
    response = test_client.post(
        "/auth/token", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    test_client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return test_client


@pytest.fixture()
def client(anon_client):
    """The default client: signed in as the ISMS manager, so it can read and write."""
    settings = get_settings()
    return _authenticate(
        anon_client, settings.demo_manager_username, settings.demo_manager_password
    )


@pytest.fixture()
def auditor_client(db_session):
    """A separate client signed in as the read-only auditor."""
    def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    settings = get_settings()
    with TestClient(fastapi_app) as test_client:
        yield _authenticate(
            test_client, settings.demo_auditor_username, settings.demo_auditor_password
        )
    fastapi_app.dependency_overrides.clear()


# --- The AI assistant ----------------------------------------------------------
#
# The suite must never need a running model server. A test that quietly depends on
# Ollama being up is a test that fails on somebody else's machine, in CI, and on a
# laptop with the service stopped -- and it would be testing the model rather than this
# application. So the provider boundary is where the double goes: everything above it
# is exercised for real, and the only thing replaced is the HTTP call to Ollama.


class StubProvider(AiProvider):
    """A provider whose answer, or failure, the test chooses."""

    name = "stub"

    def __init__(self) -> None:
        self.response_text: str = "{}"
        self.raises: Exception | None = None
        self.status_result = ProviderStatus(
            provider="stub",
            configured_model="stub-model",
            reachable=True,
            model_available=True,
            detail="Stub provider is ready.",
            available_models=("stub-model",),
            version="0.0.0-test",
        )
        # Every call is recorded so a test can assert on what was actually sent --
        # which is how the prompt-injection and context-filtering tests work.
        self.calls: list[dict] = []
        self.status_calls = 0

    def status(self) -> ProviderStatus:
        self.status_calls += 1
        return self.status_result

    def complete(self, *, system_prompt, user_prompt, json_schema=None) -> Completion:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "json_schema": json_schema,
            }
        )
        if self.raises is not None:
            raise self.raises
        return Completion(
            text=self.response_text, model="stub-model", latency_ms=7, metadata={}
        )

    # Convenience for the common case.
    def returns(self, payload: dict) -> "StubProvider":
        import json as _json

        self.response_text = _json.dumps(payload)
        return self


@pytest.fixture()
def ai_provider() -> StubProvider:
    return StubProvider()


@pytest.fixture()
def ai_service(ai_provider):
    """Install a stubbed AIService for the duration of one test.

    Substituted through ``dependency_overrides`` rather than by monkeypatching a module
    global, so the replacement is visible in the test and cannot leak into another one.
    """
    service = AIService(ai_provider, get_settings())
    fastapi_app.dependency_overrides[get_ai_service] = lambda: service
    yield service
    fastapi_app.dependency_overrides.pop(get_ai_service, None)
