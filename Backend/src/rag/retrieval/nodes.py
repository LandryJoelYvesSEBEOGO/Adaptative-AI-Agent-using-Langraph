import time
from typing import Dict

from langchain_core.documents import Document

from config.Config import Config
from src.core.exceptions import (
    RetrievalException,
    WebSearchException,  # ✅ utilisé pour les erreurs de génération (streaming et non-streaming)
)
from src.core.logger import get_logger
from src.core.retrieval_metrics import get_retrieval_metrics_collector
from src.core.retry_policy import retry_with_backoff_advanced
from src.rag.retrieval.reranker import rerank_documents
from src.rag.retrieval.retriever import get_retriever_instance
from src.rag.runtime import get_runtime


# Node functions
def retrieve(state: Dict) -> Dict:
    """Retrieve documents from the vector store."""
    start_time = time.time()
    conversation_id = state.get("conversation_id", "unknown")
    latencies = state.get("latencies", {})

    try:
        get_logger().info(
            "Retrieval started",
            extra={"component": "retrieval", "conversation_id": conversation_id},
        )
        print("---RETRIEVE---")
        if not state.get("question"):
            raise RetrievalException("Question manquante pour la récupération")

        print(f"[RETRIEVE] Recherche de documents pour: {state['question'][:50]}...")

        # Obtenir le retriever (lazy loading)
        print("[RETRIEVE] Obtention du retriever...")
        current_retriever = get_retriever_instance()
        print("[RETRIEVE] ✅ Retriever obtenu.")

        print("[RETRIEVE] Appel retriever.invoke()...")
        print("[RETRIEVE] Cette etape va:")
        print("[RETRIEVE]   1. Generer l'embedding de la question")
        print("[RETRIEVE]   2. Rechercher dans ChromaDB")
        print("[RETRIEVE] ⏳ Veuillez patienter...")

        # IMPORTANT: LangGraph exécute les nœuds directement, sans threading supplémentaire
        # Le threading peut causer des conflits avec le runtime de LangGraph
        # Appel direct: si ça bloque, c'est que le problème vient de NomicEmbeddings/ChromaDB
        try:
            # Déterminer les paramètres du reranker
            reranker_enabled = getattr(Config, "RERANKER_ENABLED", True)
            final_k = getattr(Config, "RERANKER_FINAL_K", 3)

            # Le retriever a déjà été configuré avec le bon k dans get_retriever_instance
            print("[RETRIEVE] ⏳ Début de retriever.invoke()...")
            documents = current_retriever.invoke(state["question"])

            # Appliquer le reranking si activé
            if reranker_enabled and len(documents) > 1:
                print(f"[RETRIEVE] ⏳ Reranking de {len(documents)} documents (top-{final_k})...")
                rerank_start = time.time()
                documents = rerank_documents(state["question"], documents, top_k=final_k)
                rerank_time = time.time() - rerank_start
                latencies["reranking"] = rerank_time
                print(
                    f"[RETRIEVE] ✅ Reranking terminé en {rerank_time:.3f}s ({len(documents)} documents finaux)"
                )
            elif not reranker_enabled:
                # Si reranker désactivé, prendre les k premiers
                documents = documents[:final_k]

            elapsed_time = time.time() - start_time
            latencies["retrieval"] = elapsed_time
            print(f"[RETRIEVE] ✅ retriever.invoke() terminé avec succès en {elapsed_time:.2f}s")
        except Exception as e:
            elapsed_time = time.time() - start_time
            latencies["retrieval"] = elapsed_time
            print(
                f"[RETRIEVE] ❌ Exception apres {elapsed_time:.2f}s: {type(e).__name__}: {str(e)}"
            )
            import traceback

            print("[RETRIEVE] Stack trace complete:")
            traceback.print_exc()
            raise RetrievalException(f"Erreur lors de l'invocation du retriever: {str(e)}") from e

        if documents is None:
            print("❌ [RETRIEVE] Aucun resultat retourne (None)")
            raise RetrievalException("Aucun resultat retourne par le retriever")

        if not documents or len(documents) == 0:
            print("⚠️ [RETRIEVE] Aucun document trouve")
            get_logger().warning(
                "No documents found",
                extra={"component": "retrieval", "conversation_id": conversation_id},
            )
            return {
                "documents": [],
                "error_history": state.get("error_history", []) + ["Aucun document trouve"],
                "latencies": latencies,
                "question": state.get("question"),  # Préserver la question
                "conversation_id": conversation_id,
            }

        print(f"[RETRIEVE] ✅ {len(documents)} documents trouves en {elapsed_time:.2f}s.")

        # Enregistrer les résultats de retrieval pour les métriques
        retrieval_metrics_enabled = getattr(Config, "RETRIEVAL_METRICS_ENABLED", True)
        if retrieval_metrics_enabled:
            try:
                retrieval_collector = get_retrieval_metrics_collector()
                # Extraire les IDs des documents récupérés
                retrieved_doc_ids = []
                retrieved_sources = []
                for doc in documents:
                    # Utiliser parent_doc_id si disponible, sinon chunk_id, sinon source
                    doc_id = (
                        doc.metadata.get("parent_doc_id")
                        or doc.metadata.get("chunk_id")
                        or doc.metadata.get("source", "unknown")
                    )
                    retrieved_doc_ids.append(str(doc_id))
                    source = doc.metadata.get("source", "unknown")
                    retrieved_sources.append(str(source))

                retrieval_collector.record_retrieval(
                    conversation_id=conversation_id,
                    query=state["question"],
                    retrieved_doc_ids=retrieved_doc_ids,
                    retrieved_sources=retrieved_sources,
                )
            except Exception as e:
                # Ne pas faire échouer le retrieval si l'enregistrement échoue
                print(
                    f"[WARNING] Erreur lors de l'enregistrement des métriques retrieval: {str(e)}"
                )

        get_logger().info(
            "Retrieval completed",
            extra={
                "component": "retrieval",
                "conversation_id": conversation_id,
                "data": {"latency": elapsed_time, "num_documents": len(documents)},
            },
        )
        # Préserver tous les champs du state, notamment la question
        return {
            "documents": documents,
            "latencies": latencies,
            "question": state.get("question"),  # Préserver la question
            "conversation_id": conversation_id,
            "error_history": state.get("error_history", []),
        }

    except RetrievalException:
        raise
    except Exception as e:
        elapsed_time = time.time() - start_time
        latencies["retrieval"] = elapsed_time
        print(f"❌ [RETRIEVE] Exception non capturee: {str(e)}")
        get_logger().error(
            "Retrieval failed",
            extra={"component": "retrieval", "conversation_id": conversation_id},
            exc_info=True,
        )
        import traceback

        traceback.print_exc()
        raise RetrievalException(f"Erreur recuperation: {str(e)}") from e


def web_search(state: Dict) -> Dict:
    """Perform a web search based on the question."""
    start_time = time.time()
    conversation_id = state.get("conversation_id", "unknown")
    latencies = state.get("latencies", {})

    try:
        get_logger().info(
            "Web search started",
            extra={"component": "web_search", "conversation_id": conversation_id},
        )
        print("---WEB SEARCH---")

        if not state.get("question"):
            raise WebSearchException("Question manquante pour la recherche web")

        def _search():
            return get_runtime().web_search_tool.invoke({"query": state["question"]})

        docs = retry_with_backoff_advanced(
            _search, max_retries=2, circuit_breaker=get_runtime().web_search_circuit_breaker
        )

        if not docs:
            print("⚠️ Aucun résultat de recherche web")
            elapsed_time = time.time() - start_time
            latencies["web_search"] = elapsed_time
            return {
                "documents": state.get("documents", []),
                "latencies": latencies,
                "question": state.get("question"),  # Préserver la question
                "conversation_id": conversation_id,
            }

        web_results = "\n".join([d.get("content", "") for d in docs if d.get("content")])

        if not web_results:
            print("⚠️ Résultats web vides")
            elapsed_time = time.time() - start_time
            latencies["web_search"] = elapsed_time
            return {
                "documents": state.get("documents", []),
                "latencies": latencies,
                "question": state.get("question"),  # Préserver la question
                "conversation_id": conversation_id,
            }

        documents = state.get("documents", [])
        documents.append(Document(page_content=web_results))

        elapsed_time = time.time() - start_time
        latencies["web_search"] = elapsed_time

        get_logger().info(
            "Web search completed",
            extra={
                "component": "web_search",
                "conversation_id": conversation_id,
                "data": {"latency": elapsed_time},
            },
        )

        # Préserver tous les champs du state, notamment la question
        return {
            "documents": documents,
            "latencies": latencies,
            "question": state.get("question"),  # Préserver la question
            "conversation_id": conversation_id,
            "error_history": state.get("error_history", []),
        }
    except Exception as e:
        elapsed_time = time.time() - start_time
        latencies["web_search"] = elapsed_time
        error_msg = f"Erreur lors de la recherche web: {str(e)}"
        print(f"❌ {error_msg}")
        get_logger().error(
            "Web search failed",
            extra={"component": "web_search", "conversation_id": conversation_id},
            exc_info=True,
        )
        # Ne pas bloquer, continuer avec les documents existants mais préserver la question
        return {
            "documents": state.get("documents", []),
            "latencies": latencies,
            "question": state.get("question"),  # Préserver la question
            "conversation_id": conversation_id,
            "error_history": state.get("error_history", []) + [f"Erreur web_search: {str(e)}"],
        }
