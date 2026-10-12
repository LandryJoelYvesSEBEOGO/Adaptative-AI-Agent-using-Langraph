import operator
from typing import Annotated, Dict, List, Optional

from typing_extensions import TypedDict


# GraphState definition
class GraphState(TypedDict, total=False):
    question: str
    generation: str
    web_search: str
    max_retries: int
    answers: int
    loop_step: Annotated[int, operator.add]
    documents: List[str]
    error_history: List[str]  # Nouveau : historique des erreurs
    conversation_id: Optional[str]  # ID de conversation pour métriques
    latencies: Optional[Dict[str, float]]  # Latences pour métriques
    answer_quality_scores: Optional[Dict]  # Scores de qualité de la réponse
