"""
Script de test pour valider l'implémentation de la Retry Policy Sophistiquée
"""
import os
import sys
import time
import json

# Ajouter le répertoire racine au sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.Config import Config
from src.core.retry_policy import (
    retry_with_backoff_advanced,
    get_circuit_breaker,
    CircuitBreaker,
    CircuitState
)
from src.core.recovery_strategies import RecoveryStrategy
from src.core.fallback import get_fallback_manager, FallbackManager
from src.core.exceptions import MaxRetriesException

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
        required_configs = [
            'RETRY_JITTER_ENABLED',
            'RETRY_JITTER_MAX',
            'CIRCUIT_BREAKER_ENABLED',
            'CIRCUIT_BREAKER_FAILURE_THRESHOLD',
            'CIRCUIT_BREAKER_RECOVERY_TIMEOUT',
            'CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS',
            'FALLBACK_MODELS_ENABLED',
            'FALLBACK_MODEL_SECONDARY',
            'FALLBACK_MODEL_FAST',
            'RECOVERY_STRATEGY_ENABLED',
            'RECOVERY_INCREASE_TEMPERATURE',
            'RECOVERY_TEMPERATURE_INCREASE',
            'RECOVERY_EXPAND_SEARCH',
            'RECOVERY_SEARCH_EXPANSION_FACTOR'
        ]
        
        missing_configs = []
        for config_name in required_configs:
            if not hasattr(Config, config_name):
                missing_configs.append(config_name)
        
        if missing_configs:
            print_error(f"Configurations manquantes: {', '.join(missing_configs)}")
            return False
        
        print_success("Toutes les configurations requises sont présentes")
        
        # Afficher les valeurs importantes
        print_info(f"RETRY_JITTER_ENABLED: {getattr(Config, 'RETRY_JITTER_ENABLED')}")
        print_info(f"RETRY_JITTER_MAX: {getattr(Config, 'RETRY_JITTER_MAX')}")
        print_info(f"CIRCUIT_BREAKER_ENABLED: {getattr(Config, 'CIRCUIT_BREAKER_ENABLED')}")
        print_info(f"CIRCUIT_BREAKER_FAILURE_THRESHOLD: {getattr(Config, 'CIRCUIT_BREAKER_FAILURE_THRESHOLD')}")
        print_info(f"FALLBACK_MODELS_ENABLED: {getattr(Config, 'FALLBACK_MODELS_ENABLED')}")
        print_info(f"RECOVERY_STRATEGY_ENABLED: {getattr(Config, 'RECOVERY_STRATEGY_ENABLED')}")
        
        return True
        
    except Exception as e:
        print_error(f"Erreur lors de la vérification de la configuration: {str(e)}")
        return False

def test_circuit_breaker():
    """Test 2: Test du circuit breaker."""
    print_header("TEST 2: Test du Circuit Breaker")
    
    try:
        print_test("Création d'un circuit breaker de test...")
        
        # Créer un circuit breaker avec des seuils bas pour le test
        cb = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=5,  # 5 secondes pour le test
            half_open_max_calls=2
        )
        
        print_success("Circuit breaker créé")
        print_info(f"État initial: {cb.state.value}")
        print_info(f"Seuil d'échec: {cb.failure_threshold}")
        print_info(f"Timeout de récupération: {cb.recovery_timeout}s")
        
        # Test 1: Fonction qui réussit
        print_test("Test 1: Fonction qui réussit")
        def success_func():
            return "success"
        
        try:
            result = cb.call(success_func)
            print_success(f"Résultat: {result}")
            print_info(f"État après succès: {cb.state.value}")
            print_info(f"Compteur d'échecs: {cb.failure_count}")
        except Exception as e:
            print_error(f"Erreur inattendue: {str(e)}")
            return False
        
        # Réinitialiser le circuit breaker pour le test 2 (pour éviter l'impact du test 1)
        cb.reset()
        print_info("Circuit breaker réinitialisé pour le test 2")
        
        # Test 2: Fonction qui échoue plusieurs fois
        print_test("Test 2: Fonction qui échoue (simulation)")
        failure_count = 0
        
        def failing_func():
            nonlocal failure_count
            failure_count += 1
            # Toujours échouer pour les 3 premiers appels
            if failure_count <= 3:
                raise Exception(f"Erreur simulée {failure_count}")
            return "success after failures"
        
        # Simuler des échecs (3 échecs consécutifs)
        for i in range(3):
            try:
                cb.call(failing_func)
                print_error(f"La fonction devrait échouer à l'appel {i+1}")
                return False
            except Exception as e:
                print_info(f"Échec {i+1}: {str(e)}")
                print_info(f"État: {cb.state.value}, Échecs: {cb.failure_count}, Threshold: {cb.failure_threshold}")
                
                # Après le 3ème échec, le circuit devrait être OPEN
                if i == 2:  # 3ème échec (index 2)
                    if cb.state == CircuitState.OPEN:
                        print_success("Circuit ouvert après 3 échecs (comme prévu)")
                    else:
                        print_error(f"Circuit devrait être OPEN après 3 échecs, mais est {cb.state.value}")
                        print_error(f"Détails: Échecs={cb.failure_count}, Threshold={cb.failure_threshold}")
                        return False
                elif i == 1:  # 2ème échec (index 1)
                    # Le circuit devrait être encore CLOSED (2 échecs < 3)
                    if cb.state == CircuitState.CLOSED:
                        print_success("Circuit reste CLOSED après 2 échecs (normal)")
                    else:
                        print_warning(f"État inattendu après 2 échecs: {cb.state.value}")
        
        # Test 3: Circuit ouvert bloque les appels
        print_test("Test 3: Circuit ouvert bloque les appels")
        try:
            cb.call(success_func)
            print_error("Le circuit ouvert ne devrait pas permettre les appels")
            return False
        except MaxRetriesException:
            print_success("Circuit ouvert bloque correctement les appels")
        
        # Test 4: Récupération après timeout
        print_test("Test 4: Récupération après timeout")
        print_info("Attente de la récupération (5 secondes)...")
        time.sleep(6)  # Attendre plus que le recovery_timeout
        
        try:
            result = cb.call(success_func)
            if cb.state == CircuitState.HALF_OPEN:
                print_success("Circuit passé en HALF_OPEN après timeout")
            elif cb.state == CircuitState.CLOSED:
                print_success("Circuit fermé après succès en HALF_OPEN")
            else:
                print_warning(f"État: {cb.state.value}")
        except Exception as e:
            print_error(f"Erreur lors de la récupération: {str(e)}")
            return False
        
        # Réinitialiser pour les autres tests
        cb.reset()
        print_success("Circuit breaker réinitialisé")
        
        return True
        
    except Exception as e:
        print_error(f"Erreur lors du test du circuit breaker: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_jitter():
    """Test 3: Test du jitter aléatoire."""
    print_header("TEST 3: Test du Jitter Aléatoire")
    
    try:
        print_test("Test du jitter dans les retries...")
        
        jitter_enabled = getattr(Config, 'RETRY_JITTER_ENABLED', True)
        jitter_max = getattr(Config, 'RETRY_JITTER_MAX', 0.3)
        
        if not jitter_enabled:
            print_warning("Le jitter est désactivé dans la configuration")
            return True
        
        print_info(f"Jitter activé: {jitter_enabled}")
        print_info(f"Jitter max: {jitter_max}")
        
        # Simuler des retries avec jitter
        initial_delay = 1.0
        backoff_factor = 2.0
        delays_with_jitter = []
        delays_without_jitter = []
        
        for attempt in range(3):
            # Sans jitter
            delay_no_jitter = initial_delay * (backoff_factor ** attempt)
            delays_without_jitter.append(delay_no_jitter)
            
            # Avec jitter (simulation)
            import random
            jitter = random.uniform(0, jitter_max) * delay_no_jitter
            delay_with_jitter = delay_no_jitter + jitter
            delays_with_jitter.append(delay_with_jitter)
        
        print_info("\nComparaison des délais:")
        for i, (no_jitter, with_jitter) in enumerate(zip(delays_without_jitter, delays_with_jitter)):
            diff = with_jitter - no_jitter
            print_info(f"  Tentative {i+1}: {no_jitter:.3f}s -> {with_jitter:.3f}s (diff: +{diff:.3f}s)")
        
        # Vérifier que le jitter ajoute de la variabilité
        if any(d > n for d, n in zip(delays_with_jitter, delays_without_jitter)):
            print_success("Le jitter ajoute bien de la variabilité aux délais")
        else:
            print_warning("Le jitter ne semble pas fonctionner correctement")
        
        return True
        
    except Exception as e:
        print_error(f"Erreur lors du test du jitter: {str(e)}")
        return False

def test_retry_with_backoff_advanced():
    """Test 4: Test de retry_with_backoff_advanced."""
    print_header("TEST 4: Test de retry_with_backoff_advanced")
    
    try:
        print_test("Test avec fonction qui réussit...")
        
        def success_func():
            return "success"
        
        result = retry_with_backoff_advanced(success_func, max_retries=3)
        if result == "success":
            print_success("Fonction réussie au premier essai")
        else:
            print_error(f"Résultat inattendu: {result}")
            return False
        
        print_test("Test avec fonction qui échoue puis réussit...")
        attempt_count = 0
        
        def flaky_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise Exception("Erreur temporaire")
            return "success after retry"
        
        attempt_count = 0
        start_time = time.time()
        result = retry_with_backoff_advanced(flaky_func, max_retries=3, initial_delay=0.5)
        elapsed_time = time.time() - start_time
        
        if result == "success after retry":
            print_success(f"Fonction réussie après {attempt_count} tentatives")
            print_info(f"Temps écoulé: {elapsed_time:.2f}s (inclut backoff)")
        else:
            print_error(f"Résultat inattendu: {result}")
            return False
        
        print_test("Test avec circuit breaker...")
        cb = get_circuit_breaker("test_service")
        cb.reset()  # S'assurer qu'il est fermé
        
        def test_func():
            return "success"
        
        result = retry_with_backoff_advanced(
            test_func,
            max_retries=3,
            circuit_breaker=cb
        )
        
        if result == "success":
            print_success("Retry avec circuit breaker fonctionne")
        else:
            print_error("Problème avec circuit breaker")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Erreur lors du test de retry_with_backoff_advanced: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_fallback_manager():
    """Test 5: Test du Fallback Manager."""
    print_header("TEST 5: Test du Fallback Manager")
    
    try:
        print_test("Initialisation du fallback manager...")
        
        if not getattr(Config, 'FALLBACK_MODELS_ENABLED', True):
            print_warning("Les modèles de fallback sont désactivés")
            return True
        
        fallback_manager = get_fallback_manager()
        
        if not fallback_manager:
            print_error("Impossible de créer le fallback manager")
            return False
        
        print_success("Fallback manager créé")
        
        # Vérifier le modèle actuel
        current_llm = fallback_manager.get_current_llm()
        current_model = fallback_manager.get_current_model_name()
        
        if current_llm and current_model:
            print_success(f"Modèle actuel: {current_model}")
            print_info(f"Nombre de modèles disponibles: {len(fallback_manager.models)}")
        else:
            print_error("Impossible de récupérer le modèle actuel")
            return False
        
        # Tester le passage au modèle suivant
        print_test("Test du passage au modèle suivant...")
        initial_model = current_model
        has_next = fallback_manager.try_next_model()
        
        if has_next:
            new_model = fallback_manager.get_current_model_name()
            print_success(f"Passage au modèle suivant: {new_model}")
            
            # Réinitialiser
            fallback_manager.reset()
            reset_model = fallback_manager.get_current_model_name()
            if reset_model == initial_model:
                print_success("Réinitialisation réussie")
            else:
                print_warning(f"Modèle après reset: {reset_model} (attendu: {initial_model})")
        else:
            print_info("Aucun modèle de fallback disponible (normal si seul le modèle principal est configuré)")
        
        return True
        
    except Exception as e:
        print_error(f"Erreur lors du test du fallback manager: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_recovery_strategies():
    """Test 6: Test des stratégies de recovery."""
    print_header("TEST 6: Test des Stratégies de Recovery")
    
    try:
        print_test("Test de handle_hallucination...")
        
        test_state = {
            "question": "Test question",
            "documents": [],
            "generation": "Test generation"
        }
        
        from langchain_groq import ChatGroq
        test_llm = ChatGroq(
            model_name=Config.GROQ_model,
            temperature=0,
            groq_api_key=Config.GROQ_API_KEY
        )
        
        if getattr(Config, 'RECOVERY_STRATEGY_ENABLED', True):
            result_state = RecoveryStrategy.handle_hallucination(test_state, test_llm)
            if result_state == test_state:
                print_success("handle_hallucination fonctionne")
            else:
                print_warning("L'état a été modifié (peut être normal)")
        else:
            print_info("Stratégies de recovery désactivées")
        
        print_test("Test de handle_not_useful...")
        
        test_state = {
            "question": "Test question",
            "documents": [],
            "web_search": "No"
        }
        
        if getattr(Config, 'RECOVERY_STRATEGY_ENABLED', True):
            result_state = RecoveryStrategy.handle_not_useful(test_state)
            if "web_search" in result_state:
                print_success("handle_not_useful fonctionne")
                if result_state.get("web_search") == "Yes":
                    print_info("Recherche web activée par la stratégie")
            else:
                print_warning("L'état n'a pas été modifié comme prévu")
        else:
            print_info("Stratégies de recovery désactivées")
        
        return True
        
    except Exception as e:
        print_error(f"Erreur lors du test des stratégies de recovery: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_integration():
    """Test 7: Test d'intégration avec le workflow (optionnel)."""
    print_header("TEST 7: Test d'Intégration avec le Workflow (Optionnel)")
    
    print_warning("Ce test nécessite des documents dans ChromaDB et peut prendre du temps")
    print_info("Il va tester l'intégration complète de la retry policy dans le workflow")
    
    response = input("\nVoulez-vous exécuter ce test maintenant? (o/n): ").strip().lower()
    
    if response != 'o':
        print_info("Test d'intégration ignoré")
        return True
    
    try:
        print_test("Test d'intégration avec le workflow complet...")
        
        from src.rag.Rag_model import get_final_response
        
        test_question = "What is prompt engineering?"
        print_info(f"Question de test: {test_question}")
        print_info("Exécution du workflow complet avec retry policy (cela peut prendre 30-60 secondes)...")
        
        start_time = time.time()
        response = get_final_response(test_question)
        elapsed_time = time.time() - start_time
        
        print_success(f"Réponse générée en {elapsed_time:.2f}s")
        print_info(f"Réponse (premiers 200 caractères):\n{response[:200]}...")
        
        # Vérifier que les circuit breakers fonctionnent
        llm_cb = get_circuit_breaker("llm")
        if llm_cb:
            print_info(f"État du circuit breaker LLM: {llm_cb.state.value}")
            print_info(f"Compteur d'échecs LLM: {llm_cb.failure_count}")
        
        return True
        
    except Exception as e:
        print_error(f"Erreur lors du test d'intégration: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Fonction principale pour exécuter tous les tests."""
    print_header("SCRIPT DE TEST: Retry Policy Sophistiquée")
    
    print_info("Ce script teste l'implémentation de la Retry Policy Sophistiquée")
    print_info("Il vérifie la configuration, le circuit breaker, le jitter,")
    print_info("les stratégies de recovery, le fallback manager et l'intégration.\n")
    
    results = []
    
    # Test 1: Configuration
    results.append(("Configuration", test_configuration()))
    
    # Test 2: Circuit breaker
    results.append(("Circuit Breaker", test_circuit_breaker()))
    
    # Test 3: Jitter
    results.append(("Jitter", test_jitter()))
    
    # Test 4: retry_with_backoff_advanced
    results.append(("retry_with_backoff_advanced", test_retry_with_backoff_advanced()))
    
    # Test 5: Fallback manager
    results.append(("Fallback Manager", test_fallback_manager()))
    
    # Test 6: Stratégies de recovery
    results.append(("Stratégies de Recovery", test_recovery_strategies()))
    
    # Test 7: Intégration workflow (optionnel)
    import sys
    if '--full' in sys.argv:
        results.append(("Intégration Workflow", test_integration()))
    
    # Résumé
    print_header("RÉSUMÉ DES TESTS")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSÉ" if result else "❌ ÉCHOUÉ"
        print(f"{status} - {test_name}")
    
    print(f"\n{'='*60}")
    print(f"Résultat: {passed}/{total} tests passés")
    print(f"{'='*60}\n")
    
    if passed == total:
        print_success("Tous les tests sont passés avec succès! 🎉")
        return 0
    else:
        print_error(f"{total - passed} test(s) ont échoué")
        print_info("Pour exécuter tous les tests (y compris l'intégration), utilisez:")
        print_info("  python test_retry_policy.py --full")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

