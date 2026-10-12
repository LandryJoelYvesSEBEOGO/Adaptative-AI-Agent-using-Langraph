"""
Script de test pour valider l'implémentation du Hybrid Search (Vector + BM25)
"""

import os
import sys
import time

# Ajouter le répertoire racine au sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.rag.Data_processing import get_retriever


def print_header(text):
    """Affiche un en-tête formaté."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_test(text):
    """Affiche un message de test."""
    print(f"\n[TEST] {text}")


def print_info(text):
    """Affiche une information."""
    print(f"[INFO] {text}")


def print_success(text):
    """Affiche un succès."""
    print(f"[SUCCESS] ✅ {text}")


def print_error(text):
    """Affiche une erreur."""
    print(f"[ERROR] ❌ {text}")


def print_warning(text):
    """Affiche un avertissement."""
    print(f"[WARNING] ⚠️ {text}")


def test_retriever_creation():
    """Test 1: Création du retriever avec Hybrid Search activé."""
    print_header("TEST 1: Création du Retriever (Hybrid Search)")

    try:
        print_test("Création du retriever avec hybrid search activé...")
        print_info("⏳ Cela peut prendre quelques secondes...")

        start_time = time.time()
        retriever = get_retriever(k=3, use_hybrid=True)
        elapsed_time = time.time() - start_time

        print_success(f"Retriever créé avec succès en {elapsed_time:.2f}s")

        # Vérifier le type de retriever
        from langchain.retrievers import EnsembleRetriever

        if isinstance(retriever, EnsembleRetriever):
            print_success("Type: EnsembleRetriever (Hybrid Search activé)")
            print_info(f"Nombre de retrievers: {len(retriever.retrievers)}")
            print_info(f"Poids: {retriever.weights}")
        else:
            print_warning(f"Type: {type(retriever).__name__} (Vector seulement)")

        return retriever, True

    except Exception as e:
        print_error(f"Erreur lors de la création du retriever: {str(e)}")
        import traceback

        traceback.print_exc()
        return None, False


def test_retriever_retrieval(retriever):
    """Test 2: Test de récupération de documents."""
    print_header("TEST 2: Récupération de Documents")

    if retriever is None:
        print_error("Retriever non disponible, test ignoré")
        return False

    try:
        test_queries = [
            "What is a Large Language Model?",
            "How does prompt engineering work?",
            "What are transformer models?",
        ]

        for i, query in enumerate(test_queries, 1):
            print_test(f"Requête {i}: {query}")

            start_time = time.time()
            documents = retriever.get_relevant_documents(query)
            elapsed_time = time.time() - start_time

            if documents and len(documents) > 0:
                print_success(f"✅ {len(documents)} documents récupérés en {elapsed_time:.3f}s")

                # Afficher un extrait du premier document
                first_doc = documents[0]
                preview = first_doc.page_content[:150].replace("\n", " ")
                print_info(f"Premier document (extrait): {preview}...")

                # Afficher les métadonnées si disponibles
                if hasattr(first_doc, "metadata") and first_doc.metadata:
                    print_info(f"Métadonnées: {list(first_doc.metadata.keys())}")
            else:
                print_warning("⚠️ Aucun document récupéré")

        return True

    except Exception as e:
        print_error(f"Erreur lors de la récupération: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_vector_only_retriever():
    """Test 3: Comparaison avec retriever vectoriel seul."""
    print_header("TEST 3: Comparaison Vector vs Hybrid")

    try:
        print_test("Création du retriever vectoriel seul...")
        vector_retriever = get_retriever(k=3, use_hybrid=False)
        print_success("Retriever vectoriel créé")

        print_test("Création du retriever hybrid...")
        hybrid_retriever = get_retriever(k=3, use_hybrid=True)
        print_success("Retriever hybrid créé")

        test_query = "What is prompt engineering?"
        print_test(f"Test avec la requête: {test_query}")

        # Test vectoriel
        print_info("Récupération avec retriever vectoriel...")
        start_time = time.time()
        vector_docs = vector_retriever.get_relevant_documents(test_query)
        vector_time = time.time() - start_time

        # Test hybrid
        print_info("Récupération avec retriever hybrid...")
        start_time = time.time()
        hybrid_docs = hybrid_retriever.get_relevant_documents(test_query)
        hybrid_time = time.time() - start_time

        print_info(f"Vector seul: {len(vector_docs)} documents en {vector_time:.3f}s")
        print_info(f"Hybrid: {len(hybrid_docs)} documents en {hybrid_time:.3f}s")

        # Vérifier si les résultats diffèrent
        if len(vector_docs) != len(hybrid_docs):
            print_info("Les deux retrievers retournent un nombre différent de documents")

        return True

    except Exception as e:
        print_error(f"Erreur lors de la comparaison: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Fonction principale de test."""
    print_header("TESTS HYBRID SEARCH (Vector + BM25)")
    print_info("Ce script teste l'implémentation du Hybrid Search")
    print_info("Assurez-vous que ChromaDB existe déjà ou patientez pendant sa création...")

    results = []

    # Test 1: Création du retriever
    retriever, success = test_retriever_creation()
    results.append(("Création du retriever", success))

    if success and retriever:
        # Test 2: Récupération de documents
        retrieval_success = test_retriever_retrieval(retriever)
        results.append(("Récupération de documents", retrieval_success))

        # Test 3: Comparaison
        comparison_success = test_vector_only_retriever()
        results.append(("Comparaison Vector vs Hybrid", comparison_success))

    # Résumé
    print_header("RÉSUMÉ DES TESTS")
    for test_name, success in results:
        status = "✅ RÉUSSI" if success else "❌ ÉCHOUÉ"
        print(f"{status}: {test_name}")

    total = len(results)
    passed = sum(1 for _, success in results if success)
    print_info(f"\nTotal: {passed}/{total} tests réussis")

    if passed == total:
        print_success("Tous les tests sont passés ! 🎉")
    else:
        print_warning(f"{total - passed} test(s) ont échoué")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_warning("\n⚠️ Tests interrompus par l'utilisateur")
    except Exception as e:
        print_error(f"Erreur fatale: {str(e)}")
        import traceback

        traceback.print_exc()
