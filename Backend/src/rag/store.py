"""Stockage et recherche hybride des chunks : pgvector (dense) + plein texte PostgreSQL
(lexical), fusionnés par rangs réciproques (RRF). PostgreSQL uniquement."""

import re
from dataclasses import dataclass, field

from sqlalchemy import cast, func, literal, select
from sqlalchemy.dialects.postgresql import REGCONFIG
from sqlalchemy.orm import Session

from api.database import get_engine, session_scope
from api.db_models import Chunk, Document


@dataclass
class Retrieved:
    chunk_id: int
    document_id: str
    filename: str
    content: str
    section: str | None
    kind: str
    page_start: int | None
    page_end: int | None
    company: str | None
    fiscal_year: int | None
    doc_type: str | None
    fusion_score: float = 0.0
    rerank_score: float | None = None


@dataclass
class Filters:
    company: str | None = None
    fiscal_year: int | None = None
    doc_type: str | None = None
    document_ids: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.company or self.fiscal_year or self.doc_type or self.document_ids)


def reciprocal_rank_fusion(rankings: list[list[int]], k: int = 60) -> list[tuple[int, float]]:
    """Fusionne plusieurs classements (listes d'ids du meilleur au moins bon).

    score(id) = Σ 1 / (k + rang), rang à partir de 1. Retourne (id, score) décroissants.
    """
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))


_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9&.\-]*")


def to_or_tsquery(text: str) -> str | None:
    """Question -> requête `to_tsquery` en OU sur les mots significatifs (les mots vides sont
    écartés par PostgreSQL). Un ET strict ne ramènerait presque rien pour une phrase longue."""
    words = {w.strip(".-").lower() for w in _TOKEN.findall(text)}
    words = {re.sub(r"[^a-z0-9]", "", w) for w in words if len(w) >= 3}
    words.discard("")
    return " | ".join(sorted(words)) or None


def _require_postgres() -> None:
    if get_engine().dialect.name != "postgresql":
        raise RuntimeError(
            "La recherche vectorielle nécessite PostgreSQL + pgvector (DATABASE_URL=postgresql+psycopg://…)"
        )


def _conditions(filters: Filters | None) -> list:
    if filters is None:
        return []
    conditions = []
    if filters.company:
        conditions.append(func.lower(Chunk.company) == filters.company.lower())
    if filters.fiscal_year:
        conditions.append(Chunk.fiscal_year == filters.fiscal_year)
    if filters.doc_type:
        conditions.append(Chunk.doc_type == filters.doc_type)
    if filters.document_ids:
        conditions.append(Chunk.document_id.in_(filters.document_ids))
    return conditions


def add_chunks(db: Session, document_id: str, rows: list[dict]) -> None:
    """Insère les chunks d'un document (remplace les précédents)."""
    db.query(Chunk).filter(Chunk.document_id == document_id).delete()
    db.add_all(Chunk(document_id=document_id, **row) for row in rows)


def dense_search(db: Session, embedding: list[float], k: int, filters: Filters | None) -> list[int]:
    stmt = (
        select(Chunk.id)
        .where(*_conditions(filters))
        .order_by(Chunk.embedding.cosine_distance(embedding))
        .limit(k)
    )
    return list(db.scalars(stmt))


def lexical_search(db: Session, text: str, k: int, filters: Filters | None) -> list[int]:
    query = to_or_tsquery(text)
    if not query:
        return []
    tsquery = func.to_tsquery(cast(literal("english"), REGCONFIG), query)
    stmt = (
        select(Chunk.id)
        .where(Chunk.tsv.op("@@")(tsquery), *_conditions(filters))
        .order_by(func.ts_rank_cd(Chunk.tsv, tsquery).desc())
        .limit(k)
    )
    return list(db.scalars(stmt))


def hybrid_search(
    text: str,
    embedding: list[float],
    k: int = 20,
    candidates: int = 40,
    rrf_k: int = 60,
    filters: Filters | None = None,
) -> list[Retrieved]:
    """Recherche hybride : les `k` meilleurs chunks après fusion RRF dense + lexical."""
    _require_postgres()
    with session_scope() as db:
        dense = dense_search(db, embedding, candidates, filters)
        lexical = lexical_search(db, text, candidates, filters)
        fused = reciprocal_rank_fusion([dense, lexical], k=rrf_k)[:k]
        if not fused:
            return []
        rows = db.execute(
            select(Chunk, Document.filename)
            .join(Document, Document.id == Chunk.document_id)
            .where(Chunk.id.in_([chunk_id for chunk_id, _ in fused]))
        ).all()
        by_id = {chunk.id: (chunk, filename) for chunk, filename in rows}
        return [
            Retrieved(
                chunk_id=chunk_id,
                document_id=by_id[chunk_id][0].document_id,
                filename=by_id[chunk_id][1],
                content=by_id[chunk_id][0].content,
                section=by_id[chunk_id][0].section,
                kind=by_id[chunk_id][0].kind,
                page_start=by_id[chunk_id][0].page_start,
                page_end=by_id[chunk_id][0].page_end,
                company=by_id[chunk_id][0].company,
                fiscal_year=by_id[chunk_id][0].fiscal_year,
                doc_type=by_id[chunk_id][0].doc_type,
                fusion_score=score,
            )
            for chunk_id, score in fused
            if chunk_id in by_id
        ]


def list_companies() -> list[str]:
    """Sociétés ayant au moins un document prêt (sert à détecter la société d'une question)."""
    if get_engine().dialect.name != "postgresql":
        return []
    with session_scope() as db:
        companies = list(
            db.scalars(
                select(Chunk.company)
                .where(Chunk.company.is_not(None))
                .distinct()
                .order_by(Chunk.company)
            )
        )
        return [c for c in companies if c]
