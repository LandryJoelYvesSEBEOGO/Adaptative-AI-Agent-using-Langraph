"""Fournisseurs d'embeddings : hébergés (OpenAI, Cohere) ou local (Nomic)."""

import time
from functools import lru_cache
from typing import Protocol

import httpx

from config.settings import get_settings


class Embedder(Protocol):
    dim: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


def post_with_retry(
    client: httpx.Client, url: str, *, retries: int = 3, **kwargs
) -> httpx.Response:
    """POST avec nouvelle tentative sur 429 / 5xx (backoff exponentiel)."""
    for attempt in range(retries + 1):
        response = client.post(url, **kwargs)
        if response.status_code not in (429, 500, 502, 503, 504) or attempt == retries:
            response.raise_for_status()
            return response
        time.sleep(min(2**attempt, 10))
    raise AssertionError("unreachable")


class OpenAIEmbedder:
    def __init__(
        self, api_key: str, model: str, dim: int, transport: httpx.BaseTransport | None = None
    ):
        self.dim = dim
        self._model = model
        self._client = httpx.Client(
            base_url="https://api.openai.com/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60,
            transport=transport,
        )

    def _embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), 96):
            batch = texts[start : start + 96]
            response = post_with_retry(
                self._client,
                "/embeddings",
                json={"model": self._model, "input": batch, "dimensions": self.dim},
            )
            data = sorted(response.json()["data"], key=lambda item: item["index"])
            vectors.extend(item["embedding"] for item in data)
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]


class CohereEmbedder:
    def __init__(
        self, api_key: str, model: str, dim: int, transport: httpx.BaseTransport | None = None
    ):
        self.dim = dim
        self._model = model
        self._client = httpx.Client(
            base_url="https://api.cohere.com/v2",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60,
            transport=transport,
        )

    def _embed(self, texts: list[str], input_type: str) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), 96):
            response = post_with_retry(
                self._client,
                "/embed",
                json={
                    "model": self._model,
                    "texts": texts[start : start + 96],
                    "input_type": input_type,
                    "embedding_types": ["float"],
                    "output_dimension": self.dim,
                },
            )
            vectors.extend(response.json()["embeddings"]["float"])
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, "search_document")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "search_query")[0]


class NomicLocalEmbedder:
    """Modèle Nomic exécuté dans le processus (extra `ml`)."""

    def __init__(self, model: str, dim: int):
        from langchain_nomic.embeddings import NomicEmbeddings  # pyright: ignore[reportMissingImports]

        self.dim = dim
        self._embeddings = NomicEmbeddings(model=model, inference_mode="local")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embeddings.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embeddings.embed_query(text)


@lru_cache
def get_embedder() -> Embedder:
    settings = get_settings()
    provider, dim, model = (
        settings.EMBEDDING_PROVIDER,
        settings.EMBEDDING_DIM,
        settings.EMBEDDING_MODEL,
    )
    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY est requis pour EMBEDDING_PROVIDER=openai")
        return OpenAIEmbedder(settings.OPENAI_API_KEY, model or "text-embedding-3-small", dim)
    if provider == "cohere":
        if not settings.COHERE_API_KEY:
            raise RuntimeError("COHERE_API_KEY est requis pour EMBEDDING_PROVIDER=cohere")
        return CohereEmbedder(settings.COHERE_API_KEY, model or "embed-v4.0", dim)
    return NomicLocalEmbedder(model or settings.NomicEmbeddings_model, dim)
