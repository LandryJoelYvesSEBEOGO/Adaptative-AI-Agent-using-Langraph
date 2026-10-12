import time
import uuid

from config.Config import Config
from src.core.exceptions import (
    LLMQuotaException,
    MaxRetriesException,
    RetrievalException,
    WebSearchException,  # ✅ utilisé pour les erreurs de génération (streaming et non-streaming)
)
from src.core.logger import get_logger
from src.rag.generation.generate import generate_stream
from src.rag.generation.rewrite import Rewrite_query
from src.rag.grading.documents import grade_documents
from src.rag.grading.generation import grade_generation_v_documents_and_question
from src.rag.grading.quality import grade_answer_quality
from src.rag.graph import get_graph
from src.rag.retrieval.nodes import retrieve, web_search
from src.rag.routing import route_question
from src.rag.state import GraphState


# Final response function
def get_final_response(query: str) -> str:
    """Point d'entrée principal pour obtenir une réponse RAG."""
    conversation_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())

    # Début de la mesure end-to-end
    start_time = time.time()
    latencies = {}

    try:
        get_logger().info(
            "Request started",
            extra={
                "component": "rag",
                "conversation_id": conversation_id,
                "trace_id": trace_id,
                "data": {"query": query[:100]},
            },
        )

        if not query or not query.strip():
            return "⚠️ Veuillez fournir une question valide."

        # Réécriture de la requête (avec fallback sur query originale)
        try:
            rewritten_query = Rewrite_query(query, history=None)
        except Exception as e:
            print(f"⚠️ Erreur réécriture, utilisation query originale: {str(e)}")
            rewritten_query = query

        # Initialisation de l'état avec max_retries, conversation_id et latencies
        max_retries = getattr(Config, "MAX_RETRIES", 3)
        initial_state = GraphState(
            question=rewritten_query,
            generation="",
            web_search="No",
            max_retries=max_retries,
            answers=0,
            loop_step=0,
            documents=[],
            error_history=[],
            conversation_id=conversation_id,
            latencies=latencies,
        )

        # Exécution du workflow
        final_state = get_graph().invoke(initial_state)

        # Récupérer les latences mises à jour depuis le state
        latencies = final_state.get("latencies", latencies)

        # Extraction de la réponse
        generation = final_state.get("generation")
        if generation and hasattr(generation, "content"):
            response = generation.content
        elif generation:
            response = str(generation)
        else:
            response = "⚠️ Aucune réponse générée. Veuillez reformuler votre question."

        # Mesurer latence end-to-end
        latencies["end_to_end"] = time.time() - start_time

        get_logger().info(
            "Request completed",
            extra={
                "component": "rag",
                "conversation_id": conversation_id,
                "trace_id": trace_id,
                "data": {"latency": latencies["end_to_end"]},
            },
        )

        return response

    except MaxRetriesException:
        latencies["end_to_end"] = time.time() - start_time
        error_msg = "⚠️ Désolé, j'ai atteint le nombre maximum de tentatives. Veuillez reformuler votre question ou réessayer plus tard."

        get_logger().warning(
            "Request max retries",
            extra={"component": "rag", "conversation_id": conversation_id, "trace_id": trace_id},
        )

        return error_msg

    except LLMQuotaException:
        latencies["end_to_end"] = time.time() - start_time
        error_msg = (
            "⚠️ Le service est temporairement saturé. Veuillez réessayer dans quelques instants."
        )

        get_logger().error(
            "Request quota exceeded",
            extra={"component": "rag", "conversation_id": conversation_id, "trace_id": trace_id},
        )

        return error_msg

    except RetrievalException:
        latencies["end_to_end"] = time.time() - start_time
        error_msg = (
            "⚠️ Impossible de trouver des documents pertinents. Veuillez reformuler votre question."
        )

        get_logger().error(
            "Request retrieval failed",
            extra={"component": "rag", "conversation_id": conversation_id, "trace_id": trace_id},
        )

        return error_msg

    except WebSearchException:
        latencies["end_to_end"] = time.time() - start_time
        error_msg = "⚠️ Erreur lors de la recherche web. Veuillez réessayer."

        get_logger().error(
            "Request web search failed",
            extra={"component": "rag", "conversation_id": conversation_id, "trace_id": trace_id},
        )

        return error_msg

    except Exception as e:
        latencies["end_to_end"] = time.time() - start_time
        error_msg = str(e)

        # Enregistrer l'erreur

        get_logger().error(
            "Request failed",
            extra={
                "component": "rag",
                "conversation_id": conversation_id,
                "trace_id": trace_id,
                "data": {"error": error_msg},
            },
            exc_info=True,
        )

        raise


def get_final_response_stream(query: str):
    """
    Point d'entrée principal pour obtenir une réponse RAG avec streaming.
    Retourne un générateur qui yield les chunks de la réponse.

    Args:
        query: Question de l'utilisateur

    Yields:
        str: Chunks de la réponse au fur et à mesure de la génération
    """
    conversation_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())

    # Début de la mesure end-to-end
    start_time = time.time()
    latencies = {}

    try:
        get_logger().info(
            "Streaming request started",
            extra={
                "component": "rag",
                "conversation_id": conversation_id,
                "trace_id": trace_id,
                "data": {"query": query[:100]},
            },
        )

        if not query or not query.strip():
            yield "⚠️ Veuillez fournir une question valide."
            return

        # Réécriture de la requête
        try:
            rewritten_query = Rewrite_query(query, history=None)
        except Exception as e:
            print(f"⚠️ Erreur réécriture, utilisation query originale: {str(e)}")
            rewritten_query = query

        # Initialisation de l'état
        max_retries = getattr(Config, "MAX_RETRIES", 3)
        initial_state = GraphState(
            question=rewritten_query,
            generation="",
            web_search="No",
            max_retries=max_retries,
            answers=0,
            loop_step=0,
            documents=[],
            error_history=[],
            conversation_id=conversation_id,
            latencies=latencies,
        )

        # Exécuter le workflow jusqu'à la génération
        # On doit exécuter manuellement les étapes jusqu'à generate
        current_state = initial_state

        # Route question
        route = route_question(current_state)
        if route == "websearch":
            current_state = web_search(current_state)
        else:
            current_state = retrieve(current_state)
            current_state = grade_documents(current_state)

            # Décider si on fait web search
            if current_state.get("web_search") == "Yes":
                current_state = web_search(current_state)

        # Maintenant on génère avec streaming
        # Utiliser generate_stream avec callback
        # Note: On doit adapter car generate_stream attend un callback, pas un générateur
        # Solution: créer un wrapper qui yield les chunks

        chunks_received = []

        def stream_callback_wrapper(chunk: str):
            """Wrapper pour collecter les chunks."""
            chunks_received.append(chunk)

        # Générer avec streaming
        generation_state = generate_stream(current_state, stream_callback=stream_callback_wrapper)

        # Yielder tous les chunks
        for chunk in chunks_received:
            yield chunk

        # Mettre à jour l'état final
        final_state = generation_state

        # Continuer avec le grading (sans streaming)
        # Note: Le grading et quality scoring ne stream pas
        try:
            grade_result = grade_generation_v_documents_and_question(final_state)
            if grade_result == "useful":
                # Succès
                pass
            elif grade_result == "not supported" and final_state.get("loop_step", 0) < max_retries:
                # Retry (ne devrait pas arriver souvent avec streaming)
                print("⚠️ Retry nécessaire après streaming")
        except Exception as e:
            print(f"⚠️ Erreur lors du grading: {str(e)}")

        # Exécuter le quality scoring aussi
        try:
            final_state = grade_answer_quality(final_state)
        except Exception as e:
            print(f"⚠️ Erreur lors du quality scoring: {str(e)}")

        # Récupérer les latences
        latencies = final_state.get("latencies", latencies)
        latencies["end_to_end"] = time.time() - start_time

        # Récupérer la réponse complète depuis l'état final
        generation = final_state.get("generation", "")
        full_response = (
            generation
            if isinstance(generation, str)
            else (generation.content if hasattr(generation, "content") else str(generation))
        )

        get_logger().info(
            "Streaming request completed",
            extra={
                "component": "rag",
                "conversation_id": conversation_id,
                "trace_id": trace_id,
                "data": {"latency": latencies["end_to_end"]},
            },
        )

    except Exception as e:
        latencies["end_to_end"] = time.time() - start_time
        error_msg = f"⚠️ Erreur lors de la génération: {str(e)}"
        yield error_msg

        get_logger().error(
            "Streaming request failed",
            extra={
                "component": "rag",
                "conversation_id": conversation_id,
                "trace_id": trace_id,
                "data": {"error": str(e)},
            },
            exc_info=True,
        )
