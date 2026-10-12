from typing import Optional

from langchain_core.messages import HumanMessage

from src.core.exceptions import (
    InvalidResponseException,  # ✅ utilisé pour les erreurs de génération (streaming et non-streaming)
)
from src.core.retry_policy import retry_with_backoff_advanced
from src.rag.runtime import get_runtime


def Rewrite_query(query: str, history: Optional[str] = None) -> str:
    """Rewrite the query to be more specific, using optional conversation history."""
    try:
        print("---Rewrite the query---")
        if not query or not query.strip():
            return query

        rewritting_prompt_formatted = (
            get_runtime().prompt["Rewritting_prompt"].format(query=query, history=history or "")
        )

        def _call_llm():
            # Utiliser le gestionnaire de clés avec fallback automatique
            return get_runtime().groq_key_manager.invoke_with_fallback(
                [HumanMessage(content=rewritting_prompt_formatted)], json_mode=False
            )

        generation = retry_with_backoff_advanced(
            _call_llm, circuit_breaker=get_runtime().llm_circuit_breaker
        )

        if hasattr(generation, "content"):
            return generation.content
        elif isinstance(generation, str):
            return generation
        else:
            raise InvalidResponseException(
                "Format de réponse invalide lors de la réécriture de la requête",
                {"query": query, "response_type": type(generation).__name__},
            )
    except Exception as e:
        # En cas d'erreur, retourner la query originale
        print(f"⚠️ Erreur lors de la réécriture: {str(e)}. Utilisation de la requête originale.")
        return query
