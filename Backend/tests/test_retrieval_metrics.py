"""
Script de test pour les métriques de retrieval (Precision, Recall, MAP)
"""
import os
import sys
from pathlib import Path

# Ajouter le répertoire racine au sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.retrieval_metrics import (
    get_retrieval_metrics_collector,
    calculate_precision_at_k,
    calculate_recall_at_k,
    calculate_average_precision,
    calculate_mean_average_precision,
    calculate_retrieval_metrics
)


def test_basic_precision_recall():
    """Test des fonctions de base Precision@k et Recall@k."""
    print("\n" + "="*60)
    print("TEST 1: Precision@k et Recall@k (Basique)")
    print("="*60)
    
    # Cas de test simple
    retrieved_ids = ["doc1", "doc2", "doc3", "doc4", "doc5"]
    relevant_ids = {"doc1", "doc3", "doc5", "doc7"}
    
    # Precision@3 = 2 pertinents sur 3 récupérés = 2/3 = 0.667
    precision_3 = calculate_precision_at_k(retrieved_ids, relevant_ids, k=3)
    print(f"Precision@3: {precision_3:.3f} (attendu: ~0.667)")
    assert abs(precision_3 - 0.667) < 0.01, f"Precision@3 incorrecte: {precision_3}"
    
    # Recall@3 = 2 pertinents récupérés sur 4 pertinents totaux = 2/4 = 0.5
    recall_3 = calculate_recall_at_k(retrieved_ids, relevant_ids, k=3)
    print(f"Recall@3: {recall_3:.3f} (attendu: 0.500)")
    assert abs(recall_3 - 0.5) < 0.01, f"Recall@3 incorrect: {recall_3}"
    
    # Precision@5 = 3 pertinents sur 5 récupérés = 3/5 = 0.6
    precision_5 = calculate_precision_at_k(retrieved_ids, relevant_ids, k=5)
    print(f"Precision@5: {precision_5:.3f} (attendu: 0.600)")
    assert abs(precision_5 - 0.6) < 0.01, f"Precision@5 incorrecte: {precision_5}"
    
    # Recall@5 = 3 pertinents récupérés sur 4 pertinents totaux = 3/4 = 0.75
    recall_5 = calculate_recall_at_k(retrieved_ids, relevant_ids, k=5)
    print(f"Recall@5: {recall_5:.3f} (attendu: 0.750)")
    assert abs(recall_5 - 0.75) < 0.01, f"Recall@5 incorrect: {recall_5}"
    
    print("✅ Test Precision/Recall basique réussi!")


def test_average_precision():
    """Test du calcul de Average Precision."""
    print("\n" + "="*60)
    print("TEST 2: Average Precision (AP)")
    print("="*60)
    
    # Cas de test : 3 documents pertinents sur 5 récupérés
    retrieved_ids = ["doc1", "doc2", "doc3", "doc4", "doc5"]
    relevant_ids = {"doc1", "doc3", "doc5"}
    
    # AP = (1/1 + 2/3 + 3/5) / 3 = (1 + 0.667 + 0.6) / 3 = 2.267/3 = 0.756
    ap = calculate_average_precision(retrieved_ids, relevant_ids)
    print(f"Average Precision: {ap:.3f} (attendu: ~0.756)")
    
    # Test avec aucun document pertinent
    ap_zero = calculate_average_precision(retrieved_ids, set())
    print(f"AP (aucun pertinent): {ap_zero:.3f} (attendu: 0.000)")
    assert ap_zero == 0.0, "AP devrait être 0 si aucun document pertinent"
    
    # Test avec aucun document récupéré
    ap_empty = calculate_average_precision([], relevant_ids)
    print(f"AP (aucun récupéré): {ap_empty:.3f} (attendu: 0.000)")
    assert ap_empty == 0.0, "AP devrait être 0 si aucun document récupéré"
    
    print("✅ Test Average Precision réussi!")


def test_mean_average_precision():
    """Test du calcul de Mean Average Precision (MAP)."""
    print("\n" + "="*60)
    print("TEST 3: Mean Average Precision (MAP)")
    print("="*60)
    
    # Créer des résultats de retrieval simulés
    retrieval_results = [
        {
            "query": "test query 1",
            "retrieved_doc_ids": ["doc1", "doc2", "doc3"],
        },
        {
            "query": "test query 2",
            "retrieved_doc_ids": ["doc4", "doc5", "doc6"],
        }
    ]
    
    # Ground truth
    ground_truth = {
        "test query 1": {"doc1", "doc3"},  # 2 pertinents sur 3 récupérés
        "test query 2": {"doc4", "doc5", "doc7"},  # 2 pertinents sur 3 récupérés
    }
    
    map_score = calculate_mean_average_precision(retrieval_results, ground_truth)
    print(f"MAP: {map_score:.3f}")
    print("✅ Test MAP réussi!")


def test_retrieval_metrics_full():
    """Test du calcul complet des métriques."""
    print("\n" + "="*60)
    print("TEST 4: Calcul complet des métriques")
    print("="*60)
    
    # Créer un ensemble de résultats de test
    retrieval_results = [
        {
            "query": "Qu'est-ce que Python?",
            "retrieved_doc_ids": ["python_doc1", "python_doc2", "python_doc3", "python_doc4"],
        },
        {
            "query": "Comment utiliser LangChain?",
            "retrieved_doc_ids": ["langchain_doc1", "langchain_doc2", "langchain_doc3"],
        },
        {
            "query": "Qu'est-ce que RAG?",
            "retrieved_doc_ids": ["rag_doc1", "rag_doc2", "rag_doc3", "rag_doc4", "rag_doc5"],
        }
    ]
    
    # Ground truth (documents réellement pertinents)
    ground_truth = {
        "Qu'est-ce que Python?": {"python_doc1", "python_doc2", "python_doc4"},
        "Comment utiliser LangChain?": {"langchain_doc1", "langchain_doc3"},
        "Qu'est-ce que RAG?": {"rag_doc1", "rag_doc2", "rag_doc3"},
    }
    
    # Calculer toutes les métriques
    metrics = calculate_retrieval_metrics(
        retrieval_results,
        ground_truth,
        k_values=[1, 3, 5]
    )
    
    print(f"Nombre de requêtes: {metrics['num_queries']}")
    print("\nPrecision@k:")
    for k, precision in metrics['precision_at_k'].items():
        print(f"  {k}: {precision:.3f}")
    
    print("\nRecall@k:")
    for k, recall in metrics['recall_at_k'].items():
        print(f"  {k}: {recall:.3f}")
    
    print(f"\nMean Average Precision (MAP): {metrics['mean_average_precision']:.3f}")
    
    print("✅ Test calcul complet réussi!")


def test_metrics_collector():
    """Test du collecteur de métriques."""
    print("\n" + "="*60)
    print("TEST 5: Collecteur de métriques")
    print("="*60)
    
    collector = get_retrieval_metrics_collector()
    
    # Enregistrer quelques résultats de test
    print("Enregistrement de résultats de retrieval...")
    collector.record_retrieval(
        conversation_id="test_conv_001",
        query="Test query 1",
        retrieved_doc_ids=["doc1", "doc2", "doc3"],
        retrieved_sources=["source1.pdf", "source2.pdf", "source3.pdf"]
    )
    
    collector.record_retrieval(
        conversation_id="test_conv_002",
        query="Test query 2",
        retrieved_doc_ids=["doc4", "doc5"],
        retrieved_sources=["source4.pdf", "source5.pdf"]
    )
    
    # Charger les résultats
    results = collector.load_retrieval_results(limit=10)
    print(f"\nNombre de résultats chargés: {len(results)}")
    
    if results:
        print("\nDernier résultat enregistré:")
        last_result = results[-1]
        print(f"  Conversation ID: {last_result.get('conversation_id')}")
        print(f"  Query: {last_result.get('query')}")
        print(f"  Documents récupérés: {len(last_result.get('retrieved_doc_ids', []))}")
        print(f"  Sources: {last_result.get('retrieved_sources', [])}")
    
    print("✅ Test collecteur réussi!")


def main():
    """Exécute tous les tests."""
    print("\n" + "="*60)
    print("TESTS DES METRIQUES DE RETRIEVAL")
    print("="*60)
    
    try:
        test_basic_precision_recall()
        test_average_precision()
        test_mean_average_precision()
        test_retrieval_metrics_full()
        test_metrics_collector()
        
        print("\n" + "="*60)
        print("✅ TOUS LES TESTS SONT PASSES AVEC SUCCES!")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n❌ ERREUR DE TEST: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERREUR INATTENDUE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

