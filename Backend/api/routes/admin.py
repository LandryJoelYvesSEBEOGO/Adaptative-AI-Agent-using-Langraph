from typing import List

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import require_admin
from api.models.admin import (
    AdminUser,
    ErrorDistribution,
    LatencyComponentStat,
    LatencyTrendPoint,
    MetricOverview,
    RecentRequest,
    RequestDataPoint,
    RequestDetail,
    RoleUpdate,
    SystemStatus,
)
from api.services import user_service
from api.services.metrics_service import (
    get_error_distribution,
    get_latency_component_stats,
    get_latency_trend,
    get_metrics_overview,
    get_recent_requests,
    get_request_details,
    get_requests_chart_data,
    get_system_status,
)

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("/metrics/overview", response_model=MetricOverview)
def get_overview():
    """
    Retourne un aperçu des métriques du système.
    """

    overview = get_metrics_overview()
    return MetricOverview(**overview)


@router.get("/metrics/requests", response_model=List[RequestDataPoint])
def get_requests_metrics(days: int = 7):
    """
    Retourne les données pour le graphique des requêtes.
    """

    chart_data = get_requests_chart_data(days=days)
    return [RequestDataPoint(**item) for item in chart_data]


@router.get("/metrics/recent", response_model=List[RecentRequest])
def get_recent_requests_endpoint(limit: int = 10):
    """
    Retourne les requêtes récentes.
    """

    requests = get_recent_requests(limit=limit)
    return [RecentRequest(**req) for req in requests]


@router.get("/requests", response_model=List[RequestDetail])
def get_requests_endpoint(limit: int = 50):
    """
    Retourne les requêtes détaillées (admin).
    """
    requests = get_request_details(limit=limit)
    return [RequestDetail(**req) for req in requests]


@router.get("/metrics/latency/components", response_model=List[LatencyComponentStat])
def get_latency_components_endpoint():
    """
    Retourne les statistiques de latence par composant.
    """
    stats = get_latency_component_stats()
    return [LatencyComponentStat(**item) for item in stats]


@router.get("/metrics/latency/trend", response_model=List[LatencyTrendPoint])
def get_latency_trend_endpoint(days: int = 7):
    """
    Retourne les tendances de latence.
    """
    trend = get_latency_trend(days=days)
    return [LatencyTrendPoint(**item) for item in trend]


@router.get("/metrics/errors", response_model=ErrorDistribution)
def get_error_distribution_endpoint():
    """
    Retourne la répartition des erreurs.
    """

    distribution = get_error_distribution()
    return ErrorDistribution(**distribution)


@router.get("/system/status", response_model=SystemStatus)
def get_system_status_endpoint():
    """
    Retourne le statut du système.
    """

    status = get_system_status()
    return SystemStatus(**status)


@router.get("/users", response_model=List[AdminUser])
def list_users_endpoint():
    """Utilisateurs et leur activité."""
    return user_service.list_users()


def _raise_for(error: str | None) -> None:
    if error == "not_found":
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if error == "last_admin":
        raise HTTPException(status_code=409, detail="Impossible : dernier administrateur")


@router.patch("/users/{user_id}", response_model=AdminUser)
def update_user_role(
    user_id: str, payload: RoleUpdate, current_user: dict = Depends(require_admin)
):
    """Change le rôle d'un utilisateur (jamais le sien : on ne se rétrograde pas soi-même)."""
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas modifier votre propre rôle")
    _raise_for(user_service.set_role(user_id, payload.role))
    return next(u for u in user_service.list_users() if u["id"] == user_id)


@router.delete("/users/{user_id}", status_code=204)
def delete_user_endpoint(user_id: str, current_user: dict = Depends(require_admin)):
    """Supprime un compte et ses conversations (jamais le sien)."""
    if user_id == current_user["id"]:
        raise HTTPException(
            status_code=400, detail="Vous ne pouvez pas supprimer votre propre compte"
        )
    _raise_for(user_service.delete_user(user_id))
