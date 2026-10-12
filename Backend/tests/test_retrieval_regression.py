"""L3.8 : garde-fou de retrieval en CI.

Mini-corpus synthétique ingéré par le vrai code (chunking, index pgvector + plein texte, RRF) avec
un embedding déterministe : si un changement dégrade la recherche (découpage, fusion, filtres),
le hit@3 / MRR tombe sous le seuil. Le jeu complet FinanceBench (avec LLM) est dans
.github/workflows/eval.yml.
"""

import pytest

from tests.api_stub import install

install()

from api.database import run_migrations, session_scope  # noqa: E402
from api.db_models import Chunk, Document  # noqa: E402
from config.settings import get_settings  # noqa: E402
from src.ingestion.chunking import Page, chunk_pages  # noqa: E402
from src.ingestion.metadata import parse_filename  # noqa: E402
from src.rag.rerankers import NoReranker  # noqa: E402
from src.rag.search import search_documents  # noqa: E402
from src.rag.store import Filters, add_chunks, list_companies  # noqa: E402
from tests.fakes import HashEmbedder  # noqa: E402

pytestmark = pytest.mark.skipif(
    not get_settings().database_url.startswith("postgresql"),
    reason="nécessite PostgreSQL + pgvector",
)

FILINGS = {
    "ALPHA_2021_10K.pdf": [
        "# Item 7. MD&A\n\n## Liquidity\n\nPurchases of property, plant and equipment were 1,577 million in fiscal 2021.",
        "## Results of Operations\n\n| Item | 2021 | 2020 |\n|---|---|---|\n| Net sales | 32,765 | 31,657 |\n| Operating income | 7,207 | 7,692 |",
        "# Item 1A. Risk Factors\n\nSupply chain disruptions and tariffs could reduce margins.",
    ],
    "ALPHA_2020_10K.pdf": [
        "# Item 7. MD&A\n\n## Liquidity\n\nPurchases of property, plant and equipment were 1,300 million in fiscal 2020.",
    ],
    "BETA_2021_10K.pdf": [
        "# Item 7. MD&A\n\n## Liquidity\n\nNet cash provided by operating activities was 7,838 million.",
        "# Item 1. Business\n\nBeta sells cloud software subscriptions to enterprise customers.",
    ],
    "GAMMA_2022_10Q.pdf": [
        "# Item 2. MD&A\n\nTotal debt outstanding was 4,500 million at the end of the quarter, mostly senior notes.",
    ],
}

# (question, fichier attendu, texte attendu dans le passage)
QUESTIONS = [
    ("Alpha 2021 purchases of property plant and equipment", "ALPHA_2021_10K.pdf", "1,577"),
    ("Alpha 2020 purchases of property plant and equipment", "ALPHA_2020_10K.pdf", "1,300"),
    ("What were Alpha's net sales and operating income in 2021?", "ALPHA_2021_10K.pdf", "32,765"),
    (
        "Which risks could reduce Alpha's margins? tariffs supply chain",
        "ALPHA_2021_10K.pdf",
        "tariffs",
    ),
    ("Beta net cash provided by operating activities", "BETA_2021_10K.pdf", "7,838"),
    ("What does Beta sell? cloud software subscriptions", "BETA_2021_10K.pdf", "subscriptions"),
    ("Gamma total debt senior notes quarter", "GAMMA_2022_10Q.pdf", "4,500"),
]


@pytest.fixture(scope="module")
def indexed():
    run_migrations()
    embedder = HashEmbedder()
    with session_scope() as db:
        db.query(Chunk).delete()
        db.query(Document).delete()
        for filename, pages in FILINGS.items():
            meta = parse_filename(filename)
            doc = Document(
                filename=filename,
                company=meta.company,
                fiscal_year=meta.fiscal_year,
                doc_type=meta.doc_type,
                status="ready",
            )
            db.add(doc)
            db.flush()
            chunks = chunk_pages([Page(i + 1, md) for i, md in enumerate(pages)])
            texts = [c.embedding_text(meta) for c in chunks]
            vectors = embedder.embed_documents(texts)
            add_chunks(
                db,
                doc.id,
                [
                    {
                        "ordinal": c.ordinal,
                        "content": c.content,
                        "embedding_text": t,
                        "section": c.section,
                        "kind": c.kind,
                        "page_start": c.page_start,
                        "page_end": c.page_end,
                        "company": meta.company,
                        "fiscal_year": meta.fiscal_year,
                        "doc_type": meta.doc_type,
                        "embedding": v,
                    }
                    for c, t, v in zip(chunks, texts, vectors, strict=True)
                ],
            )
    return embedder


def _rank_of_answer(embedder, question, filename, needle, filters=None):
    result = search_documents(question, filters, top_k=3, embedder=embedder, reranker=NoReranker())
    for rank, doc in enumerate(result.documents, start=1):
        if doc.filename == filename and needle.lower() in doc.content.lower():
            return rank
    return None


def test_hit_at_3_and_mrr_on_reference_questions(indexed):
    ranks = [_rank_of_answer(indexed, q, f, n) for q, f, n in QUESTIONS]
    hit_at_3 = sum(r is not None for r in ranks) / len(ranks)
    mrr = sum(1 / r for r in ranks if r) / len(ranks)
    assert hit_at_3 >= 0.85, f"hit@3={hit_at_3:.2f} ranks={ranks}"
    assert mrr >= 0.7, f"MRR={mrr:.2f} ranks={ranks}"


def test_table_is_retrievable_as_a_whole(indexed):
    result = search_documents(
        "net sales operating income 2021", top_k=3, embedder=indexed, reranker=NoReranker()
    )
    tables = [d for d in result.documents if d.kind == "table"]
    assert tables and "| Net sales | 32,765 | 31,657 |" in tables[0].content


def test_metadata_filters_pick_the_right_year(indexed):
    question = "purchases of property plant and equipment"
    result = search_documents(
        question,
        Filters(company="ALPHA", fiscal_year=2020),
        top_k=3,
        embedder=indexed,
        reranker=NoReranker(),
    )
    assert result.documents and {d.fiscal_year for d in result.documents} == {2020}


def test_known_companies_feed_the_question_analysis(indexed):
    assert list_companies() == ["ALPHA", "BETA", "GAMMA"]
