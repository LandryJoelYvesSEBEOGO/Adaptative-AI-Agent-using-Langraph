import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from api.dependencies import get_current_user
from api.models.chat import ChatQueryRequest, ChatQueryResponse, FeedbackRequest
from api.services.chat_service import process_rag_query, process_rag_query_stream
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
        conv = create_conversation(current_user["email"], title=request.question[:60])
        return conv["id"]
    if not get_conversation(request.conversation_id, current_user["email"]):
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return request.conversation_id


@router.post("/query", response_model=ChatQueryResponse)
async def query_rag(request: ChatQueryRequest, current_user: dict = Depends(get_current_user)):
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="La question ne peut pas être vide")

    # 1) conversation_id
    conversation_id = _resolve_conversation(request, current_user)

    # 2) sauver message user
    add_message(
        conversation_id=conversation_id,
        role="user",
        content=request.question.strip(),
        citations=None,
    )

    # 3) exécuter RAG
    result = process_rag_query(question=request.question, conversation_id=conversation_id)

    # 4) sauver message assistant
    add_message(
        conversation_id=conversation_id,
        role="assistant",
        content=result.get("response", ""),
        citations=result.get("citations", []),
    )

    record_request(
        conversation_id=conversation_id,
        user_email=current_user.get("email"),
        question=request.question.strip(),
        status="success" if result.get("success") else "error",
        error=result.get("error"),
        latencies=result.get("latencies"),
        docs_count=result.get("num_documents"),
        response_length=len(result.get("response", "")),
        answer_quality_score=result.get("answer_quality_score"),
        answer_quality_scores=result.get("answer_quality_scores"),
    )

    return ChatQueryResponse(**result)


@router.post("/query/stream")
async def query_rag_stream(
    request: ChatQueryRequest, current_user: dict = Depends(get_current_user)
):
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="La question ne peut pas être vide")

    # 1) conversation_id
    conversation_id = _resolve_conversation(request, current_user)

    # 2) sauver message user
    add_message(conversation_id, "user", request.question.strip(), None)

    def generate_stream():
        full_response_chunks = []
        citations_holder = {"items": []}

        def on_complete(meta):
            citations_holder["items"] = meta.get("citations", []) or []
            record_request(
                conversation_id=conversation_id,
                user_email=current_user.get("email"),
                question=request.question.strip(),
                status="success" if meta.get("success") else "error",
                error=meta.get("error"),
                latencies=meta.get("latencies"),
                docs_count=meta.get("num_documents"),
                response_length=meta.get("response_length"),
                answer_quality_score=meta.get("answer_quality_score"),
                answer_quality_scores=meta.get("answer_quality_scores"),
            )

        for chunk in process_rag_query_stream(
            question=request.question, conversation_id=conversation_id, on_complete=on_complete
        ):
            full_response_chunks.append(chunk)
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"

        # 3) sauvegarder message assistant à la fin
        full_response = "".join(full_response_chunks)
        add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_response,
            citations=citations_holder["items"],
        )

        # 4) envoyer les citations structurées au frontend
        yield f"data: {json.dumps({'citations': citations_holder['items']})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest, current_user: dict = Depends(get_current_user)):
    """
    Enregistre le feedback utilisateur (thumbs up/down).
    """
    if request.feedback_type not in ("thumbs_up", "thumbs_down"):
        raise HTTPException(status_code=400, detail="feedback_type invalide")

    if not add_feedback(
        message_id=request.message_id,
        user_email=current_user["email"],
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
