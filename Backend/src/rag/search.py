"""Recherche complète : embedding de la question, hybride pgvector + plein texte, rerank."""

from dataclasses import dataclass

from config.settings import get_settings
from src.rag.embeddings import Embedder, get_embedder
from src.rag.rerankers import Reranker, get_reranker
from src.rag.store import Filters, Retrieved, hybrid_search


@dataclass
class SearchResult:
    documents: list[Retrieved]
    best_score: float | None  # meilleur score de rerank (0-1) ; None si pas de reranker

    @property
    def is_confident(self) -> bool:
        """Vrai si la recherche documentaire suffit (sinon : recherche web)."""
        if self.best_score is None:
            return bool(self.documents)
        return self.best_score >= get_settings().RERANK_MIN_SCORE


def search_documents(
    query: str,
    filters: Filters | None = None,
    *,
    top_k: int | None = None,
    embedder: Embedder | None = None,
    reranker: Reranker | None = None,
) -> SearchResult:
    settings = get_settings()
    top_k = top_k or settings.RERANKER_FINAL_K
    embedder = embedder or get_embedder()
    reranker = reranker or get_reranker()

    candidates = hybrid_search(
        query,
        embedder.embed_query(query),
        k=settings.RERANKER_TOP_K,
        candidates=settings.SEARCH_CANDIDATES,
        rrf_k=settings.RRF_K,
        filters=filters,
    )
    if not candidates:
        return SearchResult([], None)

    ranked = reranker.rerank(query, [c.content for c in candidates], top_k)
    documents = []
    for index, score in ranked:
        candidates[index].rerank_score = score
        documents.append(candidates[index])
    scores = [d.rerank_score for d in documents if d.rerank_score is not None]
    return SearchResult(documents, max(scores) if scores else None)
