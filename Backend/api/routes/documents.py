import re
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from api.dependencies import require_admin
from api.models.documents import DocumentOut
from api.services import document_service
from config.settings import get_settings
from src.ingestion.service import ingest_document

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["documents"],
    dependencies=[Depends(require_admin)],
)

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._\- ]")


def _clean_filename(raw: str) -> str:
    name = _SAFE_NAME.sub("_", Path(raw or "").name).strip(" .")
    return name or "document.pdf"


async def _read_pdf(upload: UploadFile) -> bytes:
    limit = get_settings().MAX_UPLOAD_MB * 1024 * 1024
    data = await upload.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(
            status_code=413,
            detail=f"Fichier trop volumineux (max {get_settings().MAX_UPLOAD_MB} Mo)",
        )
    if not data.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="Seuls les fichiers PDF sont acceptés")
    return data


@router.post("", response_model=DocumentOut, status_code=202)
async def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    company: Optional[str] = Form(None),
    fiscal_year: Optional[int] = Form(None),
    doc_type: Optional[str] = Form(None),
    current_user: dict = Depends(require_admin),
):
    """Reçoit un PDF et lance son indexation en tâche de fond (statut : GET /documents/{id})."""
    filename = _clean_filename(file.filename or "")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Seuls les fichiers PDF sont acceptés")
    data = await _read_pdf(file)

    doc = await run_in_threadpool(
        document_service.create_document,
        filename,
        current_user["id"],
        company,
        fiscal_year,
        doc_type,
    )
    if doc is None:
        raise HTTPException(status_code=409, detail="Un document portant ce nom existe déjà")
    await run_in_threadpool(Path(doc["source_path"]).write_bytes, data)
    background.add_task(ingest_document, doc["id"])
    return doc


@router.get("", response_model=List[DocumentOut])
def list_documents():
    return document_service.list_documents()


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str):
    doc = document_service.get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document introuvable")
    return doc


@router.post("/{document_id}/reindex", response_model=DocumentOut, status_code=202)
def reindex_document(document_id: str, background: BackgroundTasks):
    doc = document_service.get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document introuvable")
    background.add_task(ingest_document, document_id)
    return doc


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str):
    if not document_service.delete_document(document_id):
        raise HTTPException(status_code=404, detail="Document introuvable")
