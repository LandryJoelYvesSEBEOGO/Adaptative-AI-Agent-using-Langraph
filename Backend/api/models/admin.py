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
    status: str  # "success" | "error"
    latency: float


class RequestDetail(BaseModel):
    id: str
    timestamp: str
    user: str
    question: str
    status: str  # "success" | "error"
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


class SystemStatus(BaseModel):
    rag_pipeline: str  # "Active" | "Inactive"
    vector_db: str  # "Connected" | "Disconnected"
    llm_status: str  # "Operational" | "Degraded" | "Down"
    uptime_percentage: float
