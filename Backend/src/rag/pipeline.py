"""Pipeline RAG : un seul graphe LangGraph, utilisé par les modes normal et streaming.

    analyze -> retrieve -> [web_search si recherche documentaire peu fiable] -> generate

Appels LLM dans le cas nominal : 1 (génération) ; 2 si la question dépend de l'historique
(question autonome). Aucun grading LLM par document : le reranker fait ce travail.
"""

import asyncio
import time
from collections.abc import AsyncGenerator, AsyncIterator, Callable
from contextlib import aclosing
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Required, TypedDict, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from pydantic import SecretStr

from src.rag.answer_prompt import SYSTEM_PROMPT, build_citations, build_user_prompt
from src.rag.query_analysis import Analyzer, heuristic_filters
from src.rag.schemas import QueryAnalysis, SourceDocument
from src.rag.search import SearchResult
from src.rag.store import Filters, Retrieved
from src.rag.websearch import WebSearch

NO_SOURCE_MESSAGE = (
    "No relevant source was found in the indexed documents. / "
    "Aucune source pertinente n'a été trouvée dans les documents indexés."
)


@dataclass
class Dependencies:
    """Composants externes du pipeline, injectables (tests) ou construits par `get_dependencies`."""

    llm: BaseChatModel
    analyze: Analyzer
    search: Callable[[str, Filters | None], SearchResult]
    list_companies: Callable[[], list[str]]
    web_search: WebSearch | None = None
    compiled: Any = field(default=None, repr=False)  # graphe compilé (cache)


class RAGState(TypedDict, total=False):
    question: Required[str]
    history: str
    standalone: str
    filters: Filters | None
    documents: list[SourceDocument]
    confident: bool
    best_score: float | None
    answer: str
    llm_calls: int
    used_web: bool
    latencies: dict[str, float]


def _to_source(number: int, doc: Retrieved) -> SourceDocument:
    return SourceDocument(
        number=number,
        source=doc.filename,
        content=doc.content,
        page=doc.page_start,
        section=doc.section,
        company=doc.company,
        fiscal_year=doc.fiscal_year,
        doc_type=doc.doc_type,
        document_id=doc.document_id,
        kind=doc.kind,
    )


def _timed(state: RAGState, name: str, started: float) -> dict[str, float]:
    return {**state.get("latencies", {}), name: time.perf_counter() - started}


def build_graph(deps: Dependencies):
    async def analyze(state: RAGState) -> dict[str, Any]:
        started = time.perf_counter()
        question, history = state["question"], state.get("history", "")
        llm_calls = state.get("llm_calls", 0)
        hints = QueryAnalysis(standalone_question=question)
        if history.strip():
            hints = await deps.analyze(question, history)
            llm_calls += 1
        standalone = hints.standalone_question or question
        companies = await asyncio.to_thread(deps.list_companies)
        filters = heuristic_filters(standalone, companies)
        # Les indications du LLM ne comblent que ce que les sociétés connues n'ont pas permis de voir.
        filters.company = filters.company or _known(hints.company, companies)
        filters.fiscal_year = filters.fiscal_year or hints.fiscal_year
        filters.doc_type = filters.doc_type or hints.doc_type
        return {
            "standalone": standalone,
            "filters": None if filters.is_empty() else filters,
            "llm_calls": llm_calls,
            "latencies": _timed(state, "analyze", started),
        }

    async def retrieve(state: RAGState) -> dict[str, Any]:
        started = time.perf_counter()
        query, filters = state.get("standalone") or state["question"], state.get("filters")
        result = await asyncio.to_thread(deps.search, query, filters)
        if not result.documents and filters is not None:
            result = await asyncio.to_thread(deps.search, query, None)  # filtres trop stricts
        documents = [_to_source(i, d) for i, d in enumerate(result.documents, start=1)]
        return {
            "documents": documents,
            "confident": result.is_confident,
            "best_score": result.best_score,
            "latencies": _timed(state, "retrieval", started),
        }

    async def web_search(state: RAGState) -> dict[str, Any]:
        started = time.perf_counter()
        assert deps.web_search is not None
        try:
            found = await deps.web_search(state.get("standalone") or state["question"])
        except Exception:  # la recherche web est un secours : son échec ne bloque pas la réponse
            found = []
        documents = list(state.get("documents", []))
        for item in found:
            documents.append(item.model_copy(update={"number": len(documents) + 1}))
        return {
            "documents": documents,
            "used_web": bool(found),
            "latencies": _timed(state, "web_search", started),
        }

    async def generate(state: RAGState, config: RunnableConfig) -> dict[str, Any]:
        started = time.perf_counter()
        documents = state.get("documents", [])
        if not documents:
            return {"answer": NO_SOURCE_MESSAGE, "latencies": _timed(state, "generation", started)}
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=build_user_prompt(state.get("standalone") or state["question"], documents)
            ),
        ]
        cancel = (config.get("configurable") or {}).get("cancel_event")
        parts: list[str] = []
        # `aclosing` ferme le flux du fournisseur dès qu'on s'arrête (Stop) : la génération cesse
        # côté API au lieu d'aller jusqu'au bout.
        stream = cast("AsyncGenerator[Any, None]", deps.llm.astream(messages, config=config))
        async with aclosing(stream):
            async for chunk in stream:
                parts.append(chunk.content if isinstance(chunk.content, str) else "")
                if cancel is not None and cancel.is_set():
                    break
        return {
            "answer": "".join(parts),
            "llm_calls": state.get("llm_calls", 0) + 1,
            "latencies": _timed(state, "generation", started),
        }

    def after_retrieve(state: RAGState) -> str:
        if not state.get("confident", True) and deps.web_search is not None:
            return "web_search"
        return "generate"

    graph = StateGraph(RAGState)
    graph.add_node("analyze", analyze)
    graph.add_node("retrieve", retrieve)
    graph.add_node("web_search", web_search)
    graph.add_node("generate", generate)
    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", "retrieve")
    graph.add_conditional_edges(
        "retrieve", after_retrieve, {"web_search": "web_search", "generate": "generate"}
    )
    graph.add_edge("web_search", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


def _known(candidate: str | None, companies: list[str]) -> str | None:
    """N'accepte une société suggérée par le LLM que si elle est réellement indexée."""
    if not candidate:
        return None
    lowered = {c.lower(): c for c in companies}
    return lowered.get(candidate.lower())


@lru_cache
def get_dependencies() -> Dependencies:
    """Composants de production (construits à la première requête)."""
    from langchain_groq import ChatGroq

    from config.settings import get_settings
    from src.rag.query_analysis import llm_analyzer
    from src.rag.search import search_documents
    from src.rag.store import list_companies
    from src.rag.websearch import tavily_search

    settings = get_settings()
    if not settings.GROQ_API_KEYS:
        raise RuntimeError("GROQ_API_KEY est requis pour générer des réponses")
    llm = ChatGroq(
        model=settings.GROQ_model,
        temperature=0,
        api_key=SecretStr(settings.GROQ_API_KEYS[0]),
        timeout=settings.LLM_TIMEOUT * 2,
        max_retries=settings.MAX_RETRIES,
    )
    return Dependencies(
        llm=llm,
        analyze=llm_analyzer(llm),
        search=lambda query, filters: search_documents(query, filters),
        list_companies=list_companies,
        web_search=tavily_search(),
    )


@dataclass
class RagOutput:
    answer: str
    citations: list[dict]
    latencies: dict[str, float]
    llm_calls: int
    num_documents: int
    used_web: bool
    best_score: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)


async def stream_rag(
    question: str,
    history: str = "",
    deps: Dependencies | None = None,
    cancel_event: asyncio.Event | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Exécute le pipeline et émet des événements :

    {"type": "token", "text": …} pour chaque fragment de la réponse, puis
    {"type": "done", "output": RagOutput}.

    `cancel_event` (optionnel) : une fois positionné, la génération s'arrête au prochain
    fragment et le flux ferme la connexion au fournisseur LLM.
    """
    graph = _graph_for(deps or get_dependencies())
    started = time.perf_counter()
    final: dict[str, Any] = {}
    streamed = False
    async for mode, data in graph.astream(
        {"question": question, "history": history, "llm_calls": 0, "latencies": {}},
        config={"configurable": {"cancel_event": cancel_event}},
        stream_mode=["messages", "values"],
    ):
        if mode == "messages":
            chunk, metadata = data
            text = chunk.content
            if metadata.get("langgraph_node") == "generate" and isinstance(text, str) and text:
                streamed = True
                yield {"type": "token", "text": text}
        else:
            final = data

    answer = final.get("answer", "")
    if answer and not streamed:  # réponse sans appel LLM (aucune source) ou modèle non streamé
        yield {"type": "token", "text": answer}
    documents = final.get("documents", [])
    latencies = {**final.get("latencies", {}), "end_to_end": time.perf_counter() - started}
    yield {
        "type": "done",
        "output": RagOutput(
            answer=answer,
            citations=build_citations(answer, documents) if documents else [],
            latencies=latencies,
            llm_calls=final.get("llm_calls", 0),
            num_documents=len(documents),
            used_web=final.get("used_web", False),
            best_score=final.get("best_score"),
        ),
    }


async def run_rag(question: str, history: str = "", deps: Dependencies | None = None) -> RagOutput:
    """Mode non streamé : même graphe, on attend l'événement final."""
    output: RagOutput | None = None
    async for event in stream_rag(question, history, deps):
        if event["type"] == "done":
            output = event["output"]
    assert output is not None
    return output


def _graph_for(deps: Dependencies):
    if deps.compiled is None:
        deps.compiled = build_graph(deps)
    return deps.compiled


__all__ = ["Dependencies", "RagOutput", "build_graph", "run_rag", "stream_rag"]
