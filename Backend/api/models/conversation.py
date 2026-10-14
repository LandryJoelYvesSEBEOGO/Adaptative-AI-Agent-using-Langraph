from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel

from api.models.chat import Citation


class ConversationCreate(BaseModel):
    title: Optional[str] = None


class ConversationOut(BaseModel):
    id: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    citations: Optional[List[Dict]] = None


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    citations: Optional[List[Citation]] = None
    stopped: bool = False
    feedback: Optional[Literal["thumbs_up", "thumbs_down"]] = None  # avis de l'utilisateur courant
    created_at: datetime
