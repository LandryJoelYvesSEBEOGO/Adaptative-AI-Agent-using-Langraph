"""L5.3 : logs structurés, identifiant de requête, alertes, traçage Langfuse."""

import json
import logging
import sys
import types

import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_core.callbacks import BaseCallbackHandler

from tests.api_stub import install

install()

from api import alerts  # noqa: E402
from api.database import session_scope  # noqa: E402
from api.db_models import RagRequest  # noqa: E402
from api.main import app  # noqa: E402
from api.observability import JsonFormatter, RequestIdFilter, request_id_var  # noqa: E402
from api.services import metrics_service as metrics  # noqa: E402
from config.settings import Settings, get_settings  # noqa: E402
from src.rag.pipeline import stream_rag  # noqa: E402
from src.rag.tracing import tracing_callbacks  # noqa: E402
from tests.fakes import SlowStreamingLLM, make_deps  # noqa: E402

# ---------- logs ----------


def test_json_formatter_emits_one_parsable_line_with_extras_and_request_id():
    record = logging.LogRecord(
        "api.access", logging.INFO, "f.py", 1, "GET %s -> %s", ("/x", 200), None
    )
    record.duration_ms = 12.5
    record.status = 200
    token = request_id_var.set("req-123")
    try:
        RequestIdFilter().filter(record)
        line = JsonFormatter().format(record)
    finally:
        request_id_var.reset(token)
    payload = json.loads(line)
    assert "\n" not in line
    assert payload["message"] == "GET /x -> 200" and payload["level"] == "INFO"
    assert payload["request_id"] == "req-123" and payload["duration_ms"] == 12.5
    assert payload["time"].endswith("+00:00")


def test_json_formatter_includes_exceptions():
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.LogRecord("x", logging.ERROR, "f.py", 1, "failed", None, sys.exc_info())
    assert "ValueError: boom" in json.loads(JsonFormatter().format(record))["exception"]


def test_log_format_defaults_to_json_in_prod_only():
    from api.observability import use_json_logs

    assert use_json_logs(Settings(_env_file=None, ENVIRONMENT="prod")) is True
    assert use_json_logs(Settings(_env_file=None, ENVIRONMENT="dev")) is False
    assert use_json_logs(Settings(_env_file=None, ENVIRONMENT="dev", LOG_FORMAT="json")) is True


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_request_id_is_generated_echoed_and_logged(client, caplog):
    with caplog.at_level(logging.INFO, logger="api.access"):
        generated = client.get("/health")
        echoed = client.get("/health", headers={"X-Request-ID": "trace-abc"})
    assert len(generated.headers["x-request-id"]) == 32
    assert echoed.headers["x-request-id"] == "trace-abc"
    records = [r for r in caplog.records if r.name == "api.access"]
    assert records and records[-1].path == "/health" and records[-1].status == 200
    assert records[-1].duration_ms >= 0


def test_unsafe_request_id_is_replaced(client):
    response = client.get("/health", headers={"X-Request-ID": "x" * 200})
    assert response.headers["x-request-id"] != "x" * 200


def test_unhandled_errors_are_logged_but_never_leaked(caplog):
    @app.get("/__boom")
    def boom():  # pragma: no cover - route de test
        raise RuntimeError("secret internal detail")

    try:
        with caplog.at_level(logging.ERROR), TestClient(app, raise_server_exceptions=False) as c:
            response = c.get("/__boom")
    finally:
        app.router.routes = [r for r in app.router.routes if getattr(r, "path", "") != "/__boom"]
    assert response.status_code == 500
    assert "secret internal detail" not in response.text and "RuntimeError" not in response.text
    assert any("secret internal detail" in (r.exc_text or "") or r.exc_info for r in caplog.records)


# ---------- alertes ----------


def _seed_requests(rows):
    with session_scope() as db:
        db.query(RagRequest).delete()
        for status, latency in rows:
            db.add(
                RagRequest(
                    question="q",
                    status=status,
                    error="boom" if status == "error" else None,
                    latency_end_to_end=latency,
                )
            )


def test_alerts_on_error_rate_and_latency(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "ALERT_MIN_REQUESTS", 5)
    _seed_requests([("error", 1.0)] * 3 + [("success", 60.0)] * 3)
    kinds = {a["kind"] for a in metrics.evaluate_alerts()}
    assert kinds == {"error_rate", "latency"}
    assert any("50%" in a["message"] for a in metrics.evaluate_alerts())

    _seed_requests([("success", 2.0)] * 10)
    assert metrics.evaluate_alerts() == []
    _seed_requests([("error", 1.0)] * 3)  # volume trop faible pour être significatif
    assert metrics.evaluate_alerts() == []


def test_notification_has_a_cooldown_and_posts_to_the_webhook(monkeypatch, caplog):
    settings = get_settings()
    monkeypatch.setattr(settings, "ALERT_WEBHOOK_URL", "https://hooks.example/alert")
    monkeypatch.setattr(settings, "ALERT_COOLDOWN_MINUTES", 15)
    sent = []
    monkeypatch.setattr(alerts, "_post_webhook", lambda url, text: sent.append((url, text)))

    class ImmediateThread:
        def __init__(self, target, args, daemon):
            self._target, self._args = target, args

        def start(self):
            self._target(*self._args)

    monkeypatch.setattr(alerts.threading, "Thread", ImmediateThread)
    alerts.reset()
    _seed_requests([("error", 1.0)] * 6)

    with caplog.at_level(logging.ERROR, logger="api.alerts"):
        first = alerts.notify_if_needed(now=1000.0)
        again = alerts.notify_if_needed(now=1000.0 + 60)  # dans le délai de rappel
        later = alerts.notify_if_needed(now=1000.0 + 16 * 60)
    assert [a["kind"] for a in first] == ["error_rate"] and again == [] and len(later) == 1
    assert len(sent) == 2 and sent[0][0] == "https://hooks.example/alert"
    assert "Taux d'erreur" in sent[0][1]
    assert any(r.getMessage().startswith("ALERT error_rate") for r in caplog.records)


def test_webhook_failure_does_not_raise(monkeypatch, caplog):
    def failing_post(*args, **kwargs):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(alerts.httpx, "post", failing_post)
    with caplog.at_level(logging.ERROR, logger="api.alerts"):
        alerts._post_webhook("https://hooks.example/alert", "texte")
    assert any("webhook" in r.getMessage() for r in caplog.records)


def test_system_status_exposes_active_alerts(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "ALERT_MIN_REQUESTS", 5)
    _seed_requests([("error", 1.0)] * 6)
    token = client.post(
        "/api/v1/auth/login", json={"email": "boss@example.com", "password": "Sup3rS3cret!"}
    ).json()["token"]
    status = client.get(
        "/api/v1/admin/system/status", headers={"Authorization": f"Bearer {token}"}
    ).json()
    assert [a["kind"] for a in status["alerts"]] == ["error_rate"]


# ---------- traçage ----------


def test_no_tracing_callbacks_without_langfuse_keys(monkeypatch):
    monkeypatch.setattr(get_settings(), "LANGFUSE_PUBLIC_KEY", None)
    assert tracing_callbacks() == []


def test_missing_langfuse_package_degrades_gracefully(monkeypatch, caplog):
    settings = get_settings()
    monkeypatch.setattr(settings, "LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setattr(settings, "LANGFUSE_SECRET_KEY", "sk")
    monkeypatch.setitem(sys.modules, "langfuse", None)  # import impossible
    with caplog.at_level(logging.WARNING):
        assert tracing_callbacks() == []
    assert any("langfuse" in r.getMessage().lower() for r in caplog.records)


class RecordingHandler(BaseCallbackHandler):
    def __init__(self):
        self.chains: list[str] = []
        self.llm_runs = 0

    def on_chain_start(self, serialized, inputs, **kwargs):
        self.chains.append(kwargs.get("name") or "")

    def on_chat_model_start(self, serialized, messages, **kwargs):
        self.llm_runs += 1


async def test_langfuse_handler_receives_the_pipeline_run(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setattr(settings, "LANGFUSE_SECRET_KEY", "sk")
    handler = RecordingHandler()
    fake_module = types.ModuleType("langfuse.langchain")
    fake_module.CallbackHandler = lambda: handler  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "langfuse", types.ModuleType("langfuse"))
    monkeypatch.setitem(sys.modules, "langfuse.langchain", fake_module)

    deps = make_deps(SlowStreamingLLM(calls=[], delay=0))
    async for _ in stream_rag("3M capex?", deps=deps):
        pass
    assert {"analyze", "retrieve", "generate"} <= set(handler.chains)
    assert handler.llm_runs == 1


def test_export_runtime_env_publishes_langfuse_settings(monkeypatch):
    for var in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"):
        monkeypatch.delenv(var, raising=False)
    Settings(
        _env_file=None,
        LANGFUSE_PUBLIC_KEY="pk",
        LANGFUSE_SECRET_KEY="sk",
        LANGFUSE_HOST="https://lf",
    ).export_runtime_env()
    import os

    assert (os.environ["LANGFUSE_PUBLIC_KEY"], os.environ["LANGFUSE_HOST"]) == ("pk", "https://lf")
    for var in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"):
        monkeypatch.delenv(var, raising=False)
