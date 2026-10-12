"""Traçage des exécutions (LangSmith via variables d'environnement, Langfuse via callback)."""

import logging
from typing import Any

from config.settings import get_settings

logger = logging.getLogger(__name__)


def tracing_callbacks() -> list[Any]:
    """Callbacks LangChain à joindre à une exécution : Langfuse si les clés sont configurées.

    LangSmith n'en a pas besoin : `Settings.export_runtime_env()` active son traçage global
    (LANGCHAIN_TRACING_V2 + LANGSMITH_API_KEY). Si le paquet `langfuse` est absent alors que ses
    clés sont renseignées, l'exécution continue sans trace (avertissement journalisé)."""
    settings = get_settings()
    if not (settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY):
        return []
    try:
        from langfuse.langchain import CallbackHandler  # type: ignore[import-not-found]
    except ImportError:
        logger.warning(
            "Langfuse configuré mais le paquet est absent (uv sync --extra observability)"
        )
        return []
    return [CallbackHandler()]
