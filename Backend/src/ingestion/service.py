"""Ingestion d'un document : parsing -> chunks -> embeddings -> index, avec statut."""

import logging
from datetime import UTC, datetime
from pathlib import Path

from api.database import session_scope
from api.db_models import Document
from config.settings import get_settings
from src.ingestion.chunking import chunk_pages
from src.ingestion.metadata import parse_filename
from src.ingestion.parsing import parse_pdf
from src.rag.embeddings import Embedder, get_embedder
from src.rag.store import add_chunks

logger = logging.getLogger(__name__)

EMBED_BATCH = 64


def _set_status(document_id: str, status: str, **fields) -> None:
    with session_scope() as db:
        doc = db.get(Document, document_id)
        if doc is None:
            return
        doc.status = status
        doc.updated_at = datetime.now(UTC)
        for name, value in fields.items():
            setattr(doc, name, value)


def ingest_document(document_id: str, embedder: Embedder | None = None) -> None:
    """Indexe le PDF d'un document. Ne lève jamais : l'échec est consigné dans le document.

    Peut être rappelée pour réindexer (les chunks précédents sont remplacés)."""
    settings = get_settings()
    with session_scope() as db:
        doc = db.get(Document, document_id)
        if doc is None:
            return
        path, filename = doc.source_path, doc.filename
        given = (doc.company, doc.fiscal_year, doc.doc_type)
    _set_status(document_id, "processing", error=None)

    try:
        if not path or not Path(path).is_file():
            raise FileNotFoundError("fichier source introuvable")
        embedder = embedder or get_embedder()

        guessed = parse_filename(filename)
        company = given[0] or guessed.company
        fiscal_year = given[1] or guessed.fiscal_year
        doc_type = given[2] or guessed.doc_type

        pages = parse_pdf(path, parser=settings.INGEST_PARSER)
        if not pages:
            raise ValueError("aucun texte extractible (PDF scanné ?)")
        chunks = chunk_pages(pages, max_chars=settings.INGEST_CHUNK_MAX_CHARS)

        meta = guessed.__class__(company, fiscal_year, guessed.quarter, doc_type)
        texts = [chunk.embedding_text(meta) for chunk in chunks]
        vectors: list[list[float]] = []
        for start in range(0, len(texts), EMBED_BATCH):
            vectors.extend(embedder.embed_documents(texts[start : start + EMBED_BATCH]))

        rows = [
            {
                "ordinal": chunk.ordinal,
                "content": chunk.content,
                "embedding_text": text,
                "section": chunk.section or None,
                "kind": chunk.kind,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "company": company,
                "fiscal_year": fiscal_year,
                "doc_type": doc_type,
                "embedding": vector,
            }
            for chunk, text, vector in zip(chunks, texts, vectors, strict=True)
        ]
        with session_scope() as db:
            add_chunks(db, document_id, rows)
        _set_status(
            document_id,
            "ready",
            pages=pages[-1].number,
            chunk_count=len(rows),
            company=company,
            fiscal_year=fiscal_year,
            doc_type=doc_type,
        )
    except Exception as exc:
        logger.exception("Échec de l'ingestion du document %s", document_id)
        _set_status(document_id, "failed", error=f"{type(exc).__name__}: {exc}"[:500])
