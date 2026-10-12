from typing import List

from langchain_core.documents import Document

from config.Config import Config

_reranker = None


def get_reranker_instance():
    """Récupère ou crée le reranker cross-encoder (lazy loading)."""
    global _reranker
    if _reranker is None:
        reranker_enabled = getattr(Config, "RERANKER_ENABLED", True)
        if not reranker_enabled:
            return None

        reranker_model = getattr(Config, "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        print(f"[RERANKER] ⏳ Initialisation du reranker: {reranker_model}...")
        try:
            _reranker = __import__("sentence_transformers").CrossEncoder(reranker_model)
            print("[RERANKER] ✅ Reranker initialisé avec succès")
        except Exception as e:
            print(f"[RERANKER] ❌ Erreur lors de l'initialisation: {str(e)}")
            print("[RERANKER] Le reranking sera désactivé pour cette session")
            return None
    return _reranker


def rerank_documents(query: str, documents: List[Document], top_k: int = None) -> List[Document]:
    """
    Rerank les documents avec un cross-encoder.

    Args:
        query: La question de l'utilisateur
        documents: Liste de documents à reranker
        top_k: Nombre de documents à retourner après reranking

    Returns:
        Liste de documents rerankés (top_k premiers)
    """
    if not documents or len(documents) == 0:
        return documents

    reranker = get_reranker_instance()
    if reranker is None:
        # Si reranker non disponible, retourner les documents originaux
        return documents[:top_k] if top_k else documents

    if top_k is None:
        top_k = getattr(Config, "RERANKER_FINAL_K", 3)

    try:
        # Préparer les paires (query, document) pour le cross-encoder
        pairs = [[query, doc.page_content] for doc in documents]

        # Calculer les scores de pertinence
        scores = reranker.predict(pairs)

        # Créer une liste de tuples (score, document) et trier par score décroissant
        scored_docs = list(zip(scores, documents))
        scored_docs.sort(key=lambda x: x[0], reverse=True)

        # Retourner les top_k documents
        reranked_docs = [doc for _, doc in scored_docs[:top_k]]

        return reranked_docs

    except Exception as e:
        print(f"[RERANKER] ⚠️ Erreur lors du reranking: {str(e)}")
        print("[RERANKER] Retour des documents originaux (sans reranking)")
        return documents[:top_k] if top_k else documents
