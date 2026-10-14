"""Métadonnées métier déduites du nom de fichier (convention FinanceBench)."""

import re
from dataclasses import dataclass
from pathlib import Path

# Exemples : 3M_2018_10K.pdf, AMERICANEXPRESS_2022_10K.pdf, 3M_2023Q2_10Q.pdf, AES_2022_8K.pdf
_PATTERN = re.compile(
    r"^(?P<company>.+?)_(?P<year>(?:19|20)\d{2})(?:Q(?P<quarter>[1-4]))?_(?P<type>10-?K|10-?Q|8-?K|[A-Z0-9]+)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DocumentMetadata:
    company: str | None = None
    fiscal_year: int | None = None
    quarter: int | None = None
    doc_type: str | None = None  # normalisé : 10-K, 10-Q, 8-K…


def _normalize_type(raw: str) -> str:
    upper = raw.upper().replace("-", "")
    if upper in {"10K", "10Q", "8K"}:
        return f"{upper[:-1]}-{upper[-1]}"
    return raw.upper()


def parse_filename(filename: str) -> DocumentMetadata:
    """Extrait société, exercice, trimestre et type depuis `SOCIETE_ANNEE[Qn]_TYPE.pdf`."""
    match = _PATTERN.match(Path(filename).stem)
    if not match:
        return DocumentMetadata()
    return DocumentMetadata(
        company=match["company"].replace("-", " ").strip(),
        fiscal_year=int(match["year"]),
        quarter=int(match["quarter"]) if match["quarter"] else None,
        doc_type=_normalize_type(match["type"]),
    )
