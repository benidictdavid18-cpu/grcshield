"""Authentication and authorisation.

The read-only auditor role is the point of the demo, and it only means something if
unauthenticated reads are refused outright.
"""

import pytest

PROTECTED_READS = [
    "/risks", "/soa", "/control-tests", "/findings", "/isms/audits", "/ropa", "/dpias",
    "/bia", "/assets", "/risk-exceptions", "/kris", "/executive-summary", "/reports",
    "/frameworks", "/internal-controls", "/risk-appetite",
]


@pytest.mark.parametrize("path", PROTECTED_READS)
def test_every_register_refuses_an_unauthenticated_read(anon_client, path):
    assert anon_client.get(path).status_code == 401, path


def test_health_stays_open_so_a_load_balancer_can_reach_it(anon_client):
    assert anon_client.get("/health").status_code == 200


def test_a_garbage_token_is_refused(anon_client):
    response = anon_client.get("/risks", headers={"Authorization": "Bearer nonsense"})
    assert response.status_code == 401


def test_a_token_signed_with_the_wrong_key_is_refused(anon_client):
    import jwt

    forged = jwt.encode(
        {"sub": "isms.manager", "role": "ADMIN", "iss": "grcshield", "exp": 9_999_999_999},
        "not-the-real-secret",
        algorithm="HS256",
    )
    response = anon_client.get("/risks", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_an_expired_token_is_refused(anon_client):
    import jwt

    from app.core.config import get_settings

    expired = jwt.encode(
        {"sub": "isms.manager", "role": "ADMIN", "iss": "grcshield", "exp": 1_000_000_000},
        get_settings().jwt_secret,
        algorithm="HS256",
    )
    response = anon_client.get("/risks", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_a_valid_token_for_an_unknown_user_is_refused(anon_client):
    """The role is re-read from the database, not trusted from the token."""
    import jwt

    from app.core.config import get_settings

    token = jwt.encode(
        {"sub": "ghost", "role": "ADMIN", "iss": "grcshield", "exp": 9_999_999_999},
        get_settings().jwt_secret,
        algorithm="HS256",
    )
    assert anon_client.get("/risks", headers={"Authorization": f"Bearer {token}"}).status_code == 401


@pytest.mark.parametrize(
    "username,password",
    [
        ("auditor", "wrong-password"),
        ("does-not-exist", "auditor-demo-2026"),
        ("auditor", ""),
    ],
)
def test_bad_credentials_all_return_the_same_401(anon_client, username, password):
    """Distinguishing them would let an attacker enumerate usernames."""
    response = anon_client.post(
        "/auth/token", json={"username": username, "password": password}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password."


def test_the_demo_accounts_authenticate(anon_client):
    for username, password, role, can_write in (
        ("auditor", "auditor-demo-2026", "AUDITOR", False),
        ("isms.manager", "manager-demo-2026", "ISMS_MANAGER", True),
    ):
        response = anon_client.post(
            "/auth/token", json={"username": username, "password": password}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["role"] == role
        assert body["can_write"] is can_write
        assert body["token_type"] == "bearer"
        assert body["expires_in"] == 8 * 3600


def test_passwords_are_not_stored_in_plain_text(db_session):
    from sqlalchemy import select

    from app.models.user import User

    for user in db_session.scalars(select(User)).all():
        assert "demo-2026" not in user.hashed_password
        # bcrypt, cost 12.
        assert user.hashed_password.startswith("$2b$12$")


def test_me_reports_the_signed_in_identity(client):
    body = client.get("/auth/me").json()
    assert body["username"] == "isms.manager"
    assert body["can_write"] is True


# --- The read-only role -------------------------------------------------------


def test_the_auditor_can_read_everything(auditor_client):
    for path in PROTECTED_READS:
        assert auditor_client.get(path).status_code == 200, path


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("patch", "/risks/RISK-001/residual",
         {"residual_likelihood": 1, "residual_impact": 1, "residual_justification": "x"}),
        ("patch", "/soa/A.8.13", {"owner": "someone else"}),
        ("patch", "/internal-controls/AC-002/effectiveness",
         {"operating_effectiveness": "EFFECTIVE"}),
        ("post", "/control-tests", {"control_id": "AC-006"}),
        ("post", "/risk-exceptions", {"risk_ref": "RISK-005"}),
    ],
)
def test_the_auditor_cannot_write(auditor_client, method, path, body):
    response = getattr(auditor_client, method)(path, json=body)
    assert response.status_code == 403, f"{method} {path} returned {response.status_code}"
    assert "read-only" in response.json()["detail"]


def test_the_manager_can_write(client):
    response = client.patch(
        "/risks/RISK-001/residual",
        json={
            "residual_likelihood": 2,
            "residual_impact": 4,
            "residual_justification": "AC-002 tested effective; likelihood held at 2.",
        },
    )
    assert response.status_code == 200


def test_a_write_refusal_happens_before_validation(auditor_client):
    """403, not 422 — the role is checked before the payload is."""
    response = auditor_client.patch(
        "/risks/RISK-001/residual",
        json={"residual_likelihood": 99, "residual_impact": 99, "residual_justification": ""},
    )
    assert response.status_code == 403
