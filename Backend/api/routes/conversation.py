from typing import List

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_current_user
from api.models.conversation import (
    ConversationCreate,
    ConversationOut,
    MessageCreate,
    MessageOut,
)
from api.services.conversation_service import (
    add_message,
    create_conversation,
    get_conversation,
    list_conversations,
    list_messages,
)

router = APIRouter(prefix="/api/v1/chat", tags=["conversations"])


@router.post("/conversations", response_model=ConversationOut)
def create_new_conversation(
    payload: ConversationCreate,
    current_user: dict = Depends(get_current_user),
):
    conv = create_conversation(current_user["id"], payload.title)
    return conv


@router.get("/conversations", response_model=List[ConversationOut])
def get_conversations(
    current_user: dict = Depends(get_current_user),
):
    rows = list_conversations(current_user["id"])
    return rows


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageOut])
def get_messages(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    conv = get_conversation(conversation_id, current_user["id"])
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    msgs = list_messages(conversation_id, current_user["id"])
    return msgs


@router.post("/conversations/{conversation_id}/messages", response_model=MessageOut)
def add_message_to_conversation(
    conversation_id: str,
    payload: MessageCreate,
    current_user: dict = Depends(get_current_user),
):
    conv = get_conversation(conversation_id, current_user["id"])
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    msg = add_message(
        conversation_id=conversation_id,
        role=payload.role,
        content=payload.content,
        citations=payload.citations,
    )
    return msg
