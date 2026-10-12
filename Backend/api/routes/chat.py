import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from api.dependencies import get_current_user
from api.models.chat import ChatQueryRequest, ChatQueryResponse, FeedbackRequest
from api.services import chat_service
from api.services.conversation_service import (
    add_feedback,
    add_message,
    create_conversation,
    get_conversation,
)
from api.services.metrics_service import record_request

router = APIRouter(
    prefix="/api/v1/chat",
    tags=["chat"],
    dependencies=[Depends(get_current_user)],
)


def _resolve_conversation(request: ChatQueryRequest, current_user: dict) -> str:
    """Retourne l'id de conversation, en vérifiant qu'elle appartient à l'utilisateur."""
    if not request.conversation_id:
        conv = create_conversation(current_user["id"], title=request.question[:60])
        return conv["id"]
    if not get_conversation(request.conversation_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return request.conversation_id


def _persist_outcome(
    conversation_id: str, question: str, user_id: str, result: dict
) -> Optional[str]:
    """Enregistre la réponse (si réussie) et la mesure de la requête ; retourne l'id du message."""
    message_id = None
    if result.get("success"):
        message_id = add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=result.get("response", ""),
            citations=result.get("citations", []),
        )["id"]
    record_request(
        conversation_id=conversation_id,
        user_id=user_id,
        question=question,
        status="success" if result.get("success") else "error",
        error=result.get("error"),
        latencies=result.get("latencies"),
        docs_count=result.get("num_documents"),
        response_length=len(result.get("response", "")),
        answer_quality_score=result.get("answer_quality_score"),
        answer_quality_scores=result.get("answer_quality_scores"),
    )
    return message_id


def _start_turn(request: ChatQueryRequest, current_user: dict) -> tuple[str, str]:
    """Valide la question, résout la conversation et enregistre le message utilisateur."""
    question = (request.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="La question ne peut pas être vide")
    conversation_id = _resolve_conversation(request, current_user)
    add_message(conversation_id, "user", question, None)
    return conversation_id, question


@router.post("/query", response_model=ChatQueryResponse)
async def query_rag(request: ChatQueryRequest, current_user: dict = Depends(get_current_user)):
    conversation_id, question = await run_in_threadpool(_start_turn, request, current_user)
    result = await chat_service.answer(question, conversation_id)
    message_id = await run_in_threadpool(
        _persist_outcome, conversation_id, question, current_user["id"], result
    )
    return ChatQueryResponse(**result, message_id=message_id)


@router.post("/query/stream")
async def query_rag_stream(
    request: ChatQueryRequest, current_user: dict = Depends(get_current_user)
):
    conversation_id, question = await run_in_threadpool(_start_turn, request, current_user)

    async def event_stream():
        async for event in chat_service.answer_stream(question, conversation_id):
            if event["type"] == "token":
                yield _sse({"chunk": event["text"]})
                continue
            result = event["result"]
            message_id = await run_in_threadpool(
                _persist_outcome, conversation_id, question, current_user["id"], result
            )
            if result["success"]:
                yield _sse(
                    {
                        "citations": result["citations"],
                        "message_id": message_id,
                        "conversation_id": conversation_id,
                    }
                )
            else:
                yield _sse({"error": result["error"]})
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/feedback")
def submit_feedback(request: FeedbackRequest, current_user: dict = Depends(get_current_user)):
    """
    Enregistre le feedback utilisateur (thumbs up/down).
    """
    if request.feedback_type not in ("thumbs_up", "thumbs_down"):
        raise HTTPException(status_code=400, detail="feedback_type invalide")

    if not add_feedback(
        message_id=request.message_id,
        user_id=current_user["id"],
        feedback_type=request.feedback_type,
        comment=request.comment,
    ):
        raise HTTPException(status_code=404, detail="Message introuvable")

    return {
        "success": True,
        "message": "Feedback enregistré avec succès",
        "message_id": request.message_id,
        "feedback_type": request.feedback_type,
    }
