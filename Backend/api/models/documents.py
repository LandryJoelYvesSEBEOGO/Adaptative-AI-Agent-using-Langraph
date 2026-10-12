from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: str
    filename: str
    company: Optional[str] = None
    fiscal_year: Optional[int] = None
    doc_type: Optional[str] = None
    status: str  # pending | processing | ready | failed
    pages: Optional[int] = None
    chunk_count: Optional[int] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
