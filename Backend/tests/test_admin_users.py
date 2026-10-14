"""L4.7 : gestion des utilisateurs par l'administrateur."""

import pytest
from fastapi.testclient import TestClient

from tests.api_stub import install

install()

from api.main import app  # noqa: E402
from api.services import user_service  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def boss(client):
    body = client.post(
        "/api/v1/auth/login", json={"email": "boss@example.com", "password": "Sup3rS3cret!"}
    ).json()
    return {"headers": bearer(body["token"]), "id": body["user"]["id"]}


def register(client, email):
    body = client.post(
        "/api/v1/auth/register", json={"email": email, "password": "Passw0rd!", "name": email}
    ).json()
    return {"headers": bearer(body["token"]), "id": body["user"]["id"]}


def test_user_management_requires_admin(client):
    plain = register(client, "plain-admin-test@example.com")
    client.cookies.clear()
    assert client.get("/api/v1/admin/users").status_code in (401, 403)
    assert client.get("/api/v1/admin/users", headers=plain["headers"]).status_code == 403
    patch = client.patch(
        f"/api/v1/admin/users/{plain['id']}", json={"role": "admin"}, headers=plain["headers"]
    )
    assert patch.status_code == 403
    assert (
        client.delete(f"/api/v1/admin/users/{plain['id']}", headers=plain["headers"]).status_code
        == 403
    )


def test_list_shows_activity_without_secrets(client, boss):
    user = register(client, "active-user@example.com")
    client.cookies.clear()
    client.post("/api/v1/chat/query", json={"question": "3M capex?"}, headers=user["headers"])
    users = client.get("/api/v1/admin/users", headers=boss["headers"]).json()
    mine = next(u for u in users if u["id"] == user["id"])
    assert mine["conversations"] == 1 and mine["requests"] == 1 and mine["last_activity"]
    assert "hashed_password" not in mine
    assert any(u["role"] == "admin" for u in users)


def test_role_change_is_effective_immediately_and_guarded(client, boss):
    user = register(client, "promote-me@example.com")
    client.cookies.clear()
    patch = client.patch(
        f"/api/v1/admin/users/{user['id']}", json={"role": "admin"}, headers=boss["headers"]
    )
    assert patch.status_code == 200 and patch.json()["role"] == "admin"
    # le rôle est relu en base : le jeton déjà émis a désormais les droits admin
    assert client.get("/api/v1/admin/users", headers=user["headers"]).status_code == 200

    own = client.patch(
        f"/api/v1/admin/users/{boss['id']}", json={"role": "user"}, headers=boss["headers"]
    )
    assert own.status_code == 400  # on ne se rétrograde pas soi-même
    unknown = client.patch(
        "/api/v1/admin/users/nope", json={"role": "user"}, headers=boss["headers"]
    )
    assert unknown.status_code == 404
    invalid = client.patch(
        f"/api/v1/admin/users/{user['id']}", json={"role": "root"}, headers=boss["headers"]
    )
    assert invalid.status_code == 422

    back = client.patch(
        f"/api/v1/admin/users/{user['id']}", json={"role": "user"}, headers=boss["headers"]
    )
    assert back.json()["role"] == "user"
    assert client.get("/api/v1/admin/users", headers=user["headers"]).status_code == 403


def test_delete_user_cascades_conversations_and_blocks_the_token(client, boss):
    victim = register(client, "victim@example.com")
    client.cookies.clear()
    client.post("/api/v1/chat/query", json={"question": "hello?"}, headers=victim["headers"])
    assert (
        client.delete(f"/api/v1/admin/users/{boss['id']}", headers=boss["headers"]).status_code
        == 400
    )  # pas soi-même
    assert (
        client.delete(f"/api/v1/admin/users/{victim['id']}", headers=boss["headers"]).status_code
        == 204
    )
    assert client.get("/api/v1/auth/me", headers=victim["headers"]).status_code == 401
    assert client.delete("/api/v1/admin/users/nope", headers=boss["headers"]).status_code == 404
    assert victim["id"] not in [u["id"] for u in user_service.list_users()]


def test_last_admin_is_protected_at_service_level(client, boss, monkeypatch):
    """Défense en profondeur : inatteignable par l'API (l'acteur est lui-même admin)."""
    other = register(client, "admin-guard@example.com")
    client.patch(
        f"/api/v1/admin/users/{other['id']}", json={"role": "admin"}, headers=boss["headers"]
    )
    monkeypatch.setattr(user_service, "_admin_count", lambda db: 1)
    assert user_service.set_role(other["id"], "user") == "last_admin"
    assert user_service.delete_user(other["id"]) == "last_admin"
    assert user_service.set_role("nope", "user") == "not_found"
