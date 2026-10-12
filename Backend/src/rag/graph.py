"""Graphe LangGraph du pipeline RAG (compilé à la demande)."""

from functools import lru_cache

from langgraph.graph import END, StateGraph

from src.rag.generation.generate import generate
from src.rag.grading.documents import grade_documents
from src.rag.grading.generation import grade_generation_v_documents_and_question
from src.rag.grading.quality import grade_answer_quality
from src.rag.retrieval.nodes import retrieve, web_search
from src.rag.routing import decide_to_generate, route_question
from src.rag.state import GraphState


def build_graph() -> StateGraph:
    workflow = StateGraph(GraphState)
    workflow.add_node("websearch", web_search)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("generate", generate)
    workflow.add_node("grade_answer_quality", grade_answer_quality)

    workflow.set_conditional_entry_point(
        route_question,
        {"websearch": "websearch", "vectorstore": "retrieve"},
    )
    workflow.add_edge("websearch", "generate")
    workflow.add_edge("retrieve", "grade_documents")
    workflow.add_conditional_edges(
        "grade_documents",
        decide_to_generate,
        {"websearch": "websearch", "generate": "generate"},
    )
    workflow.add_edge("generate", "grade_answer_quality")
    workflow.add_conditional_edges(
        "grade_answer_quality",
        grade_generation_v_documents_and_question,
        {"not supported": "generate", "useful": END, "not useful": "websearch", "max retries": END},
    )
    return workflow


@lru_cache
def get_graph():
    """Graphe compilé (singleton)."""
    return build_graph().compile()
