from fastapi import APIRouter, Depends, HTTPException
from api.dependencies import require_admin
from typing import Optional, List
from api.models.admin import (
    MetricOverview,
    RequestDataPoint,
    ErrorDistribution,
    RecentRequest,
    RequestDetail,
    LatencyComponentStat,
    LatencyTrendPoint,
    SystemStatus
)
from api.services.metrics_service import (
    get_metrics_overview,
    get_requests_chart_data,
    get_error_distribution,
    get_system_status,
    get_recent_requests,
    get_request_details,
    get_latency_component_stats,
    get_latency_trend
)

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)

@router.get("/metrics/overview", response_model=MetricOverview)
async def get_overview():
    """
    Retourne un aperçu des métriques du système.
    """
    
    overview = get_metrics_overview()
    return MetricOverview(**overview)

@router.get("/metrics/requests", response_model=List[RequestDataPoint])
async def get_requests_metrics(days: Optional[int] = 7):
    """
    Retourne les données pour le graphique des requêtes.
    """
    
    chart_data = get_requests_chart_data(days=days)
    return [RequestDataPoint(**item) for item in chart_data]

@router.get("/metrics/recent", response_model=List[RecentRequest])
async def get_recent_requests_endpoint(limit: Optional[int] = 10):
    """
    Retourne les requêtes récentes.
    """
    
    requests = get_recent_requests(limit=limit)
    return [RecentRequest(**req) for req in requests]

@router.get("/requests", response_model=List[RequestDetail])
async def get_requests_endpoint(limit: Optional[int] = 50):
    """
    Retourne les requêtes détaillées (admin).
    """
    requests = get_request_details(limit=limit)
    return [RequestDetail(**req) for req in requests]

@router.get("/metrics/latency/components", response_model=List[LatencyComponentStat])
async def get_latency_components_endpoint():
    """
    Retourne les statistiques de latence par composant.
    """
    stats = get_latency_component_stats()
    return [LatencyComponentStat(**item) for item in stats]

@router.get("/metrics/latency/trend", response_model=List[LatencyTrendPoint])
async def get_latency_trend_endpoint(days: Optional[int] = 7):
    """
    Retourne les tendances de latence.
    """
    trend = get_latency_trend(days=days)
    return [LatencyTrendPoint(**item) for item in trend]

@router.get("/metrics/errors", response_model=ErrorDistribution)
async def get_error_distribution_endpoint():
    """
    Retourne la répartition des erreurs.
    """
    
    distribution = get_error_distribution()
    return ErrorDistribution(**distribution)

@router.get("/system/status", response_model=SystemStatus)
async def get_system_status_endpoint():
    """
    Retourne le statut du système.
    """
    
    status = get_system_status()
    return SystemStatus(**status)