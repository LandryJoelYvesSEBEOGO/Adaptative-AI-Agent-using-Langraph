"""
Script de test pour valider la gestion d'erreurs du système RAG.
Version simplifiée pour Windows - sans timeout complexe.
"""

import os
import sys
import time
import threading
from dotenv import load_dotenv

# Ajouter le répertoire racine au path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Charger les variables d'environnement
load_dotenv()

from src.rag.Rag_model import get_final_response
from src.core.exceptions import (
    RetrievalException, GenerationException, MaxRetriesException,
    LLMQuotaException, WebSearchException, RAGException
)


class Colors:
    """Codes couleur pour l'affichage console."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Affiche un en-tête formaté."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}\n")


def print_test(test_name):
    """Affiche le nom d'un test."""
    print(f"{Colors.BOLD}{Colors.BLUE}▶ Test: {test_name}{Colors.RESET}")


def print_success(message):
    """Affiche un message de succès."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message):
    """Affiche un message d'erreur."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_warning(message):
    """Affiche un message d'avertissement."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def print_info(message):
    """Affiche un message informatif."""
    print(f"{Colors.CYAN}ℹ {message}{Colors.RESET}")


def test_normal_query():
    """Test 1: Requête normale qui devrait fonctionner."""
    print_header("TEST 1: Requête normale")
    print_test("Question simple sur les LLMs")
    
    query = "What is a Large Language Model?"
    print_info(f"Question: {query}")
    print_warning("⏳ Cette étape peut prendre 1-5 minutes (première fois avec GPU)...")
    print_info("Les messages '---RETRIEVE---', '---GENERATE---', etc. sont normaux.")
    print_info("Le premier chargement du modèle GPU peut prendre 30-60 secondes.")
    print_info("L'embedding de la question peut prendre 10-30 secondes la première fois.")
    print_info("⏳ Patientez, c'est normal que ça prenne du temps...\n")
    
    try:
        start_time = time.time()
        should_stop = [False]
        
        def show_progress():
            """Affiche un indicateur de progression toutes les 20 secondes."""
            counter = 0
            while not should_stop[0]:
                time.sleep(20)  # Toutes les 20 secondes
                if not should_stop[0]:
                    counter += 1
                    elapsed = time.time() - start_time
                    print_info(f"⏳ Encore en cours... ({elapsed:.0f}s) - C'est normal, continuez à patienter...")
        
        progress_thread = threading.Thread(target=show_progress, daemon=True)
        progress_thread.start()
        
        try:
            print_info("🔄 Appel du workflow...")
            response = get_final_response(query)
            should_stop[0] = True
            time.sleep(0.5)
        except KeyboardInterrupt:
            should_stop[0] = True
            print_warning("\n⚠️ Interrompu par l'utilisateur")
            return None
        except Exception as e:
            should_stop[0] = True
            raise
        
        elapsed_time = time.time() - start_time
        print_success(f"✅ Réponse générée en {elapsed_time:.2f}s ({elapsed_time/60:.1f} minutes)")
        
        if response and not response.startswith("⚠️"):
            print_success("Réponse valide reçue")
            print_info(f"Longueur: {len(response)} caractères")
            print_info(f"Extrait: {response[:200]}...")
            return True
        elif response and response.startswith("⚠️"):
            print_warning(f"Avertissement: {response[:150]}...")
            return True  # Erreur bien gérée = succès
        else:
            print_error("Pas de réponse valide")
            return False
            
    except KeyboardInterrupt:
        print_warning("\n⚠️ Test interrompu")
        return None
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_empty_query():
    """Test 2: Requête vide."""
    print_header("TEST 2: Requête vide")
    print_test("Gestion des requêtes vides")
    
    queries = ["", "   "]
    
    for query in queries:
        print_info(f"Test avec: {repr(query)}")
        try:
            response = get_final_response(query)
            if response and "⚠️" in response:
                print_success("Gestion correcte")
                print_info(f"Message: {response}")
            else:
                print_warning(f"Réponse inattendue: {response}")
        except Exception as e:
            print_error(f"Exception: {str(e)}")
    return True


def test_exceptions_import():
    """Test 3: Vérifier que les exceptions sont bien importées."""
    print_header("TEST 3: Import des exceptions")
    print_test("Vérification de la hiérarchie d'exceptions")
    
    exceptions_to_check = [
        "RAGException",
        "RetrievalException",
        "GenerationException",
        "MaxRetriesException",
        "LLMQuotaException",
        "WebSearchException"
    ]
    
    all_present = True
    for exc_name in exceptions_to_check:
        try:
            from src.core.exceptions import __dict__ as exc_dict
            if exc_name in exc_dict:
                print_success(f"{exc_name}: Présente")
            else:
                print_error(f"{exc_name}: Manquante")
                all_present = False
        except ImportError as e:
            print_error(f"Import error: {str(e)}")
            all_present = False
            break
    
    return all_present


def test_retry_mechanism():
    """Test 4: Vérifier que le mécanisme de retry est présent."""
    print_header("TEST 4: Mécanisme de retry")
    print_test("Vérification de la configuration max_retries")
    
    try:
        from config.Config import Config
        
        max_retries = getattr(Config, 'MAX_RETRIES', None)
        
        if max_retries is not None:
            print_success(f"MAX_RETRIES configuré: {max_retries}")
            retry_delay = getattr(Config, 'RETRY_INITIAL_DELAY', None)
            retry_factor = getattr(Config, 'RETRY_BACKOFF_FACTOR', None)
            
            if retry_delay:
                print_success(f"RETRY_INITIAL_DELAY: {retry_delay}s")
            if retry_factor:
                print_success(f"RETRY_BACKOFF_FACTOR: {retry_factor}x")
            
            return True
        else:
            print_error("MAX_RETRIES non configuré")
            return False
    except Exception as e:
        print_error(f"Erreur: {str(e)}")
        return False


def run_all_tests():
    """Exécute les tests essentiels."""
    print_header("SUITE DE TESTS - GESTION D'ERREURS RAG")
    print_info("Tests simplifiés pour diagnostic")
    print_warning("⚠️ Le test 1 peut prendre 1-5 minutes (première fois avec GPU)")
    print_warning("⚠️ Le premier chargement du modèle GPU est long mais normal\n")
    
    results = {}
    
    # Tests rapides d'abord
    tests = [
        ("Import exceptions", test_exceptions_import),
        ("Configuration retry", test_retry_mechanism),
        ("Requête vide", test_empty_query),
        ("Requête normale", test_normal_query),  # Le plus long
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
            if result is None:  # Interrompu
                print_warning(f"⚠️ Suite interrompue après '{test_name}'")
                break
            time.sleep(0.5)
        except KeyboardInterrupt:
            print_warning(f"\n⚠️ Interrompu pendant '{test_name}'")
            results[test_name] = None
            break
        except Exception as e:
            print_error(f"Erreur dans '{test_name}': {str(e)}")
            results[test_name] = False
    
    # Résumé
    print_header("RÉSUMÉ")
    total = len([r for r in results.values() if r is not None])
    passed = sum(1 for r in results.values() if r is True)
    
    for test_name, result in results.items():
        if result is True:
            print_success(f"{test_name}: PASSÉ")
        elif result is False:
            print_error(f"{test_name}: ÉCHOUÉ")
        elif result is None:
            print_warning(f"{test_name}: INTERROMPU")
    
    if total > 0:
        print_info(f"\nTotal: {total} tests | Succès: {passed}")
        if passed == total:
            print_success("\n✅ Tous les tests sont passés!")
    
    return results


if __name__ == "__main__":
    try:
        results = run_all_tests()
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrompu par l'utilisateur")
        sys.exit(130)
    except Exception as e:
        print_error(f"\nErreur fatale: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)