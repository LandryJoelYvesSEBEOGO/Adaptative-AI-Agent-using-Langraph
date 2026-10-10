from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from api.dependencies import get_current_user
from api.models.chat import ChatQueryRequest, ChatQueryResponse, FeedbackRequest
from api.services.chat_service import process_rag_query, process_rag_query_stream
import json

router = APIRouter(
    prefix="/api/v1/chat",
    tags=["chat"],
    dependencies=[Depends(get_current_user)],
)

@router.post("/query", response_model=ChatQueryResponse)
async def query_rag(request: ChatQueryRequest):
    """
    Traite une question RAG et retourne la réponse complète.
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="La question ne peut pas être vide")
    
    result = process_rag_query(
        question=request.question,
        conversation_id=request.conversation_id
    )
    
    return ChatQueryResponse(**result)

@router.post("/query/stream")
async def query_rag_stream(request: ChatQueryRequest):
    """
    Traite une question RAG en mode streaming (Server-Sent Events).
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="La question ne peut pas être vide")
    
    def generate_stream():
        for chunk in process_rag_query_stream(
            question=request.question,
            conversation_id=request.conversation_id
        ):
            # Format SSE (Server-Sent Events)
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    Enregistre le feedback utilisateur (thumbs up/down).
    """
    # TODO: Enregistrer le feedback dans une base de données
    # Pour l'instant, on retourne juste une confirmation
    
    return {
        "success": True,
        "message": "Feedback enregistré avec succès",
        "message_id": request.message_id,
        "feedback_type": request.feedback_type
    }