from typing import List, Optional

from pydantic import BaseModel, Field


class ChatQueryRequest(BaseModel):
    question: str = Field(..., max_length=2000)
    conversation_id: Optional[str] = None  # Pour maintenir le contexte


class Citation(BaseModel):
    id: int
    source: str
    excerpt: str
    metadata: Optional[dict] = None


class ChatQueryResponse(BaseModel):
    response: str
    citations: List[Citation] = []
    conversation_id: str
    message_id: Optional[str] = None  # id du message assistant (pour le feedback)
    latency: Optional[float] = None
    success: bool = True
    error: Optional[str] = None


class FeedbackRequest(BaseModel):
    message_id: str
    feedback_type: str  # "thumbs_up" | "thumbs_down"
    comment: Optional[str] = None
