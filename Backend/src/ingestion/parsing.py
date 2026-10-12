"""Lecture d'un PDF en Markdown paginé : Docling (tableaux conservés) ou pypdf (texte brut)."""

from pathlib import Path

from src.ingestion.chunking import Page


def parse_pdf(path: str | Path, parser: str = "docling") -> list[Page]:
    if parser == "docling":
        return _parse_docling(Path(path))
    if parser == "pypdf":
        return _parse_pypdf(Path(path))
    raise ValueError(f"Parseur inconnu : {parser!r} (docling | pypdf)")


def _parse_docling(path: Path) -> list[Page]:
    from docling.document_converter import DocumentConverter

    document = DocumentConverter().convert(str(path)).document
    pages = []
    for number in sorted(document.pages):
        markdown = document.export_to_markdown(page_no=number)
        if markdown.strip():
            pages.append(Page(number, markdown))
    return pages


def _parse_pypdf(path: Path) -> list[Page]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(Page(index, text))
    return pages
