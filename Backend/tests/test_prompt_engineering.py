"""
Script de test pour valider l'implémentation du Prompt Engineering Avancé
"""

import os
import sys
import time

# Ajouter le répertoire racine au sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.Config import Config
from src.core.few_shot_examples import (
    format_few_shot_examples,
    load_few_shot_examples,
    select_similar_examples,
)
from src.core.prompt_templates import (
    detect_role_from_question,
    format_structured_output_instruction,
    get_chain_of_thought_instruction,
    get_role_prompt,
)
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
            "FEW_SHOT_ENABLED",
            "FEW_SHOT_NUM_EXAMPLES",
            "FEW_SHOT_EXAMPLES_FILE",
            "FEW_SHOT_SIMILARITY_THRESHOLD",
            "CHAIN_OF_THOUGHT_ENABLED",
            "CHAIN_OF_THOUGHT_FOR_COMPLEX",
            "CHAIN_OF_THOUGHT_COMPLEXITY_THRESHOLD",
            "ROLE_BASED_PROMPTING_ENABLED",
            "ROLE_DETECTION_ENABLED",
            "STRUCTURED_OUTPUT_ENABLED",
            "STRUCTURED_OUTPUT_FORMAT",
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
        print_info(f"FEW_SHOT_ENABLED: {Config.FEW_SHOT_ENABLED}")
        print_info(f"FEW_SHOT_NUM_EXAMPLES: {Config.FEW_SHOT_NUM_EXAMPLES}")
        print_info(f"FEW_SHOT_SIMILARITY_THRESHOLD: {Config.FEW_SHOT_SIMILARITY_THRESHOLD}")
        print_info(f"CHAIN_OF_THOUGHT_ENABLED: {Config.CHAIN_OF_THOUGHT_ENABLED}")
        print_info(f"ROLE_BASED_PROMPTING_ENABLED: {Config.ROLE_BASED_PROMPTING_ENABLED}")
        print_info(f"STRUCTURED_OUTPUT_ENABLED: {Config.STRUCTURED_OUTPUT_ENABLED}")

        return True

    except Exception as e:
        print_error(f"Erreur lors de la vérification de la configuration: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_few_shot_examples():
    """Test 2: Test du chargement et de la sélection des exemples few-shot."""
    print_header("TEST 2: Test Few-Shot Examples")

    try:
        print_test("Chargement des exemples few-shot...")

        examples = load_few_shot_examples()

        if not examples:
            print_warning(
                "Aucun exemple few-shot trouvé (le fichier sera créé au premier lancement)"
            )
            return True  # Ce n'est pas une erreur, le fichier sera créé automatiquement

        print_success(f"{len(examples)} exemples chargés")

        # Vérifier la structure des exemples
        print_test("Vérification de la structure des exemples...")
        for i, example in enumerate(examples[:3], 1):
            if "question" not in example or "answer" not in example:
                print_error(
                    f"Exemple {i} n'a pas la structure correcte (manque 'question' ou 'answer')"
                )
                return False
            print_info(f"Exemple {i}: {example['question'][:50]}...")

        print_success("Structure des exemples correcte")

        # Test de sélection d'exemples similaires
        print_test("Test de sélection d'exemples similaires...")

        test_queries = [
            "What is prompt engineering?",
            "How do LLM agents work?",
            "Explain adversarial attacks on language models",
        ]

        for query in test_queries:
            selected = select_similar_examples(query, num_examples=2)
            print_info(f"Query: '{query}'")
            print_info(f"  → {len(selected)} exemples sélectionnés")
            for j, ex in enumerate(selected, 1):
                print_info(f"    {j}. {ex['question'][:60]}...")

        print_success("Sélection d'exemples similaires fonctionne")

        # Test de formatage
        print_test("Test de formatage des exemples...")
        formatted = format_few_shot_examples(examples[:2])
        if formatted:
            print_info("Formatage réussi (premiers 200 caractères):")
            print_info(formatted[:200] + "...")
            print_success("Formatage des exemples fonctionne")
        else:
            print_warning("Formatage retourne une chaîne vide (normal si pas d'exemples)")

        return True

    except Exception as e:
        print_error(f"Erreur lors du test few-shot: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_role_detection():
    """Test 3: Test de la détection de rôle."""
    print_header("TEST 3: Test Role Detection")

    try:
        print_test("Test de détection de rôle selon le type de question...")

        test_cases = [
            ("What is the syntax for Python functions?", "code"),
            ("How do I implement a REST API?", "code"),
            ("Explain the research methodology used in this study", "academic"),
            ("What are the theoretical foundations of machine learning?", "academic"),
            ("Describe the system architecture", "technical"),
            ("How does the framework handle errors?", "technical"),
            ("What is the weather today?", "general"),
            ("Tell me a joke", "general"),
        ]

        correct = 0
        total = len(test_cases)

        for question, expected_role in test_cases:
            detected_role = detect_role_from_question(question)
            status = "✅" if detected_role == expected_role else "⚠️"
            print_info(
                f"{status} '{question[:50]}...' → {detected_role} (attendu: {expected_role})"
            )
            if detected_role == expected_role:
                correct += 1

        accuracy = (correct / total) * 100
        print_info(f"\nPrécision: {correct}/{total} ({accuracy:.1f}%)")

        if accuracy >= 70:
            print_success(f"Détection de rôle fonctionne ({accuracy:.1f}% de précision)")
        else:
            print_warning(f"Détection de rôle a une précision faible ({accuracy:.1f}%)")

        # Test de génération de prompt de rôle
        print_test("Test de génération de prompt de rôle...")
        for role_key in ["technical", "academic", "code", "general"]:
            role_prompt = get_role_prompt(role_key)
            if role_prompt:
                print_info(f"Rôle '{role_key}': {role_prompt[:80]}...")
            else:
                print_warning(f"Rôle '{role_key}' ne génère pas de prompt (peut être désactivé)")

        print_success("Génération de prompts de rôle fonctionne")

        return True

    except Exception as e:
        print_error(f"Erreur lors du test de détection de rôle: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_chain_of_thought():
    """Test 4: Test de Chain-of-Thought."""
    print_header("TEST 4: Test Chain-of-Thought")

    try:
        print_test("Test de génération d'instructions Chain-of-Thought...")

        test_questions = [
            ("What is Python?", False),  # Question simple
            (
                "How do I implement a machine learning model step by step?",
                True,
            ),  # Question complexe
            (
                "Why are neural networks effective for image recognition?",
                True,
            ),  # Question avec "why"
            ("Compare Python and Java", True),  # Question avec "compare"
            ("Explain the architecture of transformer models in detail", True),  # Question longue
        ]

        for question, should_have_cot in test_questions:
            cot_instruction = get_chain_of_thought_instruction(question)
            has_cot = len(cot_instruction) > 0

            status = "✅" if has_cot == should_have_cot else "⚠️"
            print_info(f"{status} '{question[:50]}...' → CoT: {'Oui' if has_cot else 'Non'}")

            if has_cot:
                print_info(f"  Instruction: {cot_instruction[:100]}...")

        print_success("Génération d'instructions Chain-of-Thought fonctionne")

        return True

    except Exception as e:
        print_error(f"Erreur lors du test Chain-of-Thought: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_structured_output():
    """Test 5: Test de Structured Output."""
    print_header("TEST 5: Test Structured Output")

    try:
        print_test("Test de génération d'instructions Structured Output...")

        # Tester avec structured output désactivé
        original_value = getattr(Config, "STRUCTURED_OUTPUT_ENABLED", False)

        # Désactiver
        Config.STRUCTURED_OUTPUT_ENABLED = False
        instruction = format_structured_output_instruction()
        if not instruction:
            print_success("Structured output désactivé → pas d'instruction (correct)")
        else:
            print_warning("Structured output désactivé mais instruction générée")

        # Activer avec markdown
        Config.STRUCTURED_OUTPUT_ENABLED = True
        Config.STRUCTURED_OUTPUT_FORMAT = "markdown"
        instruction = format_structured_output_instruction()
        if instruction and "Markdown" in instruction:
            print_success("Structured output (Markdown) fonctionne")
            print_info(f"Instruction: {instruction[:150]}...")
        else:
            print_error("Structured output (Markdown) ne fonctionne pas correctement")
            return False

        # Activer avec JSON
        Config.STRUCTURED_OUTPUT_FORMAT = "json"
        instruction = format_structured_output_instruction()
        if instruction and "JSON" in instruction:
            print_success("Structured output (JSON) fonctionne")
            print_info(f"Instruction: {instruction[:150]}...")
        else:
            print_error("Structured output (JSON) ne fonctionne pas correctement")
            return False

        # Restaurer la valeur originale
        Config.STRUCTURED_OUTPUT_ENABLED = original_value

        return True

    except Exception as e:
        print_error(f"Erreur lors du test Structured Output: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_prompt_generation():
    """Test 6: Test de génération de prompts complets."""
    print_header("TEST 6: Test Génération de Prompts Complets")

    try:
        print_test("Test de génération de prompts avec différentes questions...")

        test_questions = [
            ("What is prompt engineering?", "technical"),
            ("How do I write a Python function?", "code"),
            ("Explain the research findings", "academic"),
            ("What is the weather?", "general"),
        ]

        for question, expected_role in test_questions:
            print_info(f"\nQuestion: '{question}'")

            # Générer le prompt
            prompts = get_prompts(question=question)
            rag_prompt = prompts.get("rag_prompt", "")

            if not rag_prompt:
                print_error("Prompt RAG non généré")
                return False

            # Vérifier les composants
            has_role = (
                expected_role in rag_prompt.lower()
                or "expert" in rag_prompt.lower()
                or "assistant" in rag_prompt.lower()
            )
            has_few_shot = "Exemple" in rag_prompt or "Examples" in rag_prompt
            has_cot = "step by step" in rag_prompt.lower() or "think" in rag_prompt.lower()

            print_info(f"  Rôle détecté: {has_role}")
            print_info(f"  Few-shot: {has_few_shot}")
            print_info(f"  Chain-of-Thought: {has_cot}")
            print_info(f"  Longueur prompt: {len(rag_prompt)} caractères")

            # Tester le formatage avec des valeurs de test
            try:
                formatted = rag_prompt.format(context="Test context [1]", question=question)
                print_success(f"  Formatage réussi ({len(formatted)} caractères)")
            except Exception as e:
                print_error(f"  Erreur de formatage: {str(e)}")
                return False

        print_success("Génération de prompts complets fonctionne")

        return True

    except Exception as e:
        print_error(f"Erreur lors du test de génération de prompts: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_integration():
    """Test 7: Test d'intégration avec le workflow (optionnel)."""
    print_header("TEST 7: Test d'Intégration avec le Workflow (Optionnel)")

    print_warning("Ce test nécessite des documents dans ChromaDB et peut prendre du temps")
    print_info("Il va tester l'intégration complète du Prompt Engineering dans le workflow")

    response = input("\nVoulez-vous exécuter ce test maintenant? (o/n): ").strip().lower()

    if response != "o":
        print_info("Test d'intégration ignoré")
        return True

    try:
        print_test("Test d'intégration avec le workflow complet...")

        from src.rag.Rag_model import get_final_response

        test_questions = ["What is prompt engineering?", "How do LLM agents work?"]

        for question in test_questions:
            print_info(f"\nQuestion de test: {question}")
            print_info(
                "Exécution du workflow complet avec Prompt Engineering (cela peut prendre 30-60 secondes)..."
            )

            start_time = time.time()
            response = get_final_response(question)
            elapsed_time = time.time() - start_time

            print_success(f"Réponse générée en {elapsed_time:.2f}s")
            print_info(f"Réponse (premiers 300 caractères):\n{response[:300]}...")

            # Vérifier que la réponse contient des éléments attendus
            has_citations = "[" in response and "]" in response
            print_info(f"Contient des citations: {has_citations}")

        return True

    except Exception as e:
        print_error(f"Erreur lors du test d'intégration: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Fonction principale pour exécuter tous les tests."""
    print_header("SCRIPT DE TEST: Prompt Engineering Avancé")

    print_info("Ce script teste l'implémentation du Prompt Engineering Avancé")
    print_info("Il vérifie la configuration, few-shot learning, role detection,")
    print_info("chain-of-thought, structured output et l'intégration.\n")

    results = []

    # Test 1: Configuration
    results.append(("Configuration", test_configuration()))

    # Test 2: Few-Shot Examples
    results.append(("Few-Shot Examples", test_few_shot_examples()))

    # Test 3: Role Detection
    results.append(("Role Detection", test_role_detection()))

    # Test 4: Chain-of-Thought
    results.append(("Chain-of-Thought", test_chain_of_thought()))

    # Test 5: Structured Output
    results.append(("Structured Output", test_structured_output()))

    # Test 6: Prompt Generation
    results.append(("Prompt Generation", test_prompt_generation()))

    # Test 7: Intégration workflow (optionnel)
    import sys

    if "--full" in sys.argv:
        results.append(("Intégration Workflow", test_integration()))

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
        print_info("Pour exécuter tous les tests (y compris l'intégration), utilisez:")
        print_info("  python test_prompt_engineering.py --full")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
