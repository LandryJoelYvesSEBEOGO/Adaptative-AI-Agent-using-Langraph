import json
import time
from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage

from config.Config import Config
from src.core.logger import get_logger
from src.core.retry_policy import retry_with_backoff_advanced
from src.rag.Prompts import get_prompts
from src.rag.runtime import get_runtime


def grade_documents(state: Dict) -> Dict:
    """Grade the relevance of retrieved documents using multi-criteria evaluation."""
    start_time = time.time()
    conversation_id = state.get("conversation_id", "unknown")
    latencies = state.get("latencies", {})

    try:
        get_logger().info(
            "Document grading started",
            extra={"component": "grading", "conversation_id": conversation_id},
        )
        print("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
        filtered_docs = []
        web_search = "No"

        # Vérifier que la question est présente
        question = state.get("question")
        if not question:
            print("⚠️ Question manquante dans le state pour le grading")
            elapsed_time = time.time() - start_time
            latencies["grading"] = elapsed_time
            return {
                "documents": [],
                "web_search": "Yes",
                "latencies": latencies,
                "question": None,  # Question manquante
                "conversation_id": conversation_id,
                "error_history": state.get("error_history", [])
                + ["Question manquante pour grading"],
            }

        if not state.get("documents"):
            elapsed_time = time.time() - start_time
            latencies["grading"] = elapsed_time
            return {
                "documents": [],
                "web_search": "Yes",
                "latencies": latencies,
                "question": question,  # Préserver la question
                "conversation_id": conversation_id,
                "error_history": state.get("error_history", []),
            }

        # Obtenir les prompts avec la question
        prompt = get_prompts(question=question)

        # Vérifier si multi-criteria grading est activé
        multi_criteria_enabled = getattr(Config, "MULTI_CRITERIA_GRADING_ENABLED", True)

        all_scores = []  # Pour seuil adaptatif

        for doc in state["documents"]:
            try:
                multi_criteria_failed = False
                if multi_criteria_enabled:
                    # Grading multi-critères
                    grader_prompt_formatted = prompt["multi_criteria_grader_prompt"].format(
                        document=doc.page_content[
                            :4000
                        ],  # Limiter la longueur pour éviter token limit
                        question=question,
                    )

                    def _grade():
                        # Utiliser le gestionnaire de clés avec fallback automatique (mode JSON)
                        return get_runtime().groq_key_manager.invoke_with_fallback(
                            [SystemMessage(content=prompt["multi_criteria_grader_instructions"])]
                            + [HumanMessage(content=grader_prompt_formatted)],
                            json_mode=True,
                        )

                    result = retry_with_backoff_advanced(
                        _grade, circuit_breaker=get_runtime().llm_circuit_breaker
                    )

                    try:
                        grade_data = json.loads(result.content)

                        # Extraire les scores
                        scores = grade_data.get("scores", {})
                        relevance = float(scores.get("relevance", 0.0))
                        coverage = float(scores.get("coverage", 0.0))
                        freshness = float(scores.get("freshness", 0.7))  # Default si inconnu
                        authority = float(scores.get("authority", 0.7))  # Default si inconnu
                        clarity = float(scores.get("clarity", 0.7))

                        # Calculer le score pondéré
                        weights = {
                            "relevance": getattr(Config, "GRADING_RELEVANCE_WEIGHT", 0.35),
                            "coverage": getattr(Config, "GRADING_COVERAGE_WEIGHT", 0.25),
                            "freshness": getattr(Config, "GRADING_FRESHNESS_WEIGHT", 0.15),
                            "authority": getattr(Config, "GRADING_AUTHORITY_WEIGHT", 0.15),
                            "clarity": getattr(Config, "GRADING_CLARITY_WEIGHT", 0.10),
                        }

                        overall_score = (
                            relevance * weights["relevance"]
                            + coverage * weights["coverage"]
                            + freshness * weights["freshness"]
                            + authority * weights["authority"]
                            + clarity * weights["clarity"]
                        )

                        # Utiliser le score du LLM si fourni, sinon utiliser notre calcul
                        overall_score = float(grade_data.get("overall_score", overall_score))
                        all_scores.append(overall_score)

                        # Déterminer le seuil
                        acceptance_threshold = getattr(Config, "GRADING_ACCEPTANCE_THRESHOLD", 0.6)
                        adaptive_threshold = getattr(Config, "GRADING_ADAPTIVE_THRESHOLD", True)

                        if adaptive_threshold and len(all_scores) > 1:
                            # Seuil adaptatif : moyenne des scores * 0.8 (plus permissif)
                            threshold = (sum(all_scores) / len(all_scores)) * 0.8
                            threshold = max(
                                threshold, acceptance_threshold * 0.7
                            )  # Minimum 70% du seuil fixe
                        else:
                            threshold = acceptance_threshold

                        accepted = grade_data.get("accepted", overall_score >= threshold)
                        reasoning = grade_data.get("reasoning", "")

                        print(
                            f"---GRADE: Score={overall_score:.2f} (R:{relevance:.2f}, C:{coverage:.2f}, F:{freshness:.2f}, A:{authority:.2f}, Cl:{clarity:.2f}) | Threshold={threshold:.2f}---"
                        )
                        if reasoning:
                            print(f"  Reasoning: {reasoning[:150]}...")

                        if accepted and overall_score >= threshold:
                            print(f"✅ DOCUMENT ACCEPTED (score: {overall_score:.2f})")
                            filtered_docs.append(doc)
                        else:
                            print(
                                f"❌ DOCUMENT REJECTED (score: {overall_score:.2f} < threshold: {threshold:.2f})"
                            )
                            web_search = "Yes"

                    except (json.JSONDecodeError, ValueError, KeyError) as e:
                        print(
                            f"⚠️ Erreur parsing JSON multi-criteria: {str(e)}. Fallback sur grading binaire pour ce document."
                        )
                        multi_criteria_failed = True

                if not multi_criteria_enabled or multi_criteria_failed:
                    # Grading binaire (fallback ou désactivé)
                    doc_grader_prompt_formatted = prompt["doc_grader_prompt"].format(
                        document=doc.page_content[:4000], question=question
                    )

                    def _grade():
                        # Utiliser le gestionnaire de clés avec fallback automatique (mode JSON)
                        return get_runtime().groq_key_manager.invoke_with_fallback(
                            [SystemMessage(content=prompt["doc_grader_instructions"])]
                            + [HumanMessage(content=doc_grader_prompt_formatted)],
                            json_mode=True,
                        )

                    result = retry_with_backoff_advanced(
                        _grade, circuit_breaker=get_runtime().llm_circuit_breaker
                    )

                    try:
                        grade_data = json.loads(result.content)
                        grade = grade_data.get("binary_score", "no")
                    except json.JSONDecodeError as e:
                        print(f"⚠️ Erreur parsing JSON: {str(e)}. Score par défaut: no")
                        grade = "no"

                    if grade.lower() == "yes":
                        print("---GRADE: DOCUMENT RELEVANT---")
                        filtered_docs.append(doc)
                    else:
                        print("---GRADE: DOCUMENT NOT RELEVANT---")
                        web_search = "Yes"

            except Exception as e:
                print(f"⚠️ Erreur lors du grading d'un document: {str(e)}. Document ignoré.")
                web_search = "Yes"
                continue

        elapsed_time = time.time() - start_time
        latencies["grading"] = elapsed_time

        get_logger().info(
            "Document grading completed",
            extra={
                "component": "grading",
                "conversation_id": conversation_id,
                "data": {
                    "latency": elapsed_time,
                    "num_filtered": len(filtered_docs),
                    "num_total": len(state.get("documents", [])),
                    "multi_criteria": multi_criteria_enabled,
                    "avg_score": sum(all_scores) / len(all_scores) if all_scores else 0.0,
                },
            },
        )

        # Préserver tous les champs du state, notamment la question
        return {
            "documents": filtered_docs,
            "web_search": web_search,
            "latencies": latencies,
            "question": question,  # Préserver la question
            "conversation_id": conversation_id,
            "error_history": state.get("error_history", []),
        }

    except Exception as e:
        elapsed_time = time.time() - start_time
        latencies["grading"] = elapsed_time
        print(f"❌ Erreur dans grade_documents: {str(e)}")
        get_logger().error(
            "Document grading failed",
            extra={"component": "grading", "conversation_id": conversation_id},
            exc_info=True,
        )
        # En cas d'erreur, on continue avec tous les documents mais on préserve la question
        return {
            "documents": state.get("documents", []),
            "web_search": "Yes",
            "latencies": latencies,
            "question": state.get("question"),  # Préserver la question
            "conversation_id": conversation_id,
            "error_history": state.get("error_history", []) + [f"Erreur grading: {str(e)}"],
        }
