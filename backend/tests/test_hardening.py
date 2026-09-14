"""Login throttling, the timing equaliser, the bcrypt length guard, and response headers.

Each of these was a row in SECURITY.md's Known gaps table. The tests are the reason the
row could be removed.
"""

import time

import pytest

from app.core import security
from app.core.config import get_settings
from app.core.rate_limit import FailureTracker, login_failures

# --- Failed-login throttling ---------------------------------------------------


@pytest.fixture()
def tight_limit(monkeypatch):
    """Three failures in a ten-second window, on a clean tracker."""
    settings = get_settings()
    monkeypatch.setattr(settings, "auth_failure_limit", 3)
    monkeypatch.setattr(settings, "auth_failure_window_seconds", 10)
    login_failures._failures.clear()
    yield
    login_failures._failures.clear()


def _login(client, username, password):
    return client.post("/auth/token", json={"username": username, "password": password})


def test_repeated_failures_against_one_account_are_refused_with_429(anon_client, tight_limit):
    for _ in range(3):
        assert _login(anon_client, "auditor", "wrong").status_code == 401
    response = _login(anon_client, "auditor", "wrong")
    assert response.status_code == 429
    assert response.headers["Retry-After"].isdigit()
    assert "Try again in" in response.json()["detail"]
    # The right password is refused too, while the window is open: the point is to
    # bound guessing, and a limit that lifts for the correct guess is not a limit.
    assert _login(anon_client, "auditor", get_settings().demo_auditor_password).status_code == 429


def test_the_limit_is_per_account_not_per_client(anon_client, tight_limit):
    for _ in range(3):
        _login(anon_client, "auditor", "wrong")
    assert _login(anon_client, "auditor", "wrong").status_code == 429
    # Same client, a different account: not affected.
    settings = get_settings()
    ok = _login(anon_client, settings.demo_manager_username, settings.demo_manager_password)
    assert ok.status_code == 200


def test_a_successful_login_clears_the_count(anon_client, tight_limit):
    settings = get_settings()
    for _ in range(2):
        _login(anon_client, "auditor", "wrong")
    assert _login(anon_client, "auditor", settings.demo_auditor_password).status_code == 200
    for _ in range(2):
        _login(anon_client, "auditor", "wrong")
    # Only two failures since the success, so still allowed.
    assert _login(anon_client, "auditor", "wrong").status_code == 401


def test_the_window_slides():
    tracker = FailureTracker()
    key = ("1.2.3.4", "auditor")
    for t in (0.0, 1.0, 2.0):
        tracker.record_failure(key, now=t)
    assert tracker.retry_after(key, now=2.5, limit=3, window=10) == 8
    # Once the oldest failure falls out of the window, an attempt is allowed again.
    assert tracker.retry_after(key, now=10.1, limit=3, window=10) is None


def test_unknown_usernames_are_throttled_too(anon_client, tight_limit):
    for _ in range(3):
        assert _login(anon_client, "nobody", "x").status_code == 401
    assert _login(anon_client, "nobody", "x").status_code == 429


# --- Username enumeration by timing --------------------------------------------


def test_an_unknown_username_costs_a_bcrypt_comparison(anon_client, monkeypatch):
    """The 401 was already uniform; this makes the response time uniform too."""
    burned = []
    # The route imported the name directly, so patch it where it is looked up.
    from app.api.routes import auth as auth_route

    monkeypatch.setattr(auth_route, "burn_a_verification", lambda plain: burned.append(plain))
    login_failures._failures.clear()
    assert _login(anon_client, "definitely-not-a-user", "pw").status_code == 401
    assert burned == ["pw"]


def test_the_unknown_user_path_takes_about_as_long_as_a_wrong_password(anon_client):
    """Coarse, but it catches the case that matters: one path skipping bcrypt entirely
    would be an order of magnitude faster, not a few percent."""
    login_failures._failures.clear()
    _login(anon_client, "auditor", "warm-up")

    start = time.perf_counter()
    _login(anon_client, "auditor", "wrong-password")
    known = time.perf_counter() - start

    start = time.perf_counter()
    _login(anon_client, "no-such-user", "wrong-password")
    unknown = time.perf_counter() - start

    login_failures._failures.clear()
    assert unknown > known * 0.5, f"unknown-user path too fast: {unknown:.3f}s vs {known:.3f}s"


# --- bcrypt's 72-byte limit ------------------------------------------------------


def test_a_password_longer_than_72_bytes_cannot_be_stored():
    with pytest.raises(security.PasswordTooLong):
        security.hash_password("a" * 73)
    # Bytes, not characters: three-byte UTF-8 characters hit the limit at 25.
    with pytest.raises(security.PasswordTooLong):
        security.hash_password("€" * 25)
    assert security.hash_password("a" * 72)


def test_a_password_longer_than_72_bytes_never_verifies():
    hashed = security.hash_password("a" * 72)
    assert security.verify_password("a" * 72, hashed)
    # Without the guard, bcrypt compares the first 72 bytes and says yes.
    assert security.verify_password("a" * 73, hashed) is False


# --- Response headers ------------------------------------------------------------


@pytest.mark.parametrize("path", ["/health", "/risks", "/auth/token", "/nope"])
def test_every_response_carries_the_security_headers(client, path):
    response = client.get(path)
    headers = response.headers
    assert headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert headers["Cache-Control"] == "no-store"


def test_the_interactive_docs_get_a_policy_that_lets_them_load(client):
    response = client.get("/docs")
    assert response.status_code == 200
    csp = response.headers["Content-Security-Policy"]
    assert "https://cdn.jsdelivr.net" in csp
    assert "frame-ancestors 'none'" in csp


def test_hsts_is_not_sent_in_development(client):
    assert get_settings().environment == "development"
    assert "Strict-Transport-Security" not in client.get("/health").headers


def test_a_pdf_carries_the_headers_too(client):
    response = client.get("/reports/risk-register.pdf")
    assert response.status_code == 200
    assert response.headers["X-Frame-Options"] == "DENY"
