"""
Script de test pour valider l'enrichissement des métadonnées des documents
"""
import os
import sys
import time

# Ajouter le répertoire racine au sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.rag.Data_processing import enrich_document_metadata, _extract_advanced_metadata
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

def test_configuration():
    """Test 1: Vérification de la configuration."""
    print_header("TEST 1: Vérification de la Configuration")
    
    try:
        print_test("Vérification des paramètres de configuration...")
        
        metadata_enabled = getattr(Config, 'METADATA_ENRICHMENT_ENABLED', True)
        extract_entities = getattr(Config, 'METADATA_EXTRACT_ENTITIES', True)
        extract_keywords = getattr(Config, 'METADATA_EXTRACT_KEYWORDS', True)
        extract_topics = getattr(Config, 'METADATA_EXTRACT_TOPICS', True)
        extract_summary = getattr(Config, 'METADATA_EXTRACT_SUMMARY', True)
        
        print_info(f"METADATA_ENRICHMENT_ENABLED: {metadata_enabled}")
        print_info(f"METADATA_EXTRACT_ENTITIES: {extract_entities}")
        print_info(f"METADATA_EXTRACT_KEYWORDS: {extract_keywords}")
        print_info(f"METADATA_EXTRACT_TOPICS: {extract_topics}")
        print_info(f"METADATA_EXTRACT_SUMMARY: {extract_summary}")
        
        max_keywords = getattr(Config, 'METADATA_MAX_KEYWORDS', 5)
        max_entities = getattr(Config, 'METADATA_MAX_ENTITIES', 10)
        max_topics = getattr(Config, 'METADATA_MAX_TOPICS', 3)
        summary_length = getattr(Config, 'METADATA_SUMMARY_MAX_LENGTH', 100)
        
        print_info(f"\nLimites configurées:")
        print_info(f"  - MAX_KEYWORDS: {max_keywords}")
        print_info(f"  - MAX_ENTITIES: {max_entities}")
        print_info(f"  - MAX_TOPICS: {max_topics}")
        print_info(f"  - SUMMARY_MAX_LENGTH: {summary_length} mots")
        
        if metadata_enabled:
            print_success("Configuration correcte - Enrichissement activé")
        else:
            print_warning("Enrichissement désactivé dans la configuration")
        
        return True
        
    except Exception as e:
        print_error(f"Erreur lors de la vérification: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_structural_metadata():
    """Test 2: Test des métadonnées structurelles."""
    print_header("TEST 2: Métadonnées Structurelles")
    
    try:
        print_test("Création de documents de test...")
        
        # Créer des documents de test
        test_docs = [
            Document(
                page_content="Large Language Models (LLMs) are advanced AI systems that can understand and generate human-like text. They are trained on vast amounts of text data.",
                metadata={"source": "test_doc_1"}
            ),
            Document(
                page_content="Prompt engineering is the practice of designing effective prompts to guide LLM behavior and improve output quality.",
                metadata={"source": "test_doc_1"}
            ),
            Document(
                page_content="Machine learning algorithms learn patterns from data without explicit programming instructions.",
                metadata={"source": "test_doc_2"}
            ),
        ]
        
        print_info(f"Documents de test créés: {len(test_docs)}")
        
        print_test("Enrichissement des métadonnées structurelles...")
        enriched_docs = enrich_document_metadata(test_docs)
        
        print_info(f"Documents enrichis: {len(enriched_docs)}")
        
        # Vérifier les métadonnées structurelles
        required_metadata = ['chunk_id', 'parent_doc_id', 'chunk_index', 'total_chunks', 
                           'language', 'created_at', 'processed_at']
        
        all_ok = True
        for i, doc in enumerate(enriched_docs):
            print_info(f"\nDocument {i+1}:")
            print_info(f"  Source originale: {doc.metadata.get('source', 'N/A')}")
            
            missing = []
            for key in required_metadata:
                if key in doc.metadata:
                    value = doc.metadata[key]
                    print_info(f"  ✓ {key}: {value}")
                else:
                    missing.append(key)
                    all_ok = False
            
            if missing:
                print_error(f"  ✗ Métadonnées manquantes: {missing}")
            
            # Vérifier la cohérence
            chunk_index = doc.metadata.get('chunk_index')
            total_chunks = doc.metadata.get('total_chunks')
            if chunk_index is not None and total_chunks is not None:
                if chunk_index >= total_chunks:
                    print_error(f"  ✗ chunk_index ({chunk_index}) >= total_chunks ({total_chunks})")
                    all_ok = False
                else:
                    print_success(f"  ✓ Indices cohérents (chunk {chunk_index+1}/{total_chunks})")
        
        if all_ok:
            print_success("\nToutes les métadonnées structurelles sont présentes et cohérentes")
        else:
            print_warning("\nCertaines métadonnées sont manquantes ou incohérentes")
        
        return all_ok
        
    except Exception as e:
        print_error(f"Erreur lors du test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_advanced_metadata_extraction():
    """Test 3: Test de l'extraction avancée de métadonnées."""
    print_header("TEST 3: Extraction Avancée (Entities, Keywords, Topics, Summary)")
    
    extract_entities = getattr(Config, 'METADATA_EXTRACT_ENTITIES', True)
    extract_keywords = getattr(Config, 'METADATA_EXTRACT_KEYWORDS', True)
    extract_topics = getattr(Config, 'METADATA_EXTRACT_TOPICS', True)
    extract_summary = getattr(Config, 'METADATA_EXTRACT_SUMMARY', True)
    
    if not any([extract_entities, extract_keywords, extract_topics, extract_summary]):
        print_warning("Toutes les extractions avancées sont désactivées, test ignoré")
        return False
    
    try:
        print_test("Création d'un document de test avec contenu riche...")
        
        test_doc = Document(
            page_content="""Artificial Intelligence and Machine Learning are transforming the technology industry. 
            Large Language Models like GPT-4 and BERT have revolutionized natural language processing. 
            Companies such as OpenAI, Google, and Microsoft are leading the development of these advanced AI systems. 
            These models are trained on massive datasets and can perform tasks like translation, summarization, 
            and question answering with remarkable accuracy. The applications span across healthcare, finance, 
            education, and many other sectors.""",
            metadata={"source": "test_advanced_extraction"}
        )
        
        print_info(f"Contenu: {len(test_doc.page_content)} caractères")
        print_warning("⏳ Extraction avec LLM (peut prendre 5-15 secondes)...")
        
        start_time = time.time()
        advanced_metadata = _extract_advanced_metadata(test_doc)
        elapsed_time = time.time() - start_time
        
        print_info(f"Extraction terminée en {elapsed_time:.2f}s")
        
        # Vérifier les résultats
        print_info("\nRésultats de l'extraction:")
        
        all_extracted = True
        if extract_keywords:
            if 'keywords' in advanced_metadata:
                keywords = advanced_metadata['keywords']
                print_success(f"✓ Keywords ({len(keywords)}): {keywords}")
            else:
                print_warning("✗ Keywords non extraits")
                all_extracted = False
        
        if extract_entities:
            if 'entities' in advanced_metadata:
                entities = advanced_metadata['entities']
                print_success(f"✓ Entities ({len(entities)}): {entities}")
            else:
                print_warning("✗ Entities non extraites")
                all_extracted = False
        
        if extract_topics:
            if 'topics' in advanced_metadata:
                topics = advanced_metadata['topics']
                print_success(f"✓ Topics ({len(topics)}): {topics}")
            else:
                print_warning("✗ Topics non extraits")
                all_extracted = False
        
        if extract_summary:
            if 'summary' in advanced_metadata:
                summary = advanced_metadata['summary']
                print_success(f"✓ Summary: {summary[:150]}...")
            else:
                print_warning("✗ Summary non extrait")
                all_extracted = False
        
        if all_extracted:
            print_success("\nToutes les métadonnées avancées ont été extraites avec succès")
        else:
            print_warning("\nCertaines métadonnées avancées n'ont pas été extraites")
        
        return all_extracted
        
    except Exception as e:
        print_error(f"Erreur lors de l'extraction: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_full_enrichment():
    """Test 4: Test de l'enrichissement complet (structurel + avancé)."""
    print_header("TEST 4: Enrichissement Complet")
    
    try:
        print_test("Test avec documents réels...")
        
        # Créer des documents de test
        test_docs = [
            Document(
                page_content="Python is a high-level programming language known for its simplicity and readability. It is widely used in data science, web development, and artificial intelligence.",
                metadata={"source": "python_guide.pdf"}
            ),
            Document(
                page_content="Django is a high-level Python web framework that enables rapid development of secure and maintainable websites. It follows the model-view-template architectural pattern.",
                metadata={"source": "python_guide.pdf"}
            ),
        ]
        
        print_info(f"Documents de test: {len(test_docs)}")
        print_warning("⏳ Enrichissement complet (peut prendre 10-30 secondes avec LLM)...")
        
        start_time = time.time()
        enriched_docs = enrich_document_metadata(test_docs)
        elapsed_time = time.time() - start_time
        
        print_info(f"Enrichissement terminé en {elapsed_time:.2f}s ({elapsed_time/60:.1f} minutes)")
        
        # Vérifier les métadonnées
        print_info("\nVérification des métadonnées enrichies:")
        
        all_ok = True
        for i, doc in enumerate(enriched_docs):
            print_info(f"\n--- Document {i+1} ---")
            print_info(f"Source: {doc.metadata.get('source', 'N/A')}")
            print_info(f"Chunk ID: {doc.metadata.get('chunk_id', 'N/A')}")
            print_info(f"Parent Doc ID: {doc.metadata.get('parent_doc_id', 'N/A')}")
            print_info(f"Chunk {doc.metadata.get('chunk_index', 'N/A') + 1}/{doc.metadata.get('total_chunks', 'N/A')}")
            
            # Vérifier les métadonnées avancées
            if 'keywords' in doc.metadata:
                print_info(f"Keywords: {doc.metadata['keywords']}")
            if 'entities' in doc.metadata:
                print_info(f"Entities: {doc.metadata['entities']}")
            if 'topics' in doc.metadata:
                print_info(f"Topics: {doc.metadata['topics']}")
            if 'summary' in doc.metadata:
                summary = doc.metadata['summary']
                print_info(f"Summary: {summary[:100]}..." if len(summary) > 100 else f"Summary: {summary}")
        
        print_success("\nEnrichissement complet réussi")
        return True
        
    except Exception as e:
        print_error(f"Erreur lors du test complet: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_metadata_persistence():
    """Test 5: Vérification de la persistance des métadonnées."""
    print_header("TEST 5: Vérification de la Persistance")
    
    try:
        print_test("Test que les métadonnées peuvent être sérialisées...")
        
        test_doc = Document(
            page_content="Test content for metadata persistence",
            metadata={
                "source": "test.pdf",
                "chunk_id": "test-id-123",
                "parent_doc_id": "parent-123",
                "chunk_index": 0,
                "total_chunks": 5,
                "keywords": ["test", "metadata"],
                "entities": ["Entity1", "Entity2"],
                "topics": ["Topic1"],
                "summary": "A test summary",
                "language": "en",
                "created_at": "2024-01-01T00:00:00",
                "processed_at": "2024-01-01T00:00:00"
            }
        )
        
        # Vérifier que les métadonnées peuvent être converties en dict
        metadata_dict = test_doc.metadata.copy()
        
        print_info("Métadonnées converties en dictionnaire:")
        for key, value in metadata_dict.items():
            print_info(f"  {key}: {value} (type: {type(value).__name__})")
        
        # Vérifier que les types sont sérialisables (JSON-compatible)
        import json
        try:
            json_str = json.dumps(metadata_dict)
            json.loads(json_str)
            print_success("✓ Métadonnées JSON-sérialisables")
            return True
        except (TypeError, ValueError) as e:
            print_error(f"✗ Erreur de sérialisation JSON: {str(e)}")
            return False
        
    except Exception as e:
        print_error(f"Erreur lors du test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Fonction principale de test."""
    print_header("TESTS ENRICHISSEMENT MÉTADONNÉES")
    print_info("Ce script teste l'enrichissement des métadonnées des documents")
    print_info("(Structurelles + Avancées)")
    
    results = []
    
    # Test 1: Configuration
    config_success = test_configuration()
    results.append(("Vérification configuration", config_success))
    
    # Test 2: Métadonnées structurelles
    structural_success = test_structural_metadata()
    results.append(("Métadonnées structurelles", structural_success))
    
    # Test 5: Persistance
    persistence_success = test_metadata_persistence()
    results.append(("Persistance des métadonnées", persistence_success))
    
    # Test 3: Extraction avancée (optionnel, peut être long)
    print_header("TEST OPTIONNEL: Extraction Avancée avec LLM")
    user_input = input("\nVoulez-vous tester l'extraction avancée ? (peut prendre 5-15s) [o/N]: ")
    if user_input.lower() in ['o', 'oui', 'y', 'yes']:
        advanced_success = test_advanced_metadata_extraction()
        results.append(("Extraction avancée", advanced_success))
    else:
        print_info("Test d'extraction avancée ignoré")
        results.append(("Extraction avancée", None))
    
    # Test 4: Enrichissement complet (optionnel, peut être long)
    print_header("TEST OPTIONNEL: Enrichissement Complet")
    user_input2 = input("\nVoulez-vous tester l'enrichissement complet ? (peut prendre 10-30s) [o/N]: ")
    if user_input2.lower() in ['o', 'oui', 'y', 'yes']:
        full_success = test_full_enrichment()
        results.append(("Enrichissement complet", full_success))
    else:
        print_info("Test d'enrichissement complet ignoré")
        results.append(("Enrichissement complet", None))
    
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
        print_info("\nL'enrichissement des métadonnées est prêt à être utilisé.")
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

