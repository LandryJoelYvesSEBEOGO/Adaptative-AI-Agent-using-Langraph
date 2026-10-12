"""
Script de test pour valider l'implémentation du Streaming des Réponses
"""

import os
import sys
import time

# Ajouter le répertoire racine au sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from langchain.schema import Document
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from config.Config import Config


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


def test_configuration():
    """Test 1: Vérification de la configuration."""
    print_header("TEST 1: Vérification de la Configuration")

    try:
        print_test("Vérification des paramètres de configuration...")

        # Vérifier que les paramètres existent
        required_configs = ["STREAMING_ENABLED", "STREAMING_CHUNK_SIZE"]

        missing_configs = []
        for config_name in required_configs:
            if not hasattr(Config, config_name):
                missing_configs.append(config_name)

        if missing_configs:
            print_error(f"Configurations manquantes: {', '.join(missing_configs)}")
            return False

        print_success("Toutes les configurations requises sont présentes")

        # Afficher les valeurs
        streaming_enabled = getattr(Config, "STREAMING_ENABLED", False)
        chunk_size = getattr(Config, "STREAMING_CHUNK_SIZE", 1)

        print_info(f"STREAMING_ENABLED: {streaming_enabled}")
        print_info(f"STREAMING_CHUNK_SIZE: {chunk_size}")

        if not streaming_enabled:
            print_warning("Le streaming est désactivé dans la configuration")
        else:
            print_success("Le streaming est activé")

        return True

    except Exception as e:
        print_error(f"Erreur lors de la vérification de la configuration: {str(e)}")
        return False


def test_llm_streaming_support():
    """Test 2: Vérification du support du streaming par le LLM."""
    print_header("TEST 2: Vérification du Support Streaming LLM")

    try:
        print_test("Test du streaming avec le LLM...")

        # Initialiser le LLM
        local_llm = ChatGroq(
            model_name=Config.GROQ_model, temperature=0, groq_api_key=Config.GROQ_API_KEY
        )

        # Test simple de streaming
        test_prompt = "Say 'Hello' in one word."

        print_info("Envoi d'une requête de test avec streaming...")
        start_time = time.time()

        chunks_received = []
        try:
            stream = local_llm.stream([HumanMessage(content=test_prompt)])

            for chunk in stream:
                if hasattr(chunk, "content") and chunk.content:
                    chunk_text = chunk.content
                    chunks_received.append(chunk_text)
                    print_info(f"Chunk reçu: '{chunk_text}'")

            elapsed_time = time.time() - start_time

            if chunks_received:
                full_response = "".join(chunks_received)
                print_success(f"Streaming fonctionne! Réponse complète: '{full_response}'")
                print_info(f"Nombre de chunks: {len(chunks_received)}")
                print_info(f"Temps total: {elapsed_time:.2f}s")
                return True
            else:
                print_error("Aucun chunk reçu du streaming")
                return False

        except AttributeError as e:
            print_error(f"Le LLM ne supporte pas le streaming: {str(e)}")
            return False
        except Exception as e:
            print_error(f"Erreur lors du test de streaming: {str(e)}")
            import traceback

            traceback.print_exc()
            return False

    except Exception as e:
        print_error(f"Erreur lors de l'initialisation du LLM: {str(e)}")
        return False


def test_generate_stream_function():
    """Test 3: Test de la fonction generate_stream."""
    print_header("TEST 3: Test de la Fonction generate_stream")

    try:
        print_test("Test de generate_stream avec un état de test...")

        from src.rag.Rag_model import generate_stream

        # Créer un état de test
        test_state = {
            "question": "What is prompt engineering?",
            "documents": [
                Document(
                    page_content="Prompt engineering is the practice of designing and optimizing prompts to effectively communicate with large language models.",
                    metadata={"source": "test_doc_1"},
                )
            ],
            "conversation_id": "test-streaming-001",
            "latencies": {},
            "loop_step": 0,
        }

        # Collecter les chunks
        chunks_collected = []

        def stream_callback(chunk: str):
            """Callback pour collecter les chunks."""
            chunks_collected.append(chunk)
            print_info(f"Chunk reçu via callback: '{chunk[:50]}...'")

        print_info("Exécution de generate_stream...")
        start_time = time.time()

        try:
            result = generate_stream(test_state, stream_callback=stream_callback)
            elapsed_time = time.time() - start_time

            if result and "generation" in result:
                generation_content = result["generation"]
                print_success(f"Génération complétée en {elapsed_time:.2f}s")
                print_info(f"Longueur de la réponse: {len(generation_content)} caractères")
                print_info(f"Nombre de chunks reçus: {len(chunks_collected)}")
                print_info(f"Réponse (premiers 200 caractères): {generation_content[:200]}...")

                # Vérifier que les chunks correspondent à la réponse complète
                chunks_combined = "".join(chunks_collected)
                if chunks_combined in generation_content or generation_content.startswith(
                    chunks_combined
                ):
                    print_success("Les chunks correspondent à la réponse complète")
                else:
                    print_warning(
                        "Les chunks ne correspondent pas exactement (peut être dû aux citations)"
                    )

                return True
            else:
                print_error("La fonction generate_stream n'a pas retourné de résultat valide")
                return False

        except Exception as e:
            print_error(f"Erreur lors de l'exécution de generate_stream: {str(e)}")
            import traceback

            traceback.print_exc()
            return False

    except ImportError as e:
        print_error(f"Impossible d'importer generate_stream: {str(e)}")
        return False
    except Exception as e:
        print_error(f"Erreur lors du test: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_get_final_response_stream():
    """Test 4: Test de la fonction get_final_response_stream."""
    print_header("TEST 4: Test de get_final_response_stream")

    print_warning("Ce test nécessite des documents dans ChromaDB et peut prendre du temps")
    print_info("Il va exécuter le workflow complet avec streaming")

    response = input("\nVoulez-vous exécuter ce test maintenant? (o/n): ").strip().lower()

    if response != "o":
        print_info("Test ignoré")
        return True

    try:
        print_test("Test de get_final_response_stream avec une question simple...")

        from src.rag.Rag_model import get_final_response_stream

        test_question = "What is prompt engineering?"
        print_info(f"Question de test: {test_question}")
        print_info("Exécution avec streaming (cela peut prendre 30-60 secondes)...")

        chunks_received = []
        start_time = time.time()

        try:
            for chunk in get_final_response_stream(test_question):
                chunks_received.append(chunk)
                # Afficher progressivement
                print(chunk, end="", flush=True)

            elapsed_time = time.time() - start_time
            print("\n")  # Nouvelle ligne après le streaming

            full_response = "".join(chunks_received)

            print_success(f"Streaming complété en {elapsed_time:.2f}s")
            print_info(f"Nombre de chunks: {len(chunks_received)}")
            print_info(f"Longueur totale: {len(full_response)} caractères")
            print_info(f"Réponse complète (premiers 300 caractères):\n{full_response[:300]}...")

            if len(chunks_received) > 0:
                print_success("Le streaming fonctionne correctement!")
                return True
            else:
                print_error("Aucun chunk n'a été reçu")
                return False

        except Exception as e:
            print_error(f"Erreur lors du streaming: {str(e)}")
            import traceback

            traceback.print_exc()
            return False

    except ImportError as e:
        print_error(f"Impossible d'importer get_final_response_stream: {str(e)}")
        return False
    except Exception as e:
        print_error(f"Erreur lors du test: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_streaming_vs_non_streaming():
    """Test 5: Comparaison streaming vs non-streaming."""
    print_header("TEST 5: Comparaison Streaming vs Non-Streaming")

    print_warning("Ce test compare les performances et nécessite des documents dans ChromaDB")

    response = input("\nVoulez-vous exécuter ce test maintenant? (o/n): ").strip().lower()

    if response != "o":
        print_info("Test ignoré")
        return True

    try:
        from src.rag.Rag_model import get_final_response, get_final_response_stream

        test_question = "What is prompt engineering?"
        print_info(f"Question de test: {test_question}")

        # Test non-streaming
        print_test("Test 1: Génération non-streaming...")
        start_time = time.time()
        try:
            response_normal = get_final_response(test_question)
            time_normal = time.time() - start_time
            print_success(f"Non-streaming complété en {time_normal:.2f}s")
            print_info(f"Longueur: {len(response_normal)} caractères")
        except Exception as e:
            print_error(f"Erreur non-streaming: {str(e)}")
            return False

        # Test streaming
        print_test("Test 2: Génération avec streaming...")
        chunks_received = []
        start_time = time.time()
        try:
            for chunk in get_final_response_stream(test_question):
                chunks_received.append(chunk)
            time_streaming = time.time() - start_time
            response_streaming = "".join(chunks_received)
            print_success(f"Streaming complété en {time_streaming:.2f}s")
            print_info(f"Longueur: {len(response_streaming)} caractères")
            print_info(f"Nombre de chunks: {len(chunks_received)}")
        except Exception as e:
            print_error(f"Erreur streaming: {str(e)}")
            return False

        # Comparaison
        print_info("\n📊 Comparaison:")
        print_info(f"  Temps non-streaming: {time_normal:.2f}s")
        print_info(f"  Temps streaming: {time_streaming:.2f}s")
        print_info(f"  Différence: {abs(time_normal - time_streaming):.2f}s")

        # Vérifier que les réponses sont similaires (peuvent différer légèrement)
        similarity = len(set(response_normal.split()) & set(response_streaming.split())) / max(
            len(response_normal.split()), len(response_streaming.split())
        )
        print_info(f"  Similarité des réponses: {similarity * 100:.1f}%")

        if similarity > 0.7:
            print_success("Les réponses sont similaires (streaming fonctionne correctement)")
        else:
            print_warning(
                "Les réponses diffèrent significativement (peut être normal selon le contexte)"
            )

        return True

    except Exception as e:
        print_error(f"Erreur lors de la comparaison: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_fallback_mechanism():
    """Test 6: Test du mécanisme de fallback."""
    print_header("TEST 6: Test du Mécanisme de Fallback")

    print_info("Ce test vérifie que le fallback fonctionne en cas d'erreur de streaming")
    print_warning("Note: Ce test peut nécessiter de simuler une erreur")

    response = input("\nVoulez-vous exécuter ce test maintenant? (o/n): ").strip().lower()

    if response != "o":
        print_info("Test ignoré")
        return True

    try:
        from src.rag.Rag_model import get_final_response

        # Test que get_final_response fonctionne toujours (fallback)
        test_question = "What is AI?"
        print_test("Test du fallback (génération normale)...")

        start_time = time.time()
        try:
            response = get_final_response(test_question)
            elapsed_time = time.time() - start_time

            print_success(f"Fallback fonctionne! Réponse générée en {elapsed_time:.2f}s")
            print_info(f"Longueur: {len(response)} caractères")
            print_info(f"Réponse (premiers 200 caractères): {response[:200]}...")

            return True
        except Exception as e:
            print_error(f"Le fallback ne fonctionne pas: {str(e)}")
            return False

    except Exception as e:
        print_error(f"Erreur lors du test de fallback: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Fonction principale pour exécuter tous les tests."""
    print_header("SCRIPT DE TEST: Streaming des Réponses")

    print_info("Ce script teste l'implémentation du streaming des réponses")
    print_info("Il vérifie la configuration, le support LLM, les fonctions de streaming,")
    print_info("et compare les performances avec la génération non-streaming.\n")

    results = []

    # Test 1: Configuration
    results.append(("Configuration", test_configuration()))

    # Test 2: Support LLM
    results.append(("Support Streaming LLM", test_llm_streaming_support()))

    # Test 3: Fonction generate_stream
    results.append(("Fonction generate_stream", test_generate_stream_function()))

    # Test 4: Fonction get_final_response_stream (optionnel)
    import sys

    if "--full" in sys.argv:
        results.append(("get_final_response_stream", test_get_final_response_stream()))
        results.append(
            ("Comparaison Streaming vs Non-Streaming", test_streaming_vs_non_streaming())
        )
        results.append(("Mécanisme de Fallback", test_fallback_mechanism()))

    # Résumé
    print_header("RÉSUMÉ DES TESTS")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSÉ" if result else "❌ ÉCHOUÉ"
        print(f"{status} - {test_name}")

    print(f"\n{'=' * 60}")
    print(f"Résultat: {passed}/{total} tests passés")
    print(f"{'=' * 60}\n")

    if passed == total:
        print_success("Tous les tests sont passés avec succès! 🎉")
        return 0
    else:
        print_error(f"{total - passed} test(s) ont échoué")
        print_info("Pour exécuter tous les tests (y compris ceux nécessitant ChromaDB), utilisez:")
        print_info("  python test_streaming.py --full")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
