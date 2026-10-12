"""L3.3 : fusion RRF, fournisseurs hébergés (simulés) et recherche hybride sur PostgreSQL."""

import hashlib
import math
import re

import httpx
import pytest

from tests.api_stub import install

install()

from api.database import get_engine, run_migrations, session_scope  # noqa: E402
from api.db_models import Chunk, Document  # noqa: E402
from config.settings import get_settings  # noqa: E402
from src.rag.embeddings import CohereEmbedder, OpenAIEmbedder  # noqa: E402
from src.rag.rerankers import CohereReranker, NoReranker  # noqa: E402
from src.rag.search import SearchResult, search_documents  # noqa: E402
from src.rag.store import (  # noqa: E402
    Filters,
    add_chunks,
    hybrid_search,
    reciprocal_rank_fusion,
    to_or_tsquery,
)

# ---------- fonctions pures ----------


def test_rrf_rewards_items_ranked_by_both_branches():
    fused = reciprocal_rank_fusion([[1, 2, 3], [3, 1, 4]], k=60)
    order = [item for item, _ in fused]
    assert order[:2] == [1, 3]  # présents dans les deux classements
    assert set(order) == {1, 2, 3, 4}
    assert fused[0][1] == pytest.approx(1 / 61 + 1 / 62)


def test_rrf_handles_empty_branches():
    assert reciprocal_rank_fusion([[], []]) == []
    assert [i for i, _ in reciprocal_rank_fusion([[7, 8], []])] == [7, 8]


def test_to_or_tsquery():
    query = to_or_tsquery("Net sales of AT&T in fiscal 2019")
    assert query is not None
    assert {"net", "sales", "fiscal", "2019", "att"} <= set(query.split(" | "))
    assert to_or_tsquery("a b ?!") is None


# ---------- fournisseurs hébergés (HTTP simulé) ----------


def test_openai_embedder_batches_and_orders_results():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        body = json.loads(request.read())
        calls.append(body)
        assert request.headers["authorization"] == "Bearer k"
        assert body["dimensions"] == 4
        # renvoie volontairement dans le désordre
        data = [{"index": i, "embedding": [float(i)] * 4} for i in range(len(body["input"]))]
        return httpx.Response(200, json={"data": list(reversed(data))})

    embedder = OpenAIEmbedder("k", "text-embedding-3-small", 4, httpx.MockTransport(handler))
    vectors = embedder.embed_documents([f"t{i}" for i in range(100)])
    assert len(calls) == 2 and len(calls[0]["input"]) == 96
    assert [v[0] for v in vectors] == [float(i) for i in range(96)] + [float(i) for i in range(4)]


def test_cohere_embedder_uses_input_types():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        body = json.loads(request.read())
        seen.append(body["input_type"])
        return httpx.Response(200, json={"embeddings": {"float": [[0.1] * 4] * len(body["texts"])}})

    embedder = CohereEmbedder("k", "embed-v4.0", 4, httpx.MockTransport(handler))
    embedder.embed_documents(["a", "b"])
    embedder.embed_query("q")
    assert seen == ["search_document", "search_query"]


def test_cohere_reranker_sorts_by_score():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {"index": 2, "relevance_score": 0.2},
                    {"index": 0, "relevance_score": 0.9},
                ]
            },
        )

    reranker = CohereReranker("k", transport=httpx.MockTransport(handler))
    assert reranker.rerank("q", ["a", "b", "c"], 2) == [(0, 0.9), (2, 0.2)]


def test_post_retries_on_rate_limit(monkeypatch):
    monkeypatch.setattr("src.rag.embeddings.time.sleep", lambda _s: None)
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) < 3:
            return httpx.Response(429)
        return httpx.Response(200, json={"embeddings": {"float": [[0.0] * 4]}})

    embedder = CohereEmbedder("k", "m", 4, httpx.MockTransport(handler))
    assert embedder.embed_query("x") == [0.0] * 4
    assert len(attempts) == 3


# ---------- recherche hybride sur PostgreSQL + pgvector ----------

pytestmark_pg = pytest.mark.skipif(
    not get_settings().database_url.startswith("postgresql"),
    reason="nécessite PostgreSQL + pgvector (DATABASE_URL)",
)


class HashEmbedder:
    """Embedding déterministe par sac de mots hachés : similaire si les mots se recoupent."""

    dim = get_settings().EMBEDDING_DIM

    def _vec(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dim] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


CORPUS = {
    ("3M_2018_10K.pdf", "3M", 2018): [
        (
            "Item 7 > Liquidity",
            "Purchases of property, plant and equipment were 1,577 million in 2018.",
            60,
        ),
        (
            "Item 1A > Risk Factors",
            "Tariffs and trade restrictions could affect our supply chain.",
            12,
        ),
    ],
    ("ADOBE_2022_10K.pdf", "ADOBE", 2022): [
        ("Item 7 > Liquidity", "Net cash provided by operating activities was 7,838 million.", 55),
        ("Item 1 > Business", "Adobe Creative Cloud subscriptions drive digital media revenue.", 4),
    ],
    ("3M_2019_10K.pdf", "3M", 2019): [
        (
            "Item 7 > Liquidity",
            "Purchases of property, plant and equipment were 1,750 million in 2019.",
            58,
        ),
    ],
}


@pytest.fixture(scope="module")
def corpus():
    if not get_settings().database_url.startswith("postgresql"):
        pytest.skip("nécessite PostgreSQL + pgvector")
    run_migrations()
    embedder = HashEmbedder()
    with session_scope() as db:
        db.query(Chunk).delete()
        db.query(Document).delete()
        for (filename, company, year), chunks in CORPUS.items():
            doc = Document(
                filename=filename,
                company=company,
                fiscal_year=year,
                doc_type="10-K",
                status="ready",
            )
            db.add(doc)
            db.flush()
            texts = [f"[{company} {year} 10-K — {sec}]\n{text}" for sec, text, _ in chunks]
            vectors = embedder.embed_documents(texts)
            add_chunks(
                db,
                doc.id,
                [
                    {
                        "ordinal": i,
                        "content": text,
                        "embedding_text": texts[i],
                        "section": sec,
                        "kind": "text",
                        "page_start": page,
                        "page_end": page,
                        "company": company,
                        "fiscal_year": year,
                        "doc_type": "10-K",
                        "embedding": vectors[i],
                    }
                    for i, (sec, text, page) in enumerate(chunks)
                ],
            )
    return embedder


def _search(corpus, text, **kw):
    return hybrid_search(text, corpus.embed_query(text), k=5, candidates=10, **kw)


@pytest.mark.skipif(
    not get_settings().database_url.startswith("postgresql"), reason="PostgreSQL requis"
)
class TestPostgres:
    def test_finds_exact_figure_and_returns_provenance(self, corpus):
        hits = _search(corpus, "purchases of property plant and equipment 3M 2018")
        top = hits[0]
        assert top.filename == "3M_2018_10K.pdf" and top.page_start == 60
        assert top.company == "3M" and top.fiscal_year == 2018 and top.doc_type == "10-K"
        assert top.fusion_score > 0

    def test_lexical_branch_finds_rare_term_missed_by_dense(self, corpus):
        hits = _search(corpus, "tariffs")
        assert hits and hits[0].section == "Item 1A > Risk Factors"

    def test_filters_restrict_results(self, corpus):
        hits = _search(
            corpus,
            "purchases of property plant and equipment",
            filters=Filters(company="3m", fiscal_year=2019),
        )
        assert hits and {h.fiscal_year for h in hits} == {2019}
        assert _search(corpus, "revenue", filters=Filters(company="UNKNOWN")) == []

    def test_search_documents_with_reranker_and_confidence(self, corpus):
        class Fixed:
            def rerank(self, query, texts, top_n):
                return [(0, 0.95)]

        result = search_documents(
            "net cash operating activities adobe", embedder=corpus, reranker=Fixed(), top_k=1
        )
        assert len(result.documents) == 1 and result.best_score == 0.95 and result.is_confident

        class Weak:
            def rerank(self, query, texts, top_n):
                return [(0, 0.01)]

        weak = search_documents("net cash", embedder=corpus, reranker=Weak(), top_k=1)
        assert weak.best_score == 0.01 and not weak.is_confident

    def test_without_reranker_signal_results_are_confident_if_any(self, corpus):
        result = search_documents("liquidity", embedder=corpus, reranker=NoReranker(), top_k=2)
        assert len(result.documents) == 2 and result.best_score is None and result.is_confident
        assert not SearchResult([], None).is_confident


def test_postgres_required_error_on_other_backends():
    if get_engine().dialect.name == "postgresql":
        pytest.skip("test spécifique à SQLite")
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        hybrid_search("x", [0.0] * get_settings().EMBEDDING_DIM)
