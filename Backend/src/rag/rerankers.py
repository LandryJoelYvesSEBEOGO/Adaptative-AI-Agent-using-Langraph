"""Rerankers : Cohere (hébergé), cross-encoder local, ou aucun.

Chaque reranker retourne des couples (indice du passage, score) triés par pertinence
décroissante. Les scores sont ramenés entre 0 et 1 pour que le seuil `RERANK_MIN_SCORE`
ait le même sens quel que soit le fournisseur ; `None` signifie « pas de signal ».
"""

import math
from functools import lru_cache
from typing import Protocol

import httpx

from config.settings import get_settings
from src.rag.embeddings import post_with_retry


class Reranker(Protocol):
    def rerank(
        self, query: str, texts: list[str], top_n: int
    ) -> list[tuple[int, float | None]]: ...


class NoReranker:
    def rerank(self, query: str, texts: list[str], top_n: int) -> list[tuple[int, float | None]]:
        return [(i, None) for i in range(min(top_n, len(texts)))]


class CohereReranker:
    def __init__(
        self, api_key: str, model: str = "rerank-v3.5", transport: httpx.BaseTransport | None = None
    ):
        self._model = model
        self._client = httpx.Client(
            base_url="https://api.cohere.com/v2",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60,
            transport=transport,
        )

    def rerank(self, query: str, texts: list[str], top_n: int) -> list[tuple[int, float | None]]:
        if not texts:
            return []
        response = post_with_retry(
            self._client,
            "/rerank",
            json={"model": self._model, "query": query, "documents": texts, "top_n": top_n},
        )
        results = response.json()["results"]
        return [
            (r["index"], float(r["relevance_score"]))
            for r in sorted(results, key=lambda r: -r["relevance_score"])
        ]


class LocalCrossEncoderReranker:
    def __init__(self, model_name: str):
        from sentence_transformers import CrossEncoder  # type: ignore[import-not-found]

        self._model = CrossEncoder(model_name)

    def rerank(self, query: str, texts: list[str], top_n: int) -> list[tuple[int, float | None]]:
        if not texts:
            return []
        logits = self._model.predict([(query, text) for text in texts])
        scored: list[tuple[int, float | None]] = [
            (i, 1 / (1 + math.exp(-float(x)))) for i, x in enumerate(logits)
        ]
        return sorted(scored, key=lambda pair: -(pair[1] or 0.0))[:top_n]


@lru_cache
def get_reranker() -> Reranker:
    settings = get_settings()
    if settings.RERANKER_PROVIDER == "cohere":
        if not settings.COHERE_API_KEY:
            raise RuntimeError("COHERE_API_KEY est requis pour RERANKER_PROVIDER=cohere")
        return CohereReranker(settings.COHERE_API_KEY)
    if settings.RERANKER_PROVIDER == "local":
        return LocalCrossEncoderReranker(settings.RERANKER_MODEL)
    return NoReranker()
