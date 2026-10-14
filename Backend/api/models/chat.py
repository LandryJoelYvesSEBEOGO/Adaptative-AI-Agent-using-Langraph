from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ChatQueryRequest(BaseModel):
    question: str = Field("", max_length=2000)
    conversation_id: Optional[str] = None  # Pour maintenir le contexte
    regenerate: bool = False  # repose la dernière question de la conversation, sans la dupliquer
    regenerate: bool = False  # repose la dernière question de la conversation (sans la dupliquer)


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


FeedbackType = Literal["thumbs_up", "thumbs_down"]


class FeedbackRequest(BaseModel):
    message_id: str
    feedback_type: FeedbackType
    comment: Optional[str] = Field(default=None, max_length=2000)


class FeedbackResponse(BaseModel):
    success: bool
    message_id: str
    feedback_type: FeedbackType
