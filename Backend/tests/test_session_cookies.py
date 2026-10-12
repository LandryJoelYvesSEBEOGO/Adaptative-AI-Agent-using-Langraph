"""L4.8 : session par cookies httpOnly, refresh, déconnexion, protection CSRF."""

import pytest
from fastapi.testclient import TestClient

from tests.api_stub import install

install()

from api.main import app  # noqa: E402
from api.services.auth_service import create_refresh_token  # noqa: E402

ORIGIN = "http://localhost:5173"  # présente dans CORS_ORIGINS par défaut


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _cookie_headers(response) -> list[str]:
    return [v for k, v in response.headers.multi_items() if k == "set-cookie"]


def register(client, email):
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Passw0rd!", "name": "Cookie"},
    )


def test_login_sets_httponly_cookies_with_scoped_refresh(client):
    register(client, "cookie1@example.com")
    r = client.post(
        "/api/v1/auth/login", json={"email": "cookie1@example.com", "password": "Passw0rd!"}
    )
    cookies = _cookie_headers(r)
    access = next(c for c in cookies if c.startswith("access_token="))
    refresh = next(c for c in cookies if c.startswith("refresh_token="))
    for cookie in (access, refresh):
        assert "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert "Path=/;" in access + ";" and "Path=/api/v1/auth" in refresh
    assert r.json()["token"]  # pour les clients non navigateur (évaluation, scripts)


def test_cookie_authenticates_without_authorization_header(client):
    register(client, "cookie2@example.com")  # le jar du client conserve les cookies
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200 and me.json()["email"] == "cookie2@example.com"
    assert client.get("/api/v1/chat/conversations").status_code == 200


def test_no_credentials_means_401(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/chat/conversations").status_code == 401


def test_csrf_unsafe_requests_with_cookie_need_an_allowed_origin(client):
    register(client, "cookie3@example.com")
    body = {"title": "t"}
    assert client.post("/api/v1/chat/conversations", json=body).status_code == 403
    evil = client.post(
        "/api/v1/chat/conversations", json=body, headers={"Origin": "https://evil.example"}
    )
    assert evil.status_code == 403
    ok = client.post("/api/v1/chat/conversations", json=body, headers={"Origin": ORIGIN})
    assert ok.status_code == 200
    # les lectures (GET) restent possibles sans Origin
    assert client.get("/api/v1/chat/conversations").status_code == 200


def test_bearer_header_is_not_subject_to_the_origin_check(client):
    token = register(client, "cookie4@example.com").json()["token"]
    client.cookies.clear()
    r = client.post(
        "/api/v1/chat/conversations",
        json={"title": "t"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200


def test_refresh_issues_a_new_session_and_rotates_the_refresh_token(client):
    register(client, "cookie5@example.com")
    client.cookies.delete("access_token", path="/")  # l'accès a « expiré »
    assert client.get("/api/v1/auth/me").status_code == 401
    r = client.post("/api/v1/auth/refresh")
    assert r.status_code == 200 and r.json()["user"]["email"] == "cookie5@example.com"
    assert any(c.startswith("refresh_token=") for c in _cookie_headers(r))  # rotation
    assert client.get("/api/v1/auth/me").status_code == 200


def test_refresh_without_valid_cookie_is_rejected(client):
    assert client.post("/api/v1/auth/refresh").status_code == 401
    client.cookies.set("refresh_token", "garbage", path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_token_types_are_not_interchangeable(client):
    user_id = register(client, "cookie6@example.com").json()["user"]["id"]
    client.cookies.clear()
    refresh = create_refresh_token(user_id)
    # un refresh token ne donne pas accès à l'API
    assert (
        client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh}"}).status_code
        == 401
    )
    client.cookies.set("access_token", refresh, path="/")
    assert client.get("/api/v1/auth/me").status_code == 401
    # un access token ne permet pas de se renouveler
    access = register(client, "cookie7@example.com").json()["token"]
    client.cookies.clear()
    client.cookies.set("refresh_token", access, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_logout_clears_the_session(client):
    register(client, "cookie8@example.com")
    r = client.post("/api/v1/auth/logout")
    assert r.status_code == 200
    cleared = _cookie_headers(r)
    assert any(c.startswith("access_token=") and "Max-Age=0" in c for c in cleared)
    assert any(c.startswith("refresh_token=") and "Max-Age=0" in c for c in cleared)
    assert client.get("/api/v1/auth/me").status_code == 401
