import time
from typing import Callable

from config.Config import Config
from src.core.exceptions import (
    LLMQuotaException,
    LLMTimeoutException,
    MaxRetriesException,  # ✅ utilisé pour les erreurs de génération (streaming et non-streaming)
)
from src.core.retry_policy import retry_with_backoff_advanced
from src.rag.runtime import get_runtime


# Fonction helper pour retry avec backoff (conservée pour compatibilité)
def retry_with_backoff(func: Callable, max_retries: int = None, initial_delay: int = None) -> any:
    """Retry une fonction avec backoff exponentiel (wrapper pour compatibilité)."""
    # Utiliser la version avancée si activée
    if getattr(Config, "CIRCUIT_BREAKER_ENABLED", True) or getattr(
        Config, "RETRY_JITTER_ENABLED", True
    ):
        # Déterminer quel circuit breaker utiliser selon le contexte
        circuit_breaker = None  # Peut être défini selon le contexte

        return retry_with_backoff_advanced(
            func,
            max_retries=max_retries,
            initial_delay=initial_delay,
            circuit_breaker=circuit_breaker,
        )
    else:
        # Ancienne implémentation simple
        if max_retries is None:
            max_retries = getattr(Config, "MAX_RETRIES", 3)
        if initial_delay is None:
            initial_delay = getattr(Config, "RETRY_INITIAL_DELAY", 1)

        backoff_factor = getattr(Config, "RETRY_BACKOFF_FACTOR", 2)

        for attempt in range(max_retries):
            try:
                return func()
            except (LLMTimeoutException, LLMQuotaException, Exception):
                if attempt == max_retries - 1:
                    raise
                delay = initial_delay * (backoff_factor**attempt)
                print(f"⚠️ Tentative {attempt + 1}/{max_retries} échouée. Retry dans {delay}s...")
                time.sleep(delay)
        raise MaxRetriesException(f"Échec après {max_retries} tentatives")


def get_llm_with_fallback():
    """
    Récupère le LLM actuel, avec fallback automatique si activé.
    Utilise le gestionnaire de clés API pour la rotation automatique.
    """
    if get_runtime().fallback_manager and getattr(Config, "FALLBACK_MODELS_ENABLED", True):
        llm = get_runtime().fallback_manager.get_current_llm()
        if llm:
            return llm

    # Utiliser le gestionnaire de clés API (rotation automatique en cas de rate limit)
    return get_runtime().groq_key_manager.get_current_llm(json_mode=False)


def get_llm_json_with_fallback():
    """
    Récupère le LLM en mode JSON avec fallback automatique.
    Utilise le gestionnaire de clés API pour la rotation automatique.
    """
    if get_runtime().fallback_manager and getattr(Config, "FALLBACK_MODELS_ENABLED", True):
        current_llm = get_runtime().fallback_manager.get_current_llm()
        if current_llm:
            # Utiliser le gestionnaire de clés pour créer le LLM JSON
            return get_runtime().groq_key_manager.get_current_llm(json_mode=True)

    # Utiliser le gestionnaire de clés API (rotation automatique en cas de rate limit)
    return get_runtime().groq_key_manager.get_current_llm(json_mode=True)
