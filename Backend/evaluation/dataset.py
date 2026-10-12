"""Chargement du jeu de référence FinanceBench."""

import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Example:
    id: str
    question: str
    reference_answer: str
    company: str = ""
    doc_name: str = ""
    question_type: str = ""
    evidence: list[dict] = field(default_factory=list)

    @property
    def evidence_docs(self) -> set[str]:
        names = {normalize_doc_name(e.get("doc_name", "")) for e in self.evidence}
        names.add(normalize_doc_name(self.doc_name))
        names.discard("")
        return names

    @property
    def evidence_pages(self) -> set[tuple[str, int]]:
        """Couples (document normalisé, numéro de page) portant la réponse."""
        pages = set()
        for e in self.evidence:
            page = e.get("evidence_page_num")
            if page is not None:
                pages.add((normalize_doc_name(e.get("doc_name", self.doc_name)), int(page)))
        return pages


def normalize_doc_name(name: str) -> str:
    """`3M_2018_10K.pdf` et `3m 2018 10k` désignent le même document."""
    name = re.sub(r"\.pdf$", "", name.strip(), flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9]", "", name.lower())


def load_dataset(path: str | Path, limit: int | None = None, seed: int = 0) -> list[Example]:
    """Lit un fichier JSONL. `limit` extrait un sous-ensemble reproductible (même `seed`)."""
    examples = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            examples.append(
                Example(
                    id=str(row.get("financebench_id") or row.get("id") or len(examples)),
                    question=row["question"],
                    reference_answer=str(row["answer"]),
                    company=row.get("company", ""),
                    doc_name=row.get("doc_name", ""),
                    question_type=row.get("question_type", ""),
                    evidence=row.get("evidence") or [],
                )
            )
    if limit is not None and limit < len(examples):
        examples = sorted(random.Random(seed).sample(examples, limit), key=lambda e: e.id)
    return examples
