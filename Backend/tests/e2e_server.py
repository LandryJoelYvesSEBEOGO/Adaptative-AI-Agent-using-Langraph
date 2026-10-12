"""Serveur de test de bout en bout (navigateur) : vraie API, base temporaire, pipeline simulé.

    uv run python -m tests.e2e_server [port]

Comptes : admin@example.com / admin-password-123. Un PDF de démonstration est servi pour
l'aperçu des citations. Le LLM est factice (réponse en Markdown, citations [1] et [2]).
"""

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("JWT_SECRET_KEY", "e2e-secret-" + "x" * 40)
os.environ.setdefault("RAG_DB_PATH", str(Path(tempfile.mkdtemp()) / "e2e.db"))
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("ADMIN_PASSWORD", "admin-password-123")
os.environ.setdefault("UPLOAD_DIR", tempfile.mkdtemp())
os.environ.setdefault("CORS_ORIGINS", "http://127.0.0.1:8080,http://localhost:8080")

from tests.api_stub import install  # noqa: E402

state = install()
state.llm.delay = 0.04
state.llm.reply = (
    "## Capital expenditure\n\n"
    "3M's **capital expenditure** in fiscal 2018 was $1,577 million [1].\n\n"
    "| Year | Capex (USD m) |\n|---|---|\n| 2018 | 1,577 |\n| 2017 | 1,373 |\n\n"
    "It is also discussed in the liquidity section [2]."
)


def make_demo_pdf() -> Path:
    from reportlab.pdfgen import canvas

    path = Path(os.environ["UPLOAD_DIR"]) / "demo.pdf"
    pdf = canvas.Canvas(str(path))
    for page in (1, 2):
        pdf.drawString(72, 760, f"3M 2018 Form 10-K - demonstration page {page}")
        pdf.drawString(72, 730, "Purchases of property, plant and equipment (1,577)")
        pdf.showPage()
    pdf.save()
    return path


def seed_documents() -> None:
    """Document de démonstration, référencé par les citations du faux retrieval."""
    from api.database import run_migrations, session_scope
    from api.db_models import Document

    run_migrations()
    with session_scope() as db:
        doc = Document(
            filename="3M_2018_10K.pdf",
            company="3M",
            fiscal_year=2018,
            doc_type="10-K",
            status="ready",
            pages=2,
            chunk_count=2,
            source_path=str(make_demo_pdf()),
        )
        db.add(doc)
        db.flush()
        from tests.fakes import retrieved

        def search(query, filters):
            from src.rag.search import SearchResult

            first, second = retrieved(1, page=1), retrieved(2, page=2)
            for item in (first, second):
                item.document_id = doc.id
            return SearchResult([first, second], 0.9)

        state.deps.search = search


if __name__ == "__main__":
    import uvicorn

    seed_documents()
    from api.main import app

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=int(sys.argv[1]) if len(sys.argv) > 1 else 8000,
        log_level="warning",
    )
