"""Routes de chat : persistance, métriques, streaming SSE réel, feedback, erreurs."""

import json
import time

import pytest
from fastapi.testclient import TestClient

from tests.api_stub import install

state = install()

from api.main import app  # noqa: E402
from api.services import metrics_service  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "chat@example.com", "password": "Passw0rd!", "name": "Chat"},
    )
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(autouse=True)
def reset_llm():
    state.llm.reply, state.llm.delay = "Capex was 1577 million [1].", 0.0
    state.llm.calls.clear()
    state.search_delay = 0.0


def test_query_returns_cited_answer_and_persists_everything(client, auth):
    r = client.post("/api/v1/chat/query", json={"question": "3M capex?"}, headers=auth)
    body = r.json()
    assert r.status_code == 200 and body["success"]
    assert body["response"].strip() == "Capex was 1577 million [1]."
    assert body["citations"][0]["source"] == "3M_2018_10K.pdf"
    assert body["citations"][0]["metadata"]["page"] == 60
    assert body["message_id"]

    msgs = client.get(
        f"/api/v1/chat/conversations/{body['conversation_id']}/messages", headers=auth
    ).json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[1]["id"] == body["message_id"] and msgs[1]["citations"][0]["id"] == 1
    assert metrics_service.get_metrics_overview()["total_requests"] >= 1


def test_follow_up_question_uses_history_and_one_extra_llm_call(client, auth):
    first = client.post(
        "/api/v1/chat/query", json={"question": "Adobe 2022 revenue?"}, headers=auth
    )
    conv = first.json()["conversation_id"]
    calls_before = len(state.llm.calls)
    second = client.post(
        "/api/v1/chat/query",
        json={"question": "and its cash flow?", "conversation_id": conv},
        headers=auth,
    )
    assert second.json()["success"]
    assert (
        len(state.llm.calls) - calls_before == 1
    )  # génération ; l'analyse passe par le faux analyseur


def test_stream_emits_tokens_then_citations_then_done(client, auth):
    with client.stream(
        "POST", "/api/v1/chat/query/stream", json={"question": "3M capex?"}, headers=auth
    ) as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        events = [line[6:] for line in r.iter_lines() if line.startswith("data: ")]
    assert events[-1] == "[DONE]"
    parsed = [json.loads(e) for e in events[:-1]]
    chunks = [p["chunk"] for p in parsed if "chunk" in p]
    final = parsed[-1]
    assert len(chunks) >= 4 and "".join(chunks).strip() == "Capex was 1577 million [1]."
    assert final["citations"][0]["source"] == "3M_2018_10K.pdf" and final["message_id"]

    msgs = client.get(
        f"/api/v1/chat/conversations/{final['conversation_id']}/messages", headers=auth
    ).json()
    assert msgs[-1]["content"].strip() == "Capex was 1577 million [1]." and msgs[-1]["citations"]


@pytest.fixture(scope="module")
def live_server():
    """Vrai serveur HTTP : le TestClient de Starlette bufferise la réponse, il ne permet pas de
    constater un streaming progressif."""
    import socket
    import threading

    import uvicorn

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    assert server.started
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10)


def test_tokens_reach_the_http_client_progressively(live_server):
    import httpx

    state.llm.reply, state.llm.delay = "one two three four five six", 0.2
    token = httpx.post(
        f"{live_server}/api/v1/auth/register",
        json={"email": "live@example.com", "password": "Passw0rd!", "name": "L"},
    ).json()["token"]

    arrivals = []
    started = time.perf_counter()
    with httpx.stream(
        "POST",
        f"{live_server}/api/v1/chat/query/stream",
        json={"question": "3M capex?"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    ) as r:
        for line in r.iter_lines():
            if line.startswith("data: ") and '"chunk"' in line:
                arrivals.append(time.perf_counter() - started)
    total = time.perf_counter() - started
    assert len(arrivals) >= 6
    assert arrivals[0] < total - 0.6, "le premier token doit arriver bien avant la fin"
    assert arrivals[-1] - arrivals[0] > 0.8, "les tokens sont étalés dans le temps"


def test_errors_are_generic_and_recorded(client, auth):
    original = state.deps.search

    def broken(query, filters):
        raise RuntimeError("secret internal detail: db password=hunter2")

    state.deps.search = broken
    try:
        r = client.post("/api/v1/chat/query", json={"question": "boom?"}, headers=auth)
        stream = client.post("/api/v1/chat/query/stream", json={"question": "boom?"}, headers=auth)
    finally:
        state.deps.search = original
    assert r.json()["success"] is False and "hunter2" not in r.text
    assert "hunter2" not in stream.text and '"error"' in stream.text
    assert metrics_service.get_error_distribution()["other"] >= 1


def test_empty_question_rejected(client, auth):
    r = client.post("/api/v1/chat/query", json={"question": "   "}, headers=auth)
    assert r.status_code == 400
    assert (
        client.post("/api/v1/chat/query", json={"question": "x" * 2001}, headers=auth).status_code
        == 422
    )


def test_feedback_on_returned_message_id(client, auth):
    body = client.post("/api/v1/chat/query", json={"question": "3M capex?"}, headers=auth).json()
    r = client.post(
        "/api/v1/chat/feedback",
        json={"message_id": body["message_id"], "feedback_type": "thumbs_up"},
        headers=auth,
    )
    assert r.status_code == 200
