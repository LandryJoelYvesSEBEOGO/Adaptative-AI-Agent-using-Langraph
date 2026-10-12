"""Composants partagés du moteur RAG, construits à la demande (aucun effet de bord à l'import).

Le premier appel à `get_runtime()` charge la configuration, initialise la rotation des
clés Groq, les circuit breakers, le gestionnaire de fallback et les prompts.
"""

from dataclasses import dataclass
from functools import cached_property, lru_cache
from typing import Any

from config.Config import Config


@dataclass
class Runtime:
    groq_key_manager: Any
    llm_circuit_breaker: Any
    web_search_circuit_breaker: Any
    retrieval_circuit_breaker: Any
    fallback_manager: Any
    prompt: dict

    @cached_property
    def web_search_tool(self):
        """Client Tavily, créé à la première recherche web (clé requise à ce moment seulement)."""
        from langchain_community.tools.tavily_search.tool import TavilySearchResults

        return TavilySearchResults(k=3, tavily_api_key=Config.TAVILY_API_KEY)


@lru_cache
def get_runtime() -> Runtime:
    from src.core.fallback import get_fallback_manager
    from src.core.groq_key_manager import get_groq_key_manager
    from src.core.retry_policy import get_circuit_breaker
    from src.rag.Prompts import get_prompts

    Config.export_runtime_env()
    breakers_on = getattr(Config, "CIRCUIT_BREAKER_ENABLED", True)
    return Runtime(
        groq_key_manager=get_groq_key_manager(),
        llm_circuit_breaker=get_circuit_breaker("llm") if breakers_on else None,
        web_search_circuit_breaker=get_circuit_breaker("web_search") if breakers_on else None,
        retrieval_circuit_breaker=get_circuit_breaker("retrieval") if breakers_on else None,
        fallback_manager=(
            get_fallback_manager() if getattr(Config, "FALLBACK_MODELS_ENABLED", True) else None
        ),
        prompt=get_prompts(),
    )
