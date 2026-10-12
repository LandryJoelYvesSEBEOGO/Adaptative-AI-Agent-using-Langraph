import json
from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage

from config.Config import Config
from src.core.exceptions import (
    MaxRetriesException,
    ValidationException,  # ✅ utilisé pour les erreurs de génération (streaming et non-streaming)
)
from src.core.recovery_strategies import RecoveryStrategy
from src.core.retry_policy import retry_with_backoff_advanced
from src.rag.generation.formatting import format_docs
from src.rag.llm_utils import get_llm_with_fallback
from src.rag.runtime import get_runtime


def grade_generation_v_documents_and_question(state: Dict) -> str:
    """Grade whether the generation is grounded in the document and answers the question."""
    try:
        print("---CHECK HALLUCINATIONS---")

        max_retries = state.get("max_retries", getattr(Config, "MAX_RETRIES", 3))
        loop_step = state.get("loop_step", 0)

        if not state.get("generation"):
            raise ValidationException("Génération manquante pour la validation")

        generation_content = (
            state["generation"].content
            if hasattr(state["generation"], "content")
            else str(state["generation"])
        )

        # Vérification des hallucinations
        try:
            hallucination_grader_prompt_formatted = (
                get_runtime()
                .prompt["hallucination_grader_prompt"]
                .format(
                    documents=format_docs(state.get("documents", []), with_citations=False),
                    generation=generation_content,
                )
            )

            def _check_hallucination():
                # Utiliser le gestionnaire de clés avec fallback automatique (mode JSON)
                return get_runtime().groq_key_manager.invoke_with_fallback(
                    [
                        SystemMessage(
                            content=get_runtime().prompt["hallucination_grader_instructions"]
                        )
                    ]
                    + [HumanMessage(content=hallucination_grader_prompt_formatted)],
                    json_mode=True,
                )

            result = retry_with_backoff_advanced(
                _check_hallucination, circuit_breaker=get_runtime().llm_circuit_breaker
            )

            try:
                grade_data = json.loads(result.content)
                grade = grade_data.get("binary_score", "no")
            except json.JSONDecodeError:
                print("⚠️ Erreur parsing JSON hallucination. Par défaut: no")
                grade = "no"

            if grade != "yes":
                if loop_step < max_retries:
                    print(
                        f"---DECISION: GENERATION NOT GROUNDED, RETRYING ({loop_step + 1}/{max_retries})---"
                    )
                    # Appliquer stratégie de recovery pour hallucinations
                    if getattr(Config, "RECOVERY_STRATEGY_ENABLED", True):
                        try:
                            current_llm = get_llm_with_fallback()
                            state = RecoveryStrategy.handle_hallucination(state, current_llm)
                        except Exception as e:
                            print(
                                f"⚠️ Erreur lors de l'application de la stratégie de recovery: {str(e)}"
                            )

                    return "not supported"
                else:
                    print("---DECISION: MAX RETRIES REACHED---")
                    raise MaxRetriesException(
                        f"Maximum de {max_retries} tentatives atteint",
                        {"loop_step": loop_step, "max_retries": max_retries},
                    )
        except MaxRetriesException:
            raise
        except Exception as e:
            print(f"⚠️ Erreur vérification hallucination: {str(e)}. On continue...")
            # En cas d'erreur, on considère comme OK pour éviter boucle infinie

        # Vérification de l'utilité
        print("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
        try:
            answer_grader_prompt_formatted = (
                get_runtime()
                .prompt["answer_grader_prompt"]
                .format(question=state["question"], generation=generation_content)
            )

            def _check_useful():
                # Utiliser le gestionnaire de clés avec fallback automatique (mode JSON)
                return get_runtime().groq_key_manager.invoke_with_fallback(
                    [SystemMessage(content=get_runtime().prompt["answer_grader_instructions"])]
                    + [HumanMessage(content=answer_grader_prompt_formatted)],
                    json_mode=True,
                )

            result = retry_with_backoff_advanced(
                _check_useful, circuit_breaker=get_runtime().llm_circuit_breaker
            )

            try:
                grade_data = json.loads(result.content)
                grade = grade_data.get("binary_score", "no")
            except json.JSONDecodeError:
                print("⚠️ Erreur parsing JSON answer. Par défaut: no")
                grade = "no"

            if grade == "yes":
                return "useful"
            else:
                # Appliquer stratégie de recovery pour "not useful"
                if getattr(Config, "RECOVERY_STRATEGY_ENABLED", True):
                    try:
                        state = RecoveryStrategy.handle_not_useful(state)
                    except Exception as e:
                        print(
                            f"⚠️ Erreur lors de l'application de la stratégie de recovery: {str(e)}"
                        )

                return "not useful"
        except Exception as e:
            print(f"⚠️ Erreur vérification utilité: {str(e)}. Par défaut: not useful")
            return "not useful"
    except MaxRetriesException:
        return "max retries"
    except Exception as e:
        print(f"❌ Erreur dans grade_generation: {str(e)}")
        return "max retries"  # Sécurité: arrêt en cas d'erreur
