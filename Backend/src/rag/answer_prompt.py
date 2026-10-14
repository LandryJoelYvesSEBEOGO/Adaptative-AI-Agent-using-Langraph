"""Prompt de génération et mise en forme des sources / citations."""

import re

from src.rag.schemas import SourceDocument

SYSTEM_PROMPT = """You are a financial analyst assistant answering questions about companies' \
SEC filings (10-K, 10-Q, 8-K).

Rules:
- Use ONLY the numbered sources provided. Never rely on outside knowledge for figures.
- Cite every fact with its source number in square brackets, e.g. "Net sales were $32.8 billion [1]."
- Always give figures with their unit and period (fiscal year or quarter).
- If the sources do not contain the answer, say so explicitly and state what is missing.
- When sources disagree, point out the difference rather than choosing silently.
- Tables are given in Markdown; read rows and columns carefully.
- Be concise. Answer in the language of the question."""

MAX_SOURCE_CHARS = 3500


def describe(doc: SourceDocument) -> str:
    if doc.is_web:
        return f"web: {doc.source}"
    parts = [doc.company, str(doc.fiscal_year) if doc.fiscal_year else None, doc.doc_type]
    label = " ".join(p for p in parts if p) or doc.source
    if doc.page:
        label += f", p.{doc.page}"
    if doc.section:
        label += f", {doc.section}"
    return label


def build_user_prompt(question: str, documents: list[SourceDocument]) -> str:
    if documents:
        sources = "\n\n".join(
            f"[{d.number}] ({describe(d)})\n{d.content[:MAX_SOURCE_CHARS]}" for d in documents
        )
    else:
        sources = "(no source found)"
    return f"Sources:\n{sources}\n\nQuestion: {question}"


def cited_numbers(answer: str) -> list[int]:
    """Numéros de sources cités dans la réponse, y compris les listes « [1, 3] »."""
    numbers: set[int] = set()
    for group in re.findall(r"\[(\d+(?:\s*[,;]\s*\d+)*)\]", answer):
        numbers.update(int(n) for n in re.findall(r"\d+", group))
    return sorted(numbers)


def build_citations(answer: str, documents: list[SourceDocument]) -> list[dict]:
    """Citations structurées pour l'API : uniquement les sources réellement citées ; à défaut
    (réponse sans marqueur), les sources fournies au modèle."""
    by_number = {d.number: d for d in documents}
    numbers = [n for n in cited_numbers(answer) if n in by_number] or sorted(by_number)
    return [
        {
            "id": n,
            "source": by_number[n].source,
            "excerpt": by_number[n].content[:300].strip(),
            "metadata": {
                "page": by_number[n].page,
                "section": by_number[n].section,
                "company": by_number[n].company,
                "fiscal_year": by_number[n].fiscal_year,
                "doc_type": by_number[n].doc_type,
                "document_id": by_number[n].document_id,
                "kind": by_number[n].kind,
                "is_web": by_number[n].is_web,
            },
        }
        for n in numbers
    ]
