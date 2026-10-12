"""Indexe un dossier de PDF (corpus fixe, ex. rapports 10-K / 10-Q de FinanceBench).

    uv run python -m scripts.ingest_corpus data/raw [--parser pypdf] [--force]

Les fichiers restent à leur emplacement (pas de copie). Un document déjà indexé
(`ready`) est ignoré sauf avec --force. Le nom du fichier doit suivre la convention
SOCIETE_ANNEE_10K.pdf pour renseigner société, exercice et type de document.
"""

import argparse
import sys
from pathlib import Path

from sqlalchemy import select

from api.database import run_migrations, session_scope
from api.db_models import Document
from config.settings import get_settings
from src.ingestion.service import ingest_document


def register(path: Path) -> tuple[str, str]:
    """Crée ou retrouve la fiche du fichier ; retourne (id, statut)."""
    with session_scope() as db:
        doc = db.scalar(select(Document).where(Document.filename == path.name))
        if doc is None:
            doc = Document(filename=path.name, status="pending")
            db.add(doc)
        doc.source_path = str(path.resolve())
        db.flush()
        return doc.id, doc.status


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("folder", type=Path)
    parser.add_argument("--parser", choices=["docling", "pypdf"], default=None)
    parser.add_argument("--force", action="store_true", help="réindexer aussi les documents prêts")
    args = parser.parse_args()

    if args.parser:
        get_settings().INGEST_PARSER = args.parser
    pdfs = sorted(args.folder.glob("*.pdf"))
    if not pdfs:
        print(f"Aucun PDF dans {args.folder}", file=sys.stderr)
        return 1

    run_migrations()
    failed = 0
    for index, pdf in enumerate(pdfs, start=1):
        document_id, status = register(pdf)
        if status == "ready" and not args.force:
            print(f"[{index}/{len(pdfs)}] {pdf.name} : déjà indexé")
            continue
        ingest_document(document_id)
        with session_scope() as db:
            doc = db.get(Document, document_id)
            assert doc is not None
            print(
                f"[{index}/{len(pdfs)}] {pdf.name} : {doc.status}"
                + (f" ({doc.chunk_count} chunks)" if doc.status == "ready" else f" - {doc.error}")
            )
            failed += doc.status == "failed"
    print(f"Terminé : {len(pdfs) - failed} indexés, {failed} en échec")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
