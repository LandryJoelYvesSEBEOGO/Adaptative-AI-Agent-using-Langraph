from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime

from api.dependencies import get_current_user
from api.models.conversation import (
    ConversationCreate,
    ConversationOut,
    MessageCreate,
    MessageOut,
)
from api.services.conversation_service import (
    create_conversation,
    list_conversations,
    get_conversation,
    add_message,
    list_messages,
)

router = APIRouter(prefix="/api/v1/chat", tags=["conversations"])


@router.post("/conversations", response_model=ConversationOut)
async def create_new_conversation(
    payload: ConversationCreate,
    current_user: dict = Depends(get_current_user),
):
    conv = create_conversation(current_user["email"], payload.title)
    return {
        **conv,
        "created_at": datetime.fromisoformat(conv["created_at"].replace("Z", "+00:00")),
        "updated_at": datetime.fromisoformat(conv["updated_at"].replace("Z", "+00:00")),
    }


@router.get("/conversations", response_model=List[ConversationOut])
async def get_conversations(
    current_user: dict = Depends(get_current_user),
):
    rows = list_conversations(current_user["email"])
    return [
        {
            **c,
            "created_at": datetime.fromisoformat(c["created_at"].replace("Z", "+00:00")),
            "updated_at": datetime.fromisoformat(c["updated_at"].replace("Z", "+00:00")),
        }
        for c in rows
    ]


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageOut])
async def get_messages(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    conv = get_conversation(conversation_id, current_user["email"])
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    msgs = list_messages(conversation_id)
    return [
        {
            **m,
            "created_at": datetime.fromisoformat(m["created_at"].replace("Z", "+00:00")),
        }
        for m in msgs
    ]


@router.post("/conversations/{conversation_id}/messages", response_model=MessageOut)
async def add_message_to_conversation(
    conversation_id: str,
    payload: MessageCreate,
    current_user: dict = Depends(get_current_user),
):
    conv = get_conversation(conversation_id, current_user["email"])
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    msg = add_message(
        conversation_id=conversation_id,
        role=payload.role,
        content=payload.content,
        citations=payload.citations,
    )
    return {
        **msg,
        "created_at": datetime.fromisoformat(msg["created_at"].replace("Z", "+00:00")),
    }