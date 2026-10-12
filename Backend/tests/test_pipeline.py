"""L3.4 / L3.5 / L3.6 : pipeline simplifié, streaming réel, sorties structurées."""

import asyncio
import time

import pytest
from pydantic import ValidationError

from src.rag.answer_prompt import build_citations, cited_numbers
from src.rag.pipeline import NO_SOURCE_MESSAGE, run_rag, stream_rag
from src.rag.query_analysis import detect_company, detect_doc_type, detect_year, heuristic_filters
from src.rag.schemas import QueryAnalysis, SourceDocument
from src.rag.search import SearchResult
from src.rag.store import Filters
from tests.fakes import SlowStreamingLLM, make_deps, retrieved

# ---------- analyse de la question (heuristiques, sans LLM) ----------


def test_company_year_and_type_detection():
    companies = ["3M", "ADOBE", "AMERICANEXPRESS", "Best Buy"]
    assert detect_company("What was 3M's capex in FY2018?", companies) == "3M"
    assert (
        detect_company("Total revenue of American Express in 2022", companies) == "AMERICANEXPRESS"
    )
    assert detect_company("How is the weather?", companies) is None
    assert detect_year("capex in fiscal 2018") == 2018
    assert detect_year("FY19 revenue") == 2019
    assert detect_year("compare 2018 and 2019") is None  # ambigu : pas de filtre
    assert detect_doc_type("Q3 10-Q liabilities") == "10-Q"
    assert detect_doc_type("annual report highlights") == "10-K"
    f = heuristic_filters("Adobe 10-K 2022 operating cash flow", companies)
    assert (f.company, f.fiscal_year, f.doc_type) == ("ADOBE", 2022, "10-K")


def test_structured_output_schema_is_validated():
    ok = QueryAnalysis(standalone_question="q", doc_type="10-K", fiscal_year=2020)
    assert ok.company is None
    with pytest.raises(ValidationError):
        QueryAnalysis(standalone_question="q", doc_type="10-Z")  # type: ignore[arg-type]


def test_citations_only_for_cited_sources():
    docs = [
        SourceDocument(number=1, source="a.pdf", content="aaa", page=3, company="3M"),
        SourceDocument(number=2, source="b.pdf", content="bbb"),
        SourceDocument(number=3, source="https://x.io", content="ccc", is_web=True),
    ]
    assert cited_numbers("Fact [1]. Other [3, 2]. Ghost [9].") == [1, 2, 3, 9]
    cites = build_citations("Fact [1] and [3].", docs)
    assert [c["id"] for c in cites] == [1, 3]
    assert cites[0]["source"] == "a.pdf" and cites[0]["metadata"]["page"] == 3
    assert cites[1]["metadata"]["is_web"] is True
    assert [c["id"] for c in build_citations("No marker.", docs)] == [1, 2, 3]  # repli


# ---------- pipeline ----------


async def test_nominal_path_uses_one_llm_call_and_cites_sources():
    llm = SlowStreamingLLM(calls=[], delay=0)
    out = await run_rag("What was 3M's FY2018 capex?", deps=make_deps(llm))
    assert len(llm.calls) == 1 and out.llm_calls == 1
    assert out.answer.strip() == "Capex was 1577 million [1]."
    assert [c["id"] for c in out.citations] == [1]
    assert (
        out.citations[0]["source"] == "3M_2018_10K.pdf"
        and out.citations[0]["metadata"]["page"] == 60
    )
    assert out.num_documents == 2 and not out.used_web
    assert {"analyze", "retrieval", "generation", "end_to_end"} <= set(out.latencies)


async def test_tokens_are_streamed_before_generation_completes():
    llm = SlowStreamingLLM(calls=[], delay=0.2)
    started = time.perf_counter()
    arrivals, tokens = [], []
    async for event in stream_rag("3M capex?", deps=make_deps(llm)):
        if event["type"] == "token":
            arrivals.append(time.perf_counter() - started)
            tokens.append(event["text"])
        else:
            total = time.perf_counter() - started
    assert len(tokens) >= 4
    assert arrivals[0] < total - 0.5, "le premier token doit arriver bien avant la fin"
    assert all(b > a for a, b in zip(arrivals, arrivals[1:], strict=False)), "flux incrémental"
    assert "".join(tokens).strip() == llm.reply


async def test_single_execution_path_streaming_equals_non_streaming():
    deps = make_deps(SlowStreamingLLM(calls=[], delay=0))
    streamed = "".join(
        [e["text"] async for e in stream_rag("3M capex?", deps=deps) if e["type"] == "token"]
    )
    assert streamed.strip() == (await run_rag("3M capex?", deps=deps)).answer.strip()


async def test_history_triggers_one_structured_analysis_call():
    seen_analysis = []

    async def analyzer(question, history):
        seen_analysis.append((question, history))
        return QueryAnalysis(standalone_question="What was Adobe's FY2022 operating cash flow?")

    searches = []
    llm = SlowStreamingLLM(calls=[], delay=0)
    out = await run_rag(
        "and its cash flow?",
        history="User: Tell me about Adobe in 2022",
        deps=make_deps(llm, analyzer=analyzer, seen=searches),
    )
    assert seen_analysis == [("and its cash flow?", "User: Tell me about Adobe in 2022")]
    assert out.llm_calls == 2  # analyse + génération : ≤ 3 appels LLM
    query, filters = searches[0]
    assert query == "What was Adobe's FY2022 operating cash flow?"
    assert (filters.company, filters.fiscal_year) == ("ADOBE", 2022)


async def test_no_history_means_no_analysis_call():
    async def boom(question, history):
        raise AssertionError("l'analyse LLM ne doit pas être appelée sans historique")

    out = await run_rag(
        "3M capex 2018?", deps=make_deps(SlowStreamingLLM(calls=[], delay=0), analyzer=boom)
    )
    assert out.llm_calls == 1


async def test_web_search_only_when_scores_are_low():
    web_calls = []

    async def web(query):
        web_calls.append(query)
        return [
            SourceDocument(
                number=0, source="https://news.example/3m", content="3M news", is_web=True
            )
        ]

    confident = await run_rag(
        "3M capex?", deps=make_deps(SlowStreamingLLM(calls=[], delay=0), web=web)
    )
    assert web_calls == [] and not confident.used_web

    low = await run_rag(
        "3M capex?", deps=make_deps(SlowStreamingLLM(calls=[], delay=0), confident=False, web=web)
    )
    assert web_calls == ["3M capex?"] and low.used_web
    assert low.num_documents == 3  # 2 documents + 1 résultat web, numérotés à la suite


async def test_web_failure_does_not_break_the_answer():
    async def broken(query):
        raise RuntimeError("tavily down")

    out = await run_rag(
        "3M capex?",
        deps=make_deps(SlowStreamingLLM(calls=[], delay=0), confident=False, web=broken),
    )
    assert out.answer and not out.used_web


async def test_no_source_means_no_llm_call():
    llm = SlowStreamingLLM(calls=[], delay=0)
    out = await run_rag("unknown?", deps=make_deps(llm, docs=[]))
    assert out.answer == NO_SOURCE_MESSAGE and llm.calls == [] and out.llm_calls == 0
    assert out.citations == []


async def test_filters_are_relaxed_when_they_match_nothing():
    calls = []

    def search(query, filters):
        calls.append(filters)
        return SearchResult([] if filters else [retrieved(1)], 0.8)

    deps = make_deps(SlowStreamingLLM(calls=[], delay=0))
    deps.search = search
    out = await run_rag("3M capex 2018", deps=deps)
    assert isinstance(calls[0], Filters) and calls[1] is None
    assert out.num_documents == 1


async def test_cancel_event_stops_generation_and_closes_the_provider_stream():
    llm = SlowStreamingLLM(
        calls=[],
        delay=0.1,
        reply="w1 w2 w3 w4 w5 w6 w7 w8 w9 w10",
        stats={"emitted": 0, "cancelled": False},
    )
    cancel = asyncio.Event()
    tokens = []
    async for event in stream_rag("3M capex?", deps=make_deps(llm), cancel_event=cancel):
        if event["type"] == "token":
            tokens.append(event["text"])
            if len(tokens) == 3:
                cancel.set()  # Stop
        else:
            output = event["output"]
    assert llm.stats["cancelled"], "le flux du fournisseur doit être fermé"
    assert llm.stats["emitted"] < 10 and len(output.answer.split()) < 10
