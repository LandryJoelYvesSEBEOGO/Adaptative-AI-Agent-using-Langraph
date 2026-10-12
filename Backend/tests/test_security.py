"""Tests de sécurité du lot 1 (L1.2 à L1.6)."""

import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["JWT_SECRET_KEY"] = "test-secret-" + "x" * 40
os.environ["RAG_DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test.db")

import types  # noqa: E402

# Le moteur RAG (Rag_model) initialise LLM/Tavily à l'import : on le remplace ici,
# ces tests ne portent que sur la couche HTTP/sécurité.
_fake = types.ModuleType("api.services.chat_service")
_fake.process_rag_query = lambda **kw: {"response": "ok", "citations": [], "success": True}
_fake.process_rag_query_stream = lambda **kw: iter(["ok"])
sys.modules["api.services.chat_service"] = _fake

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402
from api.services.conversation_service import add_message  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # déclenche le lifespan : migrations + comptes initiaux
        yield c


def _register(client, email, **extra):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Passw0rd!", "name": "T", **extra},
    )
    body = r.json()
    assert body["success"], body
    return body


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_missing_secret_refuses_to_start(monkeypatch):
    import importlib

    from api.services import auth_service
    from config.settings import get_settings

    monkeypatch.delenv("JWT_SECRET_KEY")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError):
            importlib.reload(auth_service)
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
        importlib.reload(auth_service)


def test_admin_routes_require_admin(client):
    assert client.get("/api/v1/admin/metrics/overview").status_code in (401, 403)
    user = _register(client, "plain@example.com")
    r = client.get("/api/v1/admin/metrics/overview", headers=_auth(user["token"]))
    assert r.status_code == 403


def test_register_cannot_choose_role(client):
    body = _register(client, "sneaky@example.com", role="admin")
    assert body["user"]["role"] == "user"


def test_conversation_ownership_on_chat(client):
    alice = _register(client, "alice@example.com")
    bob = _register(client, "bob@example.com")
    conv = client.post(
        "/api/v1/chat/conversations", json={"title": "x"}, headers=_auth(alice["token"])
    ).json()
    for path in ("/api/v1/chat/query", "/api/v1/chat/query/stream"):
        r = client.post(
            path,
            json={"question": "hello", "conversation_id": conv["id"]},
            headers=_auth(bob["token"]),
        )
        assert r.status_code == 404, path


def test_feedback_requires_auth_and_ownership(client):
    alice = _register(client, "alice2@example.com")
    bob = _register(client, "bob2@example.com")
    conv = client.post(
        "/api/v1/chat/conversations", json={"title": "x"}, headers=_auth(alice["token"])
    ).json()
    msg = add_message(conv["id"], "assistant", "réponse")
    payload = {"message_id": msg["id"], "feedback_type": "thumbs_up"}

    assert client.post("/api/v1/chat/feedback", json=payload).status_code in (401, 403)
    assert (
        client.post("/api/v1/chat/feedback", json=payload, headers=_auth(bob["token"])).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/chat/feedback", json=payload, headers=_auth(alice["token"])
        ).status_code
        == 200
    )
