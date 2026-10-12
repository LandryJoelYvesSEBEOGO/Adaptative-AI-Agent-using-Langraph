"""Service de chat : relie l'API au pipeline RAG (un seul chemin, normal ou streaming)."""

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any, Dict, Optional

from api.services.conversation_service import list_messages
from config.settings import get_settings
from src.rag import pipeline

logger = logging.getLogger(__name__)

GENERIC_ERROR = "Erreur lors du traitement de la requête"


def _normalize(text: Optional[str]) -> str:
    return (text or "").strip()


def build_conversation_history(conversation_id: Optional[str], current_question: str) -> str:
    """Derniers tours de la conversation (hors question en cours), tronqués par config."""
    if not conversation_id:
        return ""
    try:
        messages = list_messages(conversation_id)
    except Exception:
        logger.exception("Lecture de l'historique impossible")
        return ""

    if messages and messages[-1].get("role") == "user":
        if _normalize(messages[-1].get("content")) == _normalize(current_question):
            messages = messages[:-1]  # la question en cours vient d'être enregistrée

    settings = get_settings()
    recent = messages[-settings.CONVERSATION_CONTEXT_TURNS * 2 :]
    parts = []
    for msg in recent:
        content = _normalize(msg.get("content"))
        if content:
            role = msg.get("role") or "user"
            label = {"user": "User", "assistant": "Assistant"}.get(role, role)
            parts.append(f"{label}: {content}")

    history = "\n".join(parts)
    max_chars = settings.CONVERSATION_CONTEXT_MAX_CHARS
    return history[-max_chars:] if max_chars and len(history) > max_chars else history


def _result(output: pipeline.RagOutput, conversation_id: str) -> Dict[str, Any]:
    return {
        "response": output.answer,
        "citations": output.citations,
        "conversation_id": conversation_id,
        "latency": output.latencies.get("end_to_end"),
        "latencies": output.latencies,
        "num_documents": output.num_documents,
        "llm_calls": output.llm_calls,
        "answer_quality_score": None,
        "answer_quality_scores": None,
        "success": True,
        "error": None,
    }


def _failure(conversation_id: str, started: float) -> Dict[str, Any]:
    elapsed = time.perf_counter() - started
    return {
        "response": "",
        "citations": [],
        "conversation_id": conversation_id,
        "latency": elapsed,
        "latencies": {"end_to_end": elapsed},
        "num_documents": 0,
        "llm_calls": 0,
        "answer_quality_score": None,
        "answer_quality_scores": None,
        "success": False,
        "error": GENERIC_ERROR,
    }


async def answer(question: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
    """Réponse complète (même graphe que le streaming)."""
    conversation_id = conversation_id or str(uuid.uuid4())
    started = time.perf_counter()
    try:
        history = await asyncio.to_thread(build_conversation_history, conversation_id, question)
        output = await pipeline.run_rag(question, history)
        return _result(output, conversation_id)
    except Exception:
        logger.exception("Erreur lors du traitement RAG")
        return _failure(conversation_id, started)


async def answer_stream(
    question: str, conversation_id: Optional[str] = None
) -> AsyncIterator[Dict[str, Any]]:
    """Événements `{"type": "token", "text": …}` puis `{"type": "done", "result": {…}}`.

    En cas d'erreur : `{"type": "done", "result": {…, "success": False}}` (message générique)."""
    conversation_id = conversation_id or str(uuid.uuid4())
    started = time.perf_counter()
    try:
        history = await asyncio.to_thread(build_conversation_history, conversation_id, question)
        async for event in pipeline.stream_rag(question, history):
            if event["type"] == "token":
                yield event
            else:
                yield {"type": "done", "result": _result(event["output"], conversation_id)}
    except Exception:
        logger.exception("Erreur lors du streaming RAG")
        yield {"type": "done", "result": _failure(conversation_id, started)}
