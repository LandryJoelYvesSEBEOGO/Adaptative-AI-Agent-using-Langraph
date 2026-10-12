from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import select

from api.database import session_scope
from api.db_models import Document
from config.settings import get_settings


def _to_dict(doc: Document) -> Dict:
    return {
        "id": doc.id,
        "filename": doc.filename,
        "company": doc.company,
        "fiscal_year": doc.fiscal_year,
        "doc_type": doc.doc_type,
        "status": doc.status,
        "pages": doc.pages,
        "chunk_count": doc.chunk_count,
        "error": doc.error,
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
    }


def upload_dir() -> Path:
    path = Path(get_settings().UPLOAD_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_document(
    filename: str,
    owner_id: Optional[str],
    company: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    doc_type: Optional[str] = None,
) -> Optional[Dict]:
    """Crée la fiche d'un document en attente ; None si le nom de fichier existe déjà."""
    with session_scope() as db:
        if db.scalar(select(Document.id).where(Document.filename == filename)):
            return None
        doc = Document(
            filename=filename,
            owner_id=owner_id,
            company=company,
            fiscal_year=fiscal_year,
            doc_type=doc_type,
            status="pending",
        )
        db.add(doc)
        db.flush()
        doc.source_path = str(upload_dir() / f"{doc.id}.pdf")
        return {**_to_dict(doc), "source_path": doc.source_path}


def list_documents() -> List[Dict]:
    with session_scope() as db:
        return [
            _to_dict(d) for d in db.scalars(select(Document).order_by(Document.created_at.desc()))
        ]


def get_document(document_id: str) -> Optional[Dict]:
    with session_scope() as db:
        doc = db.get(Document, document_id)
        return {**_to_dict(doc), "source_path": doc.source_path} if doc else None


def delete_document(document_id: str) -> bool:
    """Supprime la fiche (les chunks suivent en cascade) et le fichier source."""
    with session_scope() as db:
        doc = db.get(Document, document_id)
        if doc is None:
            return False
        source = doc.source_path
        db.delete(doc)
    if source:
        Path(source).unlink(missing_ok=True)
    return True
