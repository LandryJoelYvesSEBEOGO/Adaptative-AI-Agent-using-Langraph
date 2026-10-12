import time

from config.Config import Config

_retriever = None


def get_retriever_instance():
    """Récupère ou crée le retriever (lazy loading pour éviter blocage à l'import)."""
    global _retriever
    from src.rag.Data_processing import get_retriever

    if _retriever is None:
        print("[INIT] ⏳ Initialisation du retriever (première fois, peut prendre du temps)...")
        try:
            # Si reranker activé, récupérer plus de documents pour le reranking
            reranker_enabled = getattr(Config, "RERANKER_ENABLED", True)
            if reranker_enabled:
                reranker_top_k = getattr(Config, "RERANKER_TOP_K", 20)
                _retriever = get_retriever(k=reranker_top_k)
                print(f"[INIT] ✅ Retriever créé avec k={reranker_top_k} (pour reranking).")
            else:
                final_k = getattr(Config, "RERANKER_FINAL_K", 3)
                _retriever = get_retriever(k=final_k)
                print(f"[INIT] ✅ Retriever créé avec k={final_k}.")

            # IMPORTANT: Précharger le modèle d'embedding pour éviter le blocage au premier appel
            # Cela force le chargement du modèle en mémoire maintenant plutôt que lors du premier invoke
            print("[INIT] ⏳ Préchargement du modèle d'embedding (peut prendre 10-30s)...")
            try:
                start_preload = time.time()
                # Faire un appel test pour précharger le modèle
                test_docs = _retriever.invoke("test preload")
                preload_time = time.time() - start_preload
                print(f"[INIT] ✅ Modèle préchargé avec succès en {preload_time:.2f}s")
                print("[INIT] Le retriever est maintenant prêt à être utilisé sans blocage.")
            except Exception as preload_error:
                print(f"⚠️ [INIT] Attention: Échec du préchargement: {str(preload_error)}")
                print("[INIT] Le retriever sera initialisé lors du premier appel réel.")
                # On continue quand même, le retriever sera initialisé au premier appel

        except Exception as e:
            print(f"❌ [INIT] Erreur lors de l'initialisation du retriever: {str(e)}")
            raise
    return _retriever
