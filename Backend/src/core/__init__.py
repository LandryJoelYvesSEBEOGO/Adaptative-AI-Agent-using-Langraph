# src/core/__init__.py
from .exceptions import (
    RAGException,
    RetrievalException,
    GenerationException,
    ValidationException,
    WorkflowException
)

# Metrics and logging
from .logger import get_logger
from .retrieval_metrics import (
    get_retrieval_metrics_collector,
    calculate_precision_at_k,
    calculate_recall_at_k,
    calculate_mean_average_precision,
    calculate_retrieval_metrics
)
from src.core.retry_policy import (
    retry_with_backoff_advanced,
    get_circuit_breaker,
    CircuitBreaker,
    CircuitState
)
from src.core.recovery_strategies import RecoveryStrategy
from src.core.fallback import get_fallback_manager, FallbackManager
from src.core.few_shot_examples import (
    load_few_shot_examples,
    select_similar_examples,
    format_few_shot_examples
)
from src.core.prompt_templates import (
    detect_role_from_question,
    get_role_prompt,
    get_chain_of_thought_instruction,
    format_structured_output_instruction
)


__all__ = [
    "RAGException",
    "RetrievalException",
    "GenerationException",
    "ValidationException",
    "WorkflowException",
    "get_logger",
    "get_retrieval_metrics_collector",
    "calculate_precision_at_k",
    "calculate_recall_at_k",
    "calculate_mean_average_precision",
    "calculate_retrieval_metrics",
    "retry_with_backoff_advanced",
    "get_circuit_breaker",
    "CircuitBreaker",
    "CircuitState",
    "RecoveryStrategy",
    "get_fallback_manager",
    "FallbackManager",
    "load_few_shot_examples",
    "select_similar_examples",
    "format_few_shot_examples",
    "detect_role_from_question",
    "get_role_prompt",
    "get_chain_of_thought_instruction",
    "format_structured_output_instruction",
]