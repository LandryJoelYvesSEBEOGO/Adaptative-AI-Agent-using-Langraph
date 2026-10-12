"""L3.7 : upload, ingestion asynchrone avec statut, réindexation et suppression."""

import io

import pytest
from fastapi.testclient import TestClient

from tests.api_stub import install

install()

import tempfile  # noqa: E402

from api.database import get_engine  # noqa: E402
from api.main import app  # noqa: E402
from config.settings import get_settings  # noqa: E402
from src.rag import embeddings  # noqa: E402
from src.rag.rerankers import NoReranker  # noqa: E402
from src.rag.search import search_documents  # noqa: E402
from tests.fakes import HashEmbedder  # noqa: E402

is_pg = get_settings().database_url.startswith("postgresql")


def make_pdf(text_lines: list[str]) -> bytes:
    canvas_mod = pytest.importorskip("reportlab.pdfgen.canvas")
    buffer = io.BytesIO()
    canvas = canvas_mod.Canvas(buffer)
    y = 760
    for line in text_lines:
        canvas.drawString(72, y, line)
        y -= 20
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()


@pytest.fixture(scope="module", autouse=True)
def isolated_uploads():
    settings = get_settings()
    settings.UPLOAD_DIR = tempfile.mkdtemp()
    settings.INGEST_PARSER = "pypdf"
    embeddings.get_embedder.cache_clear()
    original = embeddings.get_embedder
    embeddings.get_embedder = lambda: HashEmbedder()  # type: ignore[assignment]
    import src.ingestion.service as service

    service.get_embedder = lambda: HashEmbedder()  # type: ignore[assignment]
    yield
    embeddings.get_embedder = original


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _login(client, email, password):
    return {
        "Authorization": "Bearer "
        + client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()[
            "token"
        ]
    }


@pytest.fixture(scope="module")
def admin(client):
    return _login(client, "boss@example.com", "Sup3rS3cret!")


@pytest.fixture(scope="module")
def user(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "doc-user@example.com", "password": "Passw0rd!", "name": "U"},
    )
    return {"Authorization": f"Bearer {r.json()['token']}"}


def upload(client, headers, name, content, **fields):
    return client.post(
        "/api/v1/documents",
        files={"file": (name, content, "application/pdf")},
        data={k: str(v) for k, v in fields.items()},
        headers=headers,
    )


def test_documents_require_admin(client, user):
    pdf = make_pdf(["hello"])
    assert client.get("/api/v1/documents").status_code in (401, 403)
    assert upload(client, user, "ACME_2020_10K.pdf", pdf).status_code == 403
    assert client.get("/api/v1/documents", headers=user).status_code == 403


def test_upload_validation(client, admin):
    assert upload(client, admin, "notes.txt", b"%PDF-1.4 fake").status_code == 415
    assert upload(client, admin, "fake.pdf", b"<html>not a pdf</html>").status_code == 415
    settings = get_settings()
    settings.MAX_UPLOAD_MB = 1
    try:
        big = b"%PDF-" + b"0" * (1024 * 1024 + 10)
        assert upload(client, admin, "big.pdf", big).status_code == 413
    finally:
        settings.MAX_UPLOAD_MB = 50


def test_filename_is_sanitized_and_duplicates_rejected(client, admin):
    pdf = make_pdf(["Total revenue was 5 million."])
    r = upload(client, admin, "../../etc/Evil Name_2021_10K.pdf", pdf)
    assert r.status_code == 202
    assert "/" not in r.json()["filename"] and r.json()["filename"].endswith("_2021_10K.pdf")
    assert upload(client, admin, "../../etc/Evil Name_2021_10K.pdf", pdf).status_code == 409


@pytest.mark.skipif(is_pg, reason="vérifie l'échec attendu hors PostgreSQL")
def test_ingestion_failure_is_reported_in_status_not_raised(client, admin):
    r = upload(client, admin, "NOPG_2020_10K.pdf", make_pdf(["Revenue 1"]))
    doc = client.get(f"/api/v1/documents/{r.json()['id']}", headers=admin).json()
    assert doc["status"] == "failed" and doc["error"]


def test_unreadable_pdf_ends_failed_with_message(client, admin):
    r = upload(client, admin, "BROKEN_2020_10K.pdf", b"%PDF-1.4 truncated garbage")
    doc = client.get(f"/api/v1/documents/{r.json()['id']}", headers=admin).json()
    assert doc["status"] == "failed" and doc["error"]


@pytest.mark.skipif(not is_pg, reason="nécessite PostgreSQL + pgvector")
class TestIngestionEndToEnd:
    def test_upload_then_search_then_reindex_then_delete(self, client, admin):
        pdf = make_pdf(
            [
                "Item 7. Liquidity",
                "Purchases of property, plant and equipment were 4242 million in 2021.",
            ]
        )
        response = upload(client, admin, "ACME_2021_10K.pdf", pdf)
        assert response.status_code == 202
        doc_id = response.json()["id"]

        # TestClient exécute la tâche de fond avant de rendre la main
        doc = client.get(f"/api/v1/documents/{doc_id}", headers=admin).json()
        assert doc["status"] == "ready", doc
        assert (doc["company"], doc["fiscal_year"], doc["doc_type"]) == ("ACME", 2021, "10-K")
        assert doc["pages"] == 1 and doc["chunk_count"] >= 1

        result = search_documents(
            "purchases of property plant equipment ACME 2021",
            embedder=HashEmbedder(),
            reranker=NoReranker(),
            top_k=3,
        )
        top = result.documents[0]
        assert top.filename == "ACME_2021_10K.pdf" and top.page_start == 1
        assert "4242" in top.content

        listing = client.get("/api/v1/documents", headers=admin).json()
        assert doc_id in [d["id"] for d in listing]

        assert client.post(f"/api/v1/documents/{doc_id}/reindex", headers=admin).status_code == 202
        again = client.get(f"/api/v1/documents/{doc_id}", headers=admin).json()
        assert (
            again["status"] == "ready" and again["chunk_count"] == doc["chunk_count"]
        )  # pas de doublons

        assert client.delete(f"/api/v1/documents/{doc_id}", headers=admin).status_code == 204
        assert client.get(f"/api/v1/documents/{doc_id}", headers=admin).status_code == 404
        gone = search_documents(
            "purchases of property plant equipment ACME 2021",
            embedder=HashEmbedder(),
            reranker=NoReranker(),
        )
        assert all(d.filename != "ACME_2021_10K.pdf" for d in gone.documents)

    def test_explicit_metadata_overrides_filename(self, client, admin):
        r = upload(
            client,
            admin,
            "report.pdf",
            make_pdf(["Net sales 10"]),
            company="Globex",
            fiscal_year=2019,
            doc_type="10-Q",
        )
        doc = client.get(f"/api/v1/documents/{r.json()['id']}", headers=admin).json()
        assert (doc["company"], doc["fiscal_year"], doc["doc_type"]) == ("Globex", 2019, "10-Q")


def test_engine_dialect_sanity():
    assert get_engine().dialect.name in {"sqlite", "postgresql"}
