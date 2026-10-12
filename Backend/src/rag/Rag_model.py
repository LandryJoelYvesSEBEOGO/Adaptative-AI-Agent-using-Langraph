"""Façade de compatibilité : le moteur RAG est réparti dans les modules de `src/rag/`.

    state.py         GraphState
    runtime.py       composants partagés (clés Groq, circuit breakers, prompts, Tavily)
    llm_utils.py     retry et fallback LLM
    generation/      formatage, réécriture de requête, génération (normale et streaming)
    retrieval/       retriever, reranker, nœuds `retrieve` et `web_search`
    grading/         grading des documents, des hallucinations, qualité de la réponse
    routing.py       routage de la question
    graph.py         graphe LangGraph (compilé à la demande)
    answer.py        points d'entrée `get_final_response` / `get_final_response_stream`

L'import de ce module n'initialise ni LLM, ni Tavily, ni le graphe.
"""

from src.rag.answer import get_final_response, get_final_response_stream
from src.rag.generation.formatting import (
    extract_sources_from_documents,
    format_citations,
    format_docs,
)
from src.rag.generation.generate import generate, generate_stream
from src.rag.generation.rewrite import Rewrite_query
from src.rag.grading.documents import grade_documents
from src.rag.grading.generation import grade_generation_v_documents_and_question
from src.rag.grading.quality import grade_answer_quality
from src.rag.graph import get_graph
from src.rag.llm_utils import get_llm_json_with_fallback, get_llm_with_fallback, retry_with_backoff
from src.rag.retrieval.nodes import retrieve, web_search
from src.rag.retrieval.reranker import get_reranker_instance, rerank_documents
from src.rag.retrieval.retriever import get_retriever_instance
from src.rag.routing import decide_to_generate, route_question
from src.rag.state import GraphState

__all__ = [
    "GraphState",
    "Rewrite_query",
    "decide_to_generate",
    "extract_sources_from_documents",
    "format_citations",
    "format_docs",
    "generate",
    "generate_stream",
    "get_final_response",
    "get_final_response_stream",
    "get_graph",
    "get_llm_json_with_fallback",
    "get_llm_with_fallback",
    "get_reranker_instance",
    "get_retriever_instance",
    "grade_answer_quality",
    "grade_documents",
    "grade_generation_v_documents_and_question",
    "rerank_documents",
    "retrieve",
    "retry_with_backoff",
    "route_question",
    "web_search",
]


def __getattr__(name: str):
    # `graph` reste accessible (compatibilité) mais n'est compilé qu'au premier accès.
    if name == "graph":
        return get_graph()
    raise AttributeError(name)
