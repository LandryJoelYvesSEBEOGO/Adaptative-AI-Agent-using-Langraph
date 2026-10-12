import json
import time
from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage

from config.Config import Config
from src.core.logger import get_logger
from src.core.retry_policy import retry_with_backoff_advanced
from src.rag.generation.formatting import format_docs
from src.rag.runtime import get_runtime


def grade_answer_quality(state: Dict) -> Dict:
    """Évalue la qualité de la réponse générée sur 5 critères."""
    start_time = time.time()
    conversation_id = state.get("conversation_id", "unknown")
    latencies = state.get("latencies", {})

    try:
        get_logger().info(
            "Answer quality scoring started",
            extra={"component": "answer_quality", "conversation_id": conversation_id},
        )
        print("---ANSWER QUALITY SCORING---")

        # Vérifier si activé
        quality_scoring_enabled = getattr(Config, "ANSWER_QUALITY_SCORING_ENABLED", True)
        if not quality_scoring_enabled:
            elapsed_time = time.time() - start_time
            latencies["answer_quality"] = elapsed_time
            return {"answer_quality_scores": None, "latencies": latencies}

        if not state.get("generation"):
            elapsed_time = time.time() - start_time
            latencies["answer_quality"] = elapsed_time
            return {"answer_quality_scores": None, "latencies": latencies}

        # Extraire le contenu de la réponse
        generation_content = (
            state["generation"].content
            if hasattr(state["generation"], "content")
            else str(state["generation"])
        )

        # Formater les documents pour le contexte
        context = format_docs(state.get("documents", []), with_citations=False)

        # Préparer le prompt
        quality_prompt_formatted = (
            get_runtime()
            .prompt["answer_quality_scorer_prompt"]
            .format(
                question=state["question"],
                answer=generation_content[:4000],  # Limiter la longueur
                context=context[:3000],  # Limiter le contexte
            )
        )

        def _score_quality():
            # Utiliser le gestionnaire de clés avec fallback automatique (mode JSON)
            return get_runtime().groq_key_manager.invoke_with_fallback(
                [SystemMessage(content=get_runtime().prompt["answer_quality_scorer_instructions"])]
                + [HumanMessage(content=quality_prompt_formatted)],
                json_mode=True,
            )

        result = retry_with_backoff_advanced(
            _score_quality, circuit_breaker=get_runtime().llm_circuit_breaker
        )

        try:
            quality_data = json.loads(result.content)

            # Extraire les scores
            scores = quality_data.get("scores", {})
            relevance = float(scores.get("relevance", 0.0))
            completeness = float(scores.get("completeness", 0.0))
            conciseness = float(scores.get("conciseness", 0.0))
            accuracy = float(scores.get("accuracy", 0.0))
            coherence = float(scores.get("coherence", 0.0))

            # Calculer le score pondéré
            relevance_weight = getattr(Config, "ANSWER_QUALITY_RELEVANCE_WEIGHT", 0.30)
            completeness_weight = getattr(Config, "ANSWER_QUALITY_COMPLETENESS_WEIGHT", 0.25)
            conciseness_weight = getattr(Config, "ANSWER_QUALITY_CONCISENESS_WEIGHT", 0.15)
            accuracy_weight = getattr(Config, "ANSWER_QUALITY_ACCURACY_WEIGHT", 0.20)
            coherence_weight = getattr(Config, "ANSWER_QUALITY_COHERENCE_WEIGHT", 0.10)

            overall_score = (
                relevance * relevance_weight
                + completeness * completeness_weight
                + conciseness * conciseness_weight
                + accuracy * accuracy_weight
                + coherence * coherence_weight
            )

            # Vérifier le seuil d'acceptation
            threshold = getattr(Config, "ANSWER_QUALITY_ACCEPTANCE_THRESHOLD", 0.65)
            accepted = overall_score >= threshold

            quality_scores = {
                "relevance": relevance,
                "completeness": completeness,
                "conciseness": conciseness,
                "accuracy": accuracy,
                "coherence": coherence,
                "overall_score": overall_score,
                "accepted": accepted,
                "reasoning": quality_data.get("reasoning", "No reasoning provided"),
            }

            print("📊 Answer Quality Scores:")
            print(f"   Relevance: {relevance:.2f}")
            print(f"   Completeness: {completeness:.2f}")
            print(f"   Conciseness: {conciseness:.2f}")
            print(f"   Accuracy: {accuracy:.2f}")
            print(f"   Coherence: {coherence:.2f}")
            print(
                f"   Overall Score: {overall_score:.2f} ({'✅ Accepted' if accepted else '❌ Below threshold'})"
            )

            elapsed_time = time.time() - start_time
            latencies["answer_quality"] = elapsed_time

            get_logger().info(
                "Answer quality scoring completed",
                extra={
                    "component": "answer_quality",
                    "conversation_id": conversation_id,
                    "data": {
                        "latency": elapsed_time,
                        "overall_score": overall_score,
                        "accepted": accepted,
                    },
                },
            )

            return {"answer_quality_scores": quality_scores, "latencies": latencies}

        except json.JSONDecodeError as e:
            print(f"⚠️ Erreur parsing JSON answer quality: {str(e)}")
            elapsed_time = time.time() - start_time
            latencies["answer_quality"] = elapsed_time
            return {"answer_quality_scores": None, "latencies": latencies}

    except Exception as e:
        elapsed_time = time.time() - start_time
        latencies["answer_quality"] = elapsed_time
        print(f"❌ Erreur dans grade_answer_quality: {str(e)}")
        get_logger().error(
            "Answer quality scoring failed",
            extra={"component": "answer_quality", "conversation_id": conversation_id},
            exc_info=True,
        )
        return {"answer_quality_scores": None, "latencies": latencies}
