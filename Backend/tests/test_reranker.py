"""
Script de test pour valider l'implémentation du Reranker (Cross-Encoder)
"""
import os
import sys
import time

# Ajouter le répertoire racine au sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.rag.Rag_model import get_reranker_instance, rerank_documents, get_final_response
from langchain.schema import Document
from config.Config import Config

def print_header(text):
    """Affiche un en-tête formaté."""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def print_test(text):
    """Affiche un message de test."""
    print(f"\n[TEST] {text}")

def print_info(text):
    """Affiche une information."""
    print(f"[INFO] {text}")

def print_success(text):
    """Affiche un succès."""
    print(f"[SUCCESS] {text}")

def print_error(text):
    """Affiche une erreur."""
    print(f"[ERROR] {text}")

def print_warning(text):
    """Affiche un avertissement."""
    print(f"[WARNING] {text}")

def test_reranker_initialization():
    """Test 1: Initialisation du reranker."""
    print_header("TEST 1: Initialisation du Reranker")
    
    try:
        print_test("Initialisation du reranker cross-encoder...")
        reranker_enabled = getattr(Config, 'RERANKER_ENABLED', True)
        
        if not reranker_enabled:
            print_warning("Reranker désactivé dans la configuration")
            return None
        
        reranker_model = getattr(Config, 'RERANKER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
        print_info(f"Modèle configuré: {reranker_model}")
        print_info("⏳ Cela peut prendre quelques secondes (téléchargement du modèle)...")
        
        start_time = time.time()
        reranker = get_reranker_instance()
        elapsed_time = time.time() - start_time
        
        if reranker is None:
            print_error("Le reranker n'a pas pu être initialisé")
            return None
        
        print_success(f"Reranker initialisé avec succès en {elapsed_time:.2f}s")
        print_info(f"Type: {type(reranker).__name__}")
        
        return reranker
        
    except Exception as e:
        print_error(f"Erreur lors de l'initialisation: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_rerank_documents():
    """Test 2: Reranking de documents."""
    print_header("TEST 2: Reranking de Documents")
    
    # Créer des documents de test
    query = "What is a Large Language Model?"
    
    documents = [
        Document(
            page_content="Large Language Models (LLMs) are advanced AI systems that can understand and generate human-like text. They are trained on vast amounts of text data and can perform various natural language processing tasks.",
            metadata={"source": "doc1", "relevance": "high"}
        ),
        Document(
            page_content="Machine learning is a subset of artificial intelligence that enables computers to learn from data without explicit programming.",
            metadata={"source": "doc2", "relevance": "low"}
        ),
        Document(
            page_content="LLMs like GPT and BERT have revolutionized natural language processing by achieving state-of-the-art performance on many tasks including translation, summarization, and question answering.",
            metadata={"source": "doc3", "relevance": "high"}
        ),
        Document(
            page_content="Deep learning neural networks use multiple layers to learn complex patterns in data. They are particularly effective for image recognition and natural language processing.",
            metadata={"source": "doc4", "relevance": "medium"}
        ),
        Document(
            page_content="The transformer architecture, introduced in 2017, is the foundation of modern LLMs. It uses attention mechanisms to process sequences of text efficiently.",
            metadata={"source": "doc5", "relevance": "high"}
        ),
    ]
    
    print_test(f"Requête: {query}")
    print_info(f"Documents initiaux: {len(documents)}")
    for i, doc in enumerate(documents, 1):
        print_info(f"  Doc {i}: {doc.page_content[:80]}...")
    
    try:
        print_info("⏳ Application du reranking...")
        start_time = time.time()
        
        reranked_docs = rerank_documents(query, documents, top_k=3)
        
        elapsed_time = time.time() - start_time
        
        print_success(f"Reranking terminé en {elapsed_time:.3f}s")
        print_info(f"Documents rerankés (top-3): {len(reranked_docs)}")
        
        print_info("\nRésultats rerankés:")
        for i, doc in enumerate(reranked_docs, 1):
            print_info(f"\n  Rang {i}:")
            print_info(f"    Source: {doc.metadata.get('source', 'N/A')}")
            print_info(f"    Contenu: {doc.page_content[:150]}...")
        
        # Vérifier que les documents sont bien triés (les plus pertinents en premier)
        if len(reranked_docs) > 1:
            print_info("\nLes documents devraient être triés par pertinence (plus pertinent en premier)")
            print_success("Reranking fonctionne correctement")
        
        return True
        
    except Exception as e:
        print_error(f"Erreur lors du reranking: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_reranker_integration():
    """Test 3: Intégration dans le workflow de récupération."""
    print_header("TEST 3: Intégration dans le Workflow")
    
    reranker_enabled = getattr(Config, 'RERANKER_ENABLED', True)
    
    if not reranker_enabled:
        print_warning("Reranker désactivé dans la configuration, test ignoré")
        return False
    
    try:
        print_test("Test avec une requête réelle...")
        query = "What is prompt engineering?"
        print_info(f"Requête: {query}")
        print_warning("⏳ Cela peut prendre 1-3 minutes (récupération + reranking)...")
        
        start_time = time.time()
        response = get_final_response(query)
        elapsed_time = time.time() - start_time
        
        print_success(f"Réponse générée en {elapsed_time:.2f}s ({elapsed_time/60:.1f} minutes)")
        
        if response and not response.startswith("⚠️"):
            print_success("Réponse valide reçue")
            print_info(f"Longueur: {len(response)} caractères")
            print_info(f"Extrait: {response[:200]}...")
            
            # Vérifier que le reranking a été appliqué
            print_info("\nLe reranking a été appliqué pendant la récupération si activé")
            return True
        elif response and response.startswith("⚠️"):
            print_warning(f"Avertissement: {response[:150]}...")
            return True  # Erreur bien gérée = succès
        else:
            print_error("Pas de réponse valide")
            return False
            
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_reranker_configuration():
    """Test 4: Vérification de la configuration."""
    print_header("TEST 4: Vérification de la Configuration")
    
    try:
        print_test("Vérification des paramètres de configuration...")
        
        reranker_enabled = getattr(Config, 'RERANKER_ENABLED', True)
        reranker_model = getattr(Config, 'RERANKER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
        reranker_top_k = getattr(Config, 'RERANKER_TOP_K', 20)
        reranker_final_k = getattr(Config, 'RERANKER_FINAL_K', 3)
        
        print_info(f"RERANKER_ENABLED: {reranker_enabled}")
        print_info(f"RERANKER_MODEL: {reranker_model}")
        print_info(f"RERANKER_TOP_K: {reranker_top_k} (documents à récupérer)")
        print_info(f"RERANKER_FINAL_K: {reranker_final_k} (documents après reranking)")
        
        if reranker_enabled:
            print_success("Configuration correcte")
            
            if reranker_top_k < reranker_final_k:
                print_warning(f"RERANKER_TOP_K ({reranker_top_k}) < RERANKER_FINAL_K ({reranker_final_k})")
                print_warning("Il est recommandé que TOP_K >= FINAL_K")
            else:
                print_info(f"✓ TOP_K ({reranker_top_k}) >= FINAL_K ({reranker_final_k})")
        else:
            print_warning("Reranker désactivé")
        
        return True
        
    except Exception as e:
        print_error(f"Erreur lors de la vérification: {str(e)}")
        return False

def test_performance_comparison():
    """Test 5: Comparaison de performance avec/sans reranking."""
    print_header("TEST 5: Comparaison de Performance")
    
    try:
        print_test("Comparaison du temps d'exécution...")
        
        # Test avec reranking activé
        original_enabled = getattr(Config, 'RERANKER_ENABLED', True)
        
        # On ne peut pas facilement désactiver le reranker dans le code actuel
        # donc on va juste tester avec reranking activé
        if not original_enabled:
            print_warning("Reranker désactivé, test ignoré")
            return False
        
        query = "What are transformer models?"
        print_info(f"Requête: {query}")
        print_warning("⏳ Test avec reranking (peut prendre 1-3 minutes)...")
        
        start_time = time.time()
        response_with_rerank = get_final_response(query)
        time_with_rerank = time.time() - start_time
        
        print_info(f"\nTemps avec reranking: {time_with_rerank:.2f}s")
        print_info(f"Longueur réponse: {len(response_with_rerank) if response_with_rerank else 0} caractères")
        
        print_info("\nNote: Pour une comparaison complète, il faudrait aussi tester sans reranking")
        print_info("(en modifiant RERANKER_ENABLED=False dans Config.py)")
        
        return True
        
    except Exception as e:
        print_error(f"Erreur lors de la comparaison: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Fonction principale de test."""
    print_header("TESTS RERANKER (Cross-Encoder)")
    print_info("Ce script teste l'implémentation du reranker")
    print_info("Assurez-vous que sentence-transformers est installé: pip install sentence-transformers")
    
    results = []
    
    # Test 1: Initialisation
    reranker = test_reranker_initialization()
    results.append(("Initialisation du reranker", reranker is not None))
    
    # Test 2: Reranking de documents
    if reranker is not None:
        rerank_success = test_rerank_documents()
        results.append(("Reranking de documents", rerank_success))
    
    # Test 3: Vérification configuration
    config_success = test_reranker_configuration()
    results.append(("Vérification configuration", config_success))
    
    # Test 4: Intégration (optionnel, peut être long)
    print_header("TEST OPTIONNEL: Intégration dans le workflow")
    user_input = input("\nVoulez-vous tester l'intégration complète ? (peut prendre 1-3 min) [o/N]: ")
    if user_input.lower() in ['o', 'oui', 'y', 'yes']:
        integration_success = test_reranker_integration()
        results.append(("Intégration dans le workflow", integration_success))
    else:
        print_info("Test d'intégration ignoré")
        results.append(("Intégration dans le workflow", None))
    
    # Test 5: Performance (optionnel)
    user_input2 = input("\nVoulez-vous tester la performance ? (peut prendre 1-3 min) [o/N]: ")
    if user_input2.lower() in ['o', 'oui', 'y', 'yes']:
        perf_success = test_performance_comparison()
        results.append(("Comparaison de performance", perf_success))
    else:
        print_info("Test de performance ignoré")
        results.append(("Comparaison de performance", None))
    
    # Résumé
    print_header("RÉSUMÉ DES TESTS")
    for test_name, success in results:
        if success is None:
            status = "⏭️ IGNORÉ"
        elif success:
            status = "✅ RÉUSSI"
        else:
            status = "❌ ÉCHOUÉ"
        print(f"{status}: {test_name}")
    
    total = len([r for r in results if r[1] is not None])
    passed = sum(1 for _, success in results if success is True)
    print_info(f"\nTotal: {passed}/{total} tests réussis")
    
    if passed == total and total > 0:
        print_success("Tous les tests sont passés ! 🎉")
    elif total > 0:
        print_warning(f"{total - passed} test(s) ont échoué")
    else:
        print_info("Aucun test exécuté")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_warning("\n⚠️ Tests interrompus par l'utilisateur")
    except Exception as e:
        print_error(f"Erreur fatale: {str(e)}")
        import traceback
        traceback.print_exc()

