import json
from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage

from src.core.retry_policy import retry_with_backoff_advanced
from src.rag.state import GraphState
from src.rag.runtime import get_runtime


# Edge functions
def route_question(state: GraphState) -> str:
    """Route the question to either web search or RAG based on LLM decision."""
    try:
        print("---ROUTE QUESTION---")

        def _route():
            # Utiliser le gestionnaire de clés avec fallback automatique (mode JSON)
            return get_runtime().groq_key_manager.invoke_with_fallback(
                [SystemMessage(content=get_runtime().prompt["router_instructions"])]
                + [HumanMessage(content=state["question"])],
                json_mode=True,
            )

        route_result = retry_with_backoff_advanced(
            _route, circuit_breaker=get_runtime().llm_circuit_breaker
        )

        try:
            route_data = json.loads(route_result.content)
            source = route_data.get("datasource", "vectorstore")
        except json.JSONDecodeError:
            print("⚠️ Erreur parsing JSON routing. Défaut: vectorstore")
            source = "vectorstore"

        return "websearch" if source == "websearch" else "vectorstore"
    except Exception as e:
        print(f"⚠️ Erreur lors du routing: {str(e)}. Défaut: vectorstore")
        return "vectorstore"  # Fallback sur vectorstore


def decide_to_generate(state: GraphState) -> str:
    """Decide whether to generate an answer or add web search."""
    print("---ASSESS GRADED DOCUMENTS---")
    if state.get("web_search") == "Yes":
        print("---DECISION: INCLUDE WEB SEARCH---")
        return "websearch"
    else:
        print("---DECISION: GENERATE---")
        return "generate"
