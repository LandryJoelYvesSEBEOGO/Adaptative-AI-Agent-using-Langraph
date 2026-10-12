import time
from typing import Dict

from langchain_core.messages import HumanMessage

from src.rag.state import GraphState
from config.Config import Config
from src.core.exceptions import (
    GenerationException,  # ✅ utilisé pour les erreurs de génération (streaming et non-streaming)
    InvalidResponseException,
    LLMQuotaException,
    MaxRetriesException,
)
from src.core.logger import get_logger
from src.core.retry_policy import retry_with_backoff_advanced
from src.rag.generation.formatting import (
    extract_sources_from_documents,
    format_citations,
    format_docs,
)
from src.rag.Prompts import get_prompts
from src.rag.runtime import get_runtime


def generate(state: GraphState) -> GraphState:
    """Generate an answer using RAG on the retrieved documents."""
    start_time = time.time()
    conversation_id = state.get("conversation_id", "unknown")
    latencies = state.get("latencies", {})

    try:
        get_logger().info(
            "Generation started",
            extra={"component": "generation", "conversation_id": conversation_id},
        )
        print("---GENERATE---")

        if not state.get("documents"):
            raise GenerationException("Aucun document disponible pour la génération")

        # Vérifier si les citations sont activées
        citations_enabled = getattr(Config, "CITATIONS_ENABLED", True)

        # Formater les documents (avec ou sans numéros de citation)
        docs_txt = format_docs(state["documents"], with_citations=citations_enabled)
        prompt = get_prompts(question=state["question"])  # Passer la question

        rag_prompt_formatted = prompt["rag_prompt"].format(
            context=docs_txt, question=state["question"]
        )

        def _generate():
            # Utiliser le gestionnaire de clés avec fallback automatique
            return get_runtime().groq_key_manager.invoke_with_fallback(
                [HumanMessage(content=rag_prompt_formatted)], json_mode=False
            )

        try:
            generation = retry_with_backoff_advanced(
                _generate, circuit_breaker=get_runtime().llm_circuit_breaker
            )
        except MaxRetriesException:
            # Essayer avec le modèle de fallback suivant
            if get_runtime().fallback_manager and get_runtime().fallback_manager.try_next_model():
                print(
                    f"[FALLBACK] Tentative avec modèle: {get_runtime().fallback_manager.get_current_model_name()}"
                )
                try:
                    generation = retry_with_backoff_advanced(
                        _generate, circuit_breaker=get_runtime().llm_circuit_breaker
                    )
                except Exception:
                    # Réinitialiser au modèle principal
                    get_runtime().fallback_manager.reset()
                    raise
            else:
                if get_runtime().fallback_manager:
                    get_runtime().fallback_manager.reset()
                raise

        if not generation:
            raise InvalidResponseException("Réponse vide du LLM")

        # Extraire le contenu de la réponse
        generation_content = (
            generation.content if hasattr(generation, "content") else str(generation)
        )

        # Traiter les citations si activées
        if citations_enabled:
            sources = extract_sources_from_documents(state["documents"])
            generation_content, references = format_citations(generation_content, sources)

            # Ajouter les références à la réponse si elles existent
            if references:
                generation_content = generation_content + references

        elapsed_time = time.time() - start_time
        latencies["generation"] = elapsed_time

        get_logger().info(
            "Generation completed",
            extra={
                "component": "generation",
                "conversation_id": conversation_id,
                "data": {"latency": elapsed_time, "citations_enabled": citations_enabled},
            },
        )

        return {
            "generation": generation_content,
            "loop_step": state.get("loop_step", 0) + 1,
            "latencies": latencies,
        }
    except LLMQuotaException as e:
        elapsed_time = time.time() - start_time
        latencies["generation"] = elapsed_time
        raise LLMQuotaException(
            "Quota API dépassé. Veuillez réessayer plus tard.",
            {"loop_step": state.get("loop_step", 0)},
        ) from e
    except Exception as e:
        elapsed_time = time.time() - start_time
        latencies["generation"] = elapsed_time
        error_msg = f"Erreur lors de la génération: {str(e)}"
        print(f"❌ {error_msg}")
        get_logger().error(
            "Generation failed",
            extra={"component": "generation", "conversation_id": conversation_id},
            exc_info=True,
        )
        # Lever une exception métier claire, déjà importée en haut du fichier
        raise GenerationException(error_msg) from e


def generate_stream(state: GraphState, stream_callback=None):
    """
    Génère une réponse avec streaming token par token.

    Args:
        state: État du graph
        stream_callback: Fonction callback appelée pour chaque chunk (chunk: str) -> None

    Returns:
        Dict avec la génération complète
    """
    start_time = time.time()
    conversation_id = state.get("conversation_id", "unknown")
    latencies = state.get("latencies", {})

    try:
        get_logger().info(
            "Generation with streaming started",
            extra={"component": "generation", "conversation_id": conversation_id},
        )
        print("---GENERATE (STREAMING)---")

        if not state.get("documents"):
            raise GenerationException("Aucun document disponible pour la génération")

        # Vérifier si les citations sont activées
        citations_enabled = getattr(Config, "CITATIONS_ENABLED", True)

        # Formater les documents
        docs_txt = format_docs(state["documents"], with_citations=citations_enabled)

        # Obtenir les prompts avec la question pour few-shot et role detection
        prompt = get_prompts(question=state["question"])

        rag_prompt_formatted = prompt["rag_prompt"].format(
            context=docs_txt, question=state["question"]
        )

        # Accumulateur pour la réponse complète
        full_response = ""

        # Streamer la réponse avec fallback automatique sur les clés
        try:
            stream = get_runtime().groq_key_manager.stream_with_fallback(
                [HumanMessage(content=rag_prompt_formatted)], json_mode=False
            )

            for chunk in stream:
                if hasattr(chunk, "content") and chunk.content:
                    chunk_text = chunk.content
                    full_response += chunk_text

                    # Appeler le callback si fourni
                    if stream_callback:
                        stream_callback(chunk_text)

            # Traiter les citations si activées
            if citations_enabled:
                sources = extract_sources_from_documents(state["documents"])
                full_response, references = format_citations(full_response, sources)

                # Streamer les références aussi
                if references:
                    if stream_callback:
                        stream_callback(references)
                    full_response = full_response + references

        except Exception as stream_error:
            # Fallback sur génération non-streaming en cas d'erreur
            print(f"⚠️ Erreur streaming, fallback sur génération normale: {str(stream_error)}")
            get_logger().warning(
                "Streaming failed, falling back to non-streaming",
                extra={
                    "component": "generation",
                    "conversation_id": conversation_id,
                    "error": str(stream_error),
                },
            )

            # S'assurer que le prompt est bien formaté avec la question
            prompt = get_prompts(question=state["question"])
            rag_prompt_formatted = prompt["rag_prompt"].format(
                context=docs_txt, question=state["question"]
            )

            def _generate():
                # Utiliser le gestionnaire de clés avec fallback automatique
                return get_runtime().groq_key_manager.invoke_with_fallback(
                    [HumanMessage(content=rag_prompt_formatted)], json_mode=False
                )

            generation = retry_with_backoff_advanced(
                _generate, circuit_breaker=get_runtime().llm_circuit_breaker
            )
            full_response = (
                generation.content if hasattr(generation, "content") else str(generation)
            )

            # Traiter les citations
            if citations_enabled:
                sources = extract_sources_from_documents(state["documents"])
                full_response, references = format_citations(full_response, sources)
                if references:
                    full_response = full_response + references

        elapsed_time = time.time() - start_time
        latencies["generation"] = elapsed_time

        get_logger().info(
            "Generation with streaming completed",
            extra={
                "component": "generation",
                "conversation_id": conversation_id,
                "data": {"latency": elapsed_time, "citations_enabled": citations_enabled},
            },
        )

        return {
            "generation": full_response,
            "loop_step": state.get("loop_step", 0) + 1,
            "latencies": latencies,
        }

    except Exception as e:
        elapsed_time = time.time() - start_time
        latencies["generation"] = elapsed_time
        error_msg = f"Erreur lors de la génération avec streaming: {str(e)}"
        print(f"❌ {error_msg}")
        get_logger().error(
            "Generation with streaming failed",
            extra={"component": "generation", "conversation_id": conversation_id},
            exc_info=True,
        )
        # Lever une exception métier claire, déjà importée en haut du fichier
        raise GenerationException(error_msg) from e
