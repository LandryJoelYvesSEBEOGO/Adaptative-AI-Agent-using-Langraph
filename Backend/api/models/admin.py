from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel


class MetricOverview(BaseModel):
    total_requests: int
    requests_today: int
    success_rate: float  # En pourcentage
    average_latency: float  # En secondes
    error_count: int


class RequestDataPoint(BaseModel):
    date: str
    requests: int
    success: int
    errors: int


class ErrorDistribution(BaseModel):
    timeout: int
    llm_error: int
    retrieval: int
    web_search: int
    other: int


class RecentRequest(BaseModel):
    id: str
    timestamp: str
    user: str
    question: str
    status: Literal["success", "error"]
    latency: float


class RequestDetail(BaseModel):
    id: str
    timestamp: str
    user: str
    question: str
    status: Literal["success", "error"]
    latency: float
    docs_count: int
    quality: float


class LatencyComponentStat(BaseModel):
    name: str
    avg: float
    p95: float
    p99: float


class LatencyTrendPoint(BaseModel):
    date: str
    endToEnd: float
    retrieval: float
    generation: float


class Alert(BaseModel):
    kind: Literal["error_rate", "latency"]
    message: str


class SystemStatus(BaseModel):
    rag_pipeline: Literal["Active", "Inactive"]  # Active : au moins un document indexé
    vector_db: Literal["Connected", "Disconnected"]  # PostgreSQL + pgvector joignable
    llm_status: Literal["Operational", "Degraded", "Down"]  # clé configurée, taux d'erreur 24 h
    availability_24h: Optional[float] = None  # % de requêtes réussies sur 24 h ; None sans trafic
    documents_ready: int = 0
    alerts: List[Alert] = []  # seuils dépassés sur la fenêtre récente


class AdminUser(BaseModel):
    id: str
    email: str
    name: str
    role: Literal["admin", "user"]
    created_at: datetime
    conversations: int
    requests: int
    last_activity: Optional[datetime] = None


class RoleUpdate(BaseModel):
    role: Literal["admin", "user"]
