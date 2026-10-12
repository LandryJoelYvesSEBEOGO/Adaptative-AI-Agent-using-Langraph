"""
Script de test pour valider l'implémentation de l'Answer Quality Scoring
"""

import json
import os
import sys
import time

# Ajouter le répertoire racine au sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from config.Config import Config
from src.rag.Prompts import get_prompts


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
        required_configs = [
            "ANSWER_QUALITY_SCORING_ENABLED",
            "ANSWER_QUALITY_RELEVANCE_WEIGHT",
            "ANSWER_QUALITY_COMPLETENESS_WEIGHT",
            "ANSWER_QUALITY_CONCISENESS_WEIGHT",
            "ANSWER_QUALITY_ACCURACY_WEIGHT",
            "ANSWER_QUALITY_COHERENCE_WEIGHT",
            "ANSWER_QUALITY_ACCEPTANCE_THRESHOLD",
            "ANSWER_QUALITY_ADAPTIVE_THRESHOLD",
        ]

        missing_configs = []
        for config_name in required_configs:
            if not hasattr(Config, config_name):
                missing_configs.append(config_name)

        if missing_configs:
            print_error(f"Configurations manquantes: {', '.join(missing_configs)}")
            return False

        print_success("Toutes les configurations requises sont présentes")

        # Afficher les valeurs
        print_info(f"ANSWER_QUALITY_SCORING_ENABLED: {Config.ANSWER_QUALITY_SCORING_ENABLED}")
        print_info(f"ANSWER_QUALITY_RELEVANCE_WEIGHT: {Config.ANSWER_QUALITY_RELEVANCE_WEIGHT}")
        print_info(
            f"ANSWER_QUALITY_COMPLETENESS_WEIGHT: {Config.ANSWER_QUALITY_COMPLETENESS_WEIGHT}"
        )
        print_info(f"ANSWER_QUALITY_CONCISENESS_WEIGHT: {Config.ANSWER_QUALITY_CONCISENESS_WEIGHT}")
        print_info(f"ANSWER_QUALITY_ACCURACY_WEIGHT: {Config.ANSWER_QUALITY_ACCURACY_WEIGHT}")
        print_info(f"ANSWER_QUALITY_COHERENCE_WEIGHT: {Config.ANSWER_QUALITY_COHERENCE_WEIGHT}")
        print_info(
            f"ANSWER_QUALITY_ACCEPTANCE_THRESHOLD: {Config.ANSWER_QUALITY_ACCEPTANCE_THRESHOLD}"
        )
        print_info(f"ANSWER_QUALITY_ADAPTIVE_THRESHOLD: {Config.ANSWER_QUALITY_ADAPTIVE_THRESHOLD}")

        # Vérifier que les poids somment à 1.0
        total_weight = (
            getattr(Config, "ANSWER_QUALITY_RELEVANCE_WEIGHT", 0)
            + getattr(Config, "ANSWER_QUALITY_COMPLETENESS_WEIGHT", 0)
            + getattr(Config, "ANSWER_QUALITY_CONCISENESS_WEIGHT", 0)
            + getattr(Config, "ANSWER_QUALITY_ACCURACY_WEIGHT", 0)
            + getattr(Config, "ANSWER_QUALITY_COHERENCE_WEIGHT", 0)
        )

        if abs(total_weight - 1.0) > 0.01:
            print_warning(f"Les poids ne somment pas à 1.0 (somme: {total_weight:.3f})")
        else:
            print_success(f"Les poids somment correctement à {total_weight:.3f}")

        return True

    except Exception as e:
        print_error(f"Erreur lors de la vérification de la configuration: {str(e)}")
        return False


def test_prompts():
    """Test 2: Vérification des prompts."""
    print_header("TEST 2: Vérification des Prompts")

    try:
        print_test("Chargement des prompts...")
        prompts = get_prompts()

        # Vérifier que les prompts existent
        required_prompts = ["answer_quality_scorer_instructions", "answer_quality_scorer_prompt"]

        missing_prompts = []
        for prompt_name in required_prompts:
            if prompt_name not in prompts:
                missing_prompts.append(prompt_name)

        if missing_prompts:
            print_error(f"Prompts manquants: {', '.join(missing_prompts)}")
            return False

        print_success("Tous les prompts requis sont présents")

        # Vérifier le contenu des prompts
        instructions = prompts["answer_quality_scorer_instructions"]
        prompt_template = prompts["answer_quality_scorer_prompt"]

        print_info(f"Longueur des instructions: {len(instructions)} caractères")
        print_info(f"Longueur du prompt template: {len(prompt_template)} caractères")

        # Vérifier que les placeholders sont présents
        required_placeholders = ["{question}", "{answer}", "{context}"]
        missing_placeholders = []
        for placeholder in required_placeholders:
            if placeholder not in prompt_template:
                missing_placeholders.append(placeholder)

        if missing_placeholders:
            print_error(f"Placeholders manquants dans le prompt: {', '.join(missing_placeholders)}")
            return False

        print_success("Tous les placeholders requis sont présents")

        # Vérifier que les critères sont mentionnés
        criteria = ["RELEVANCE", "COMPLETENESS", "CONCISENESS", "ACCURACY", "COHERENCE"]
        mentioned_criteria = []
        for criterion in criteria:
            if criterion in instructions.upper():
                mentioned_criteria.append(criterion)

        if len(mentioned_criteria) < len(criteria):
            print_warning("Certains critères ne sont pas mentionnés dans les instructions")
            print_info(f"Critères trouvés: {', '.join(mentioned_criteria)}")
        else:
            print_success("Tous les critères sont mentionnés dans les instructions")

        return True

    except Exception as e:
        print_error(f"Erreur lors de la vérification des prompts: {str(e)}")
        return False


def test_scoring_logic():
    """Test 3: Test de la logique de scoring avec un exemple."""
    print_header("TEST 3: Test de la Logique de Scoring")

    try:
        print_test("Test du scoring avec un exemple de réponse...")

        # Initialiser le LLM
        llm_json_mode = ChatGroq(
            model_name=Config.GROQ_model,
            temperature=0,
            model_kwargs={"response_format": {"type": "json_object"}},
            groq_api_key=Config.GROQ_API_KEY,
        )

        prompts = get_prompts()

        # Exemple de test
        test_question = "What is prompt engineering?"
        test_answer = "Prompt engineering is the practice of designing and optimizing prompts to effectively communicate with large language models. It involves crafting clear, specific instructions that guide the model to produce desired outputs."
        test_context = "Prompt engineering is a technique used to improve the performance of AI models by carefully crafting input prompts."

        # Formater le prompt
        quality_prompt_formatted = prompts["answer_quality_scorer_prompt"].format(
            question=test_question, answer=test_answer, context=test_context
        )

        print_info("Envoi de la requête au LLM...")
        start_time = time.time()

        result = llm_json_mode.invoke(
            [SystemMessage(content=prompts["answer_quality_scorer_instructions"])]
            + [HumanMessage(content=quality_prompt_formatted)]
        )

        elapsed_time = time.time() - start_time
        print_info(f"Réponse reçue en {elapsed_time:.2f}s")

        # Parser la réponse JSON
        try:
            quality_data = json.loads(result.content)
            print_success("Réponse JSON parsée avec succès")
        except json.JSONDecodeError as e:
            print_error(f"Erreur de parsing JSON: {str(e)}")
            print_info(f"Réponse brute: {result.content[:200]}")
            return False

        # Vérifier la structure
        required_keys = ["scores", "overall_score", "accepted", "reasoning"]
        missing_keys = []
        for key in required_keys:
            if key not in quality_data:
                missing_keys.append(key)

        if missing_keys:
            print_error(f"Clés manquantes dans la réponse: {', '.join(missing_keys)}")
            return False

        print_success("Structure JSON correcte")

        # Vérifier les scores
        scores = quality_data.get("scores", {})
        required_score_keys = ["relevance", "completeness", "conciseness", "accuracy", "coherence"]
        missing_score_keys = []
        for key in required_score_keys:
            if key not in scores:
                missing_score_keys.append(key)

        if missing_score_keys:
            print_error(f"Clés de scores manquantes: {', '.join(missing_score_keys)}")
            return False

        print_success("Tous les scores sont présents")

        # Afficher les scores
        print_info("\n📊 Scores obtenus:")
        for key in required_score_keys:
            score_value = scores.get(key, 0.0)
            print_info(f"  {key.capitalize()}: {score_value:.2f}")

        overall_score = quality_data.get("overall_score", 0.0)
        accepted = quality_data.get("accepted", False)
        reasoning = quality_data.get("reasoning", "No reasoning provided")

        print_info(f"\nScore global: {overall_score:.2f}")
        print_info(f"Accepté: {accepted}")
        print_info(f"Raisonnement: {reasoning[:100]}...")

        # Vérifier que les scores sont dans la plage [0, 1]
        invalid_scores = []
        for key, value in scores.items():
            if not (0.0 <= float(value) <= 1.0):
                invalid_scores.append(f"{key}={value}")

        if invalid_scores:
            print_error(f"Scores hors plage [0, 1]: {', '.join(invalid_scores)}")
            return False

        print_success("Tous les scores sont dans la plage [0, 1]")

        # Calculer le score pondéré manuellement pour vérification
        relevance_weight = getattr(Config, "ANSWER_QUALITY_RELEVANCE_WEIGHT", 0.30)
        completeness_weight = getattr(Config, "ANSWER_QUALITY_COMPLETENESS_WEIGHT", 0.25)
        conciseness_weight = getattr(Config, "ANSWER_QUALITY_CONCISENESS_WEIGHT", 0.15)
        accuracy_weight = getattr(Config, "ANSWER_QUALITY_ACCURACY_WEIGHT", 0.20)
        coherence_weight = getattr(Config, "ANSWER_QUALITY_COHERENCE_WEIGHT", 0.10)

        calculated_score = (
            float(scores.get("relevance", 0.0)) * relevance_weight
            + float(scores.get("completeness", 0.0)) * completeness_weight
            + float(scores.get("conciseness", 0.0)) * conciseness_weight
            + float(scores.get("accuracy", 0.0)) * accuracy_weight
            + float(scores.get("coherence", 0.0)) * coherence_weight
        )

        threshold = getattr(Config, "ANSWER_QUALITY_ACCEPTANCE_THRESHOLD", 0.65)
        calculated_accepted = calculated_score >= threshold

        print_info(f"\nScore calculé manuellement: {calculated_score:.3f}")
        print_info(f"Score du LLM: {overall_score:.3f}")
        print_info(f"Différence: {abs(calculated_score - overall_score):.3f}")

        if abs(calculated_score - overall_score) > 0.05:
            print_warning("Le score calculé diffère significativement du score du LLM")
        else:
            print_success("Le score calculé correspond au score du LLM")

        return True

    except Exception as e:
        print_error(f"Erreur lors du test de scoring: {str(e)}")
        import traceback

        traceback.print_exc()
        return False



def test_workflow_integration():
    """Test 5: Test d'intégration avec le workflow (optionnel, nécessite des documents)."""
    print_header("TEST 5: Test d'Intégration avec le Workflow (Optionnel)")

    print_warning("Ce test nécessite des documents dans ChromaDB et peut prendre du temps")
    print_info("Pour exécuter ce test, utilisez: python test_answer_quality_scoring.py --full")

    response = input("\nVoulez-vous exécuter ce test maintenant? (o/n): ").strip().lower()

    if response != "o":
        print_info("Test d'intégration ignoré")
        return True

    try:
        print_test("Test d'intégration avec le workflow complet...")

        from src.rag.Rag_model import get_final_response

        test_question = "What is prompt engineering?"
        print_info(f"Question de test: {test_question}")
        print_info("Exécution du workflow complet (cela peut prendre 30-60 secondes)...")

        start_time = time.time()
        response = get_final_response(test_question)
        elapsed_time = time.time() - start_time

        print_success(f"Réponse générée en {elapsed_time:.2f}s")
        print_info(f"\nRéponse:\n{response[:200]}...")

        return True

    except Exception as e:
        print_error(f"Erreur lors du test d'intégration: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Fonction principale pour exécuter tous les tests."""
    print_header("SCRIPT DE TEST: Answer Quality Scoring")

    print_info("Ce script teste l'implémentation de l'Answer Quality Scoring")
    print_info("Il vérifie la configuration, les prompts, la logique de scoring,")
    print_info("l'intégration avec les métriques et le workflow complet.\n")

    results = []

    # Test 1: Configuration
    results.append(("Configuration", test_configuration()))

    # Test 2: Prompts
    results.append(("Prompts", test_prompts()))

    # Test 3: Logique de scoring
    results.append(("Logique de Scoring", test_scoring_logic()))

    # Test 4: Intégration métriques

    # Test 5: Intégration workflow (optionnel)
    import sys

    if "--full" in sys.argv:
        results.append(("Intégration Workflow", test_workflow_integration()))

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
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
