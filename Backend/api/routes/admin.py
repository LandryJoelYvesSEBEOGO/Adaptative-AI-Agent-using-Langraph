from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from api.dependencies import require_admin
from api.models.admin import (
    MetricOverview,
    RequestDataPoint,
    ErrorDistribution,
    RecentRequest,
    SystemStatus
)
from api.services.metrics_service import (
    get_metrics_overview,
    get_requests_chart_data,
    get_error_distribution,
    get_system_status,
    get_recent_requests
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