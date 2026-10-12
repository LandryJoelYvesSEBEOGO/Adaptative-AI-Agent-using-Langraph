"""Tests de la couche base de données (L2.3) : migrations, services, métriques."""

import pytest

from tests.api_stub import install

install()

from pathlib import Path  # noqa: E402

from alembic.autogenerate import compare_metadata  # noqa: E402
from alembic.config import Config as AlembicConfig  # noqa: E402
from alembic.migration import MigrationContext  # noqa: E402
from sqlalchemy import inspect  # noqa: E402

from alembic import command  # noqa: E402
from api.database import (  # noqa: E402
    Base,
    get_engine,
    include_object,
    run_migrations,
    session_scope,
)
from api.services import conversation_service as conv  # noqa: E402
from api.services import metrics_service as metrics  # noqa: E402
from api.services.auth_service import (  # noqa: E402
    authenticate_user,
    create_user,
    seed_initial_users,
)


@pytest.fixture(scope="module", autouse=True)
def migrated():
    run_migrations()


def test_expected_tables_exist():
    tables = set(inspect(get_engine()).get_table_names())
    assert {
        "users",
        "conversations",
        "messages",
        "rag_requests",
        "feedback",
        "documents",
    } <= tables


def test_models_match_migrations():
    """Le schéma créé par Alembic doit être identique aux modèles ORM."""
    with get_engine().connect() as connection:
        context = MigrationContext.configure(
            connection,
            opts={
                "include_object": lambda *a: include_object(*a, connection.dialect.name),
            },
        )
        diff = compare_metadata(context, Base.metadata)
    assert diff == []


def test_migration_downgrade_and_upgrade():
    backend = Path(__file__).parent.parent
    cfg = AlembicConfig(str(backend / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend / "alembic"))
    command.downgrade(cfg, "base")
    assert "users" not in inspect(get_engine()).get_table_names()
    command.upgrade(cfg, "head")
    assert "users" in inspect(get_engine()).get_table_names()


def test_users_are_persistent_and_unique():
    user = create_user("Dup@Example.com", "pw123456", "Dup")
    assert user and user["role"] == "user"
    assert create_user("dup@example.com", "other", "Dup2") is None
    assert authenticate_user("dup@example.com", "pw123456")["id"] == user["id"]
    assert authenticate_user("dup@example.com", "wrong") is None


def test_seed_admin_from_environment_is_idempotent():
    seed_initial_users()
    seed_initial_users()
    admin = authenticate_user("boss@example.com", "Sup3rS3cret!")
    assert admin and admin["role"] == "admin"


def test_conversations_are_isolated_per_user():
    a = create_user("conv-a@example.com", "pw123456", "A")
    b = create_user("conv-b@example.com", "pw123456", "B")
    c = conv.create_conversation(a["id"], "titre")
    assert conv.get_conversation(c["id"], a["id"])
    assert conv.get_conversation(c["id"], b["id"]) is None
    assert [x["id"] for x in conv.list_conversations(b["id"])] == []

    conv.add_message(c["id"], "user", "bonjour")
    m = conv.add_message(c["id"], "assistant", "salut", [{"id": 1, "source": "x.pdf"}])
    messages = conv.list_messages(c["id"])
    assert [x["role"] for x in messages] == ["user", "assistant"]
    assert messages[1]["citations"] == [{"id": 1, "source": "x.pdf"}]
    assert conv.add_feedback(m["id"], b["id"], "thumbs_up") is False
    assert conv.add_feedback(m["id"], a["id"], "thumbs_up") is True
    assert conv.add_feedback(m["id"], a["id"], "thumbs_down") is True  # remplacement


def test_metrics_aggregation():
    u = create_user("metrics@example.com", "pw123456", "M")
    c = conv.create_conversation(u["id"], "m")
    for status, error in (("success", None), ("success", None), ("error", "LLM timeout")):
        metrics.record_request(
            conversation_id=c["id"],
            user_id=u["id"],
            question="Quelle est la marge de 3M ?",
            status=status,
            error=error,
            latencies={"end_to_end": 2.0, "retrieval": 0.5},
            docs_count=3,
            response_length=100,
            answer_quality_score=0.8,
            answer_quality_scores={"overall_score": 0.8},
        )
    overview = metrics.get_metrics_overview()
    assert overview["total_requests"] >= 3
    assert overview["error_count"] >= 1
    assert overview["requests_today"] >= 3
    assert metrics.get_error_distribution()["timeout"] >= 1
    assert metrics.get_recent_requests(1)[0]["user"] == "metrics@example.com"
    assert metrics.get_requests_chart_data(7)[-1]["requests"] >= 3
    assert metrics.get_latency_trend(7)[-1]["endToEnd"] == pytest.approx(2.0)
    stats = {s["name"]: s for s in metrics.get_latency_component_stats()}
    assert stats["End-to-End"]["avg"] == pytest.approx(2.0)


def test_system_status_reflects_the_real_state(monkeypatch):
    from api.db_models import Document

    with session_scope() as db:
        db.query(Document).filter(Document.filename == "status-probe.pdf").delete()
    monkeypatch.setenv("GROQ_API_KEY", "")
    from config.settings import get_settings

    get_settings.cache_clear()
    try:
        status = metrics.get_system_status()
        assert status["llm_status"] == "Down"  # pas de clé configurée
        before = status["documents_ready"]

        with session_scope() as db:
            db.add(Document(filename="status-probe.pdf", status="ready"))
        monkeypatch.setenv("GROQ_API_KEY", "k")
        get_settings.cache_clear()
        after = metrics.get_system_status()
        assert after["documents_ready"] == before + 1 and after["rag_pipeline"] == "Active"
        assert after["llm_status"] in {"Operational", "Degraded"}
        assert after["vector_db"] in {"Connected", "Disconnected"}
    finally:
        get_settings.cache_clear()
        with session_scope() as db:
            db.query(Document).filter(Document.filename == "status-probe.pdf").delete()
