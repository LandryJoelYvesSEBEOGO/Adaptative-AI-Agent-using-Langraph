from pydantic import BaseModel
from typing import Optional, List, Dict, Literal
from datetime import datetime

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
    citations: Optional[List[Dict]] = None
    created_at: datetime