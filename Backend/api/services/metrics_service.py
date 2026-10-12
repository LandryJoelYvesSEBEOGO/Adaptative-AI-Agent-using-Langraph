from datetime import UTC, datetime
from typing import Dict, List, Optional

from sqlalchemy import case, func, select

from api.database import session_scope
from api.db_models import RagRequest, User


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = min(int(len(sorted_values) * pct), len(sorted_values) - 1)
    return float(sorted_values[index])


def _day(column):
    """Jour (AAAA-MM-JJ) d'un horodatage, portable SQLite / PostgreSQL."""
    return func.date(column)


def record_request(
    conversation_id: Optional[str],
    user_id: Optional[str],
    question: str,
    status: str,
    error: Optional[str],
    latencies: Optional[Dict[str, float]],
    docs_count: Optional[int],
    response_length: Optional[int],
    answer_quality_score: Optional[float],
    answer_quality_scores: Optional[Dict],
) -> None:
    latencies = latencies or {}
    with session_scope() as db:
        db.add(
            RagRequest(
                conversation_id=conversation_id,
                user_id=user_id,
                question=question,
                status=status,
                error=error,
                latency_end_to_end=latencies.get("end_to_end"),
                latency_retrieval=latencies.get("retrieval"),
                latency_generation=latencies.get("generation"),
                latency_grading=latencies.get("grading"),
                latency_web_search=latencies.get("web_search"),
                latency_reranking=latencies.get("reranking"),
                latency_answer_quality=latencies.get("answer_quality"),
                docs_count=docs_count,
                response_length=response_length,
                answer_quality_score=answer_quality_score,
                answer_quality_scores=answer_quality_scores or None,
            )
        )


def get_metrics_overview() -> Dict:
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    with session_scope() as db:
        total_requests, total_errors, avg_latency = db.execute(
            select(
                func.count(RagRequest.id),
                func.coalesce(func.sum(case((RagRequest.status == "error", 1), else_=0)), 0),
                func.avg(RagRequest.latency_end_to_end),
            )
        ).one()
        requests_today = db.scalar(
            select(func.count(RagRequest.id)).where(RagRequest.created_at >= today_start)
        )

    success_rate = (
        ((total_requests - total_errors) / total_requests) * 100 if total_requests > 0 else 0.0
    )
    return {
        "total_requests": total_requests,
        "requests_today": requests_today or 0,
        "success_rate": success_rate,
        "average_latency": float(avg_latency or 0.0),
        "error_count": int(total_errors),
    }


def _format_day(day) -> str:
    if isinstance(day, str):
        day = datetime.fromisoformat(day)
    return day.strftime("%d %b")


def get_requests_chart_data(days: int = 7) -> List[Dict]:
    day = _day(RagRequest.created_at)
    with session_scope() as db:
        rows = db.execute(
            select(
                day.label("day"),
                func.count(RagRequest.id),
                func.sum(case((RagRequest.status == "success", 1), else_=0)),
                func.sum(case((RagRequest.status == "error", 1), else_=0)),
            )
            .group_by(day)
            .order_by(day.desc())
            .limit(days)
        ).all()

    return [
        {
            "date": _format_day(d),
            "requests": requests,
            "success": int(success or 0),
            "errors": int(errors or 0),
        }
        for d, requests, success, errors in reversed(rows)
    ]


_ERROR_BUCKETS = (
    ("timeout", ("timeout",)),
    ("llm_error", ("llm", "generation")),
    ("retrieval", ("retrieval", "retrieve")),
    ("web_search", ("web", "search")),
)


def get_error_distribution() -> Dict:
    distribution = {"timeout": 0, "llm_error": 0, "retrieval": 0, "web_search": 0, "other": 0}
    with session_scope() as db:
        errors = db.scalars(
            select(RagRequest.error).where(
                RagRequest.status == "error", RagRequest.error.is_not(None)
            )
        ).all()

    for raw in errors:
        error = (raw or "").lower()
        for bucket, keywords in _ERROR_BUCKETS:
            if any(k in error for k in keywords):
                distribution[bucket] += 1
                break
        else:
            distribution["other"] += 1
    return distribution


def _recent_rows(limit: int):
    with session_scope() as db:
        return db.execute(
            select(RagRequest, User.email)
            .outerjoin(User, User.id == RagRequest.user_id)
            .order_by(RagRequest.created_at.desc())
            .limit(limit)
        ).all()


def get_recent_requests(limit: int = 10) -> List[Dict]:
    formatted = []
    for req, email in _recent_rows(limit):
        question = req.question or ""
        formatted.append(
            {
                "id": req.id,
                "timestamp": req.created_at.isoformat(),
                "user": email or "unknown",
                "question": question[:50] + "..." if len(question) > 50 else question,
                "status": req.status,
                "latency": req.latency_end_to_end or 0.0,
            }
        )
    return formatted


def get_request_details(limit: int = 50) -> List[Dict]:
    return [
        {
            "id": req.id,
            "timestamp": req.created_at.isoformat(),
            "user": email or "unknown",
            "question": req.question,
            "status": req.status,
            "latency": req.latency_end_to_end or 0.0,
            "docs_count": req.docs_count or 0,
            "quality": req.answer_quality_score or 0.0,
        }
        for req, email in _recent_rows(limit)
    ]


def get_latency_component_stats() -> List[Dict]:
    with session_scope() as db:
        rows = db.execute(
            select(
                RagRequest.latency_end_to_end,
                RagRequest.latency_retrieval,
                RagRequest.latency_generation,
                RagRequest.latency_grading,
                RagRequest.latency_web_search,
            ).where(RagRequest.status == "success")
        ).all()

    names = ("End-to-End", "Retrieval", "Generation", "Grading", "Web Search")
    result = []
    for index, name in enumerate(names):
        values = [row[index] for row in rows if row[index] is not None]
        result.append(
            {
                "name": name,
                "avg": sum(values) / len(values) if values else 0.0,
                "p95": _percentile(values, 0.95),
                "p99": _percentile(values, 0.99),
            }
        )
    return result


def get_latency_trend(days: int = 7) -> List[Dict]:
    day = _day(RagRequest.created_at)
    with session_scope() as db:
        rows = db.execute(
            select(
                day.label("day"),
                func.avg(RagRequest.latency_end_to_end),
                func.avg(RagRequest.latency_retrieval),
                func.avg(RagRequest.latency_generation),
            )
            .where(RagRequest.status == "success")
            .group_by(day)
            .order_by(day.desc())
            .limit(days)
        ).all()

    return [
        {
            "date": _format_day(d),
            "endToEnd": float(end_to_end or 0.0),
            "retrieval": float(retrieval or 0.0),
            "generation": float(generation or 0.0),
        }
        for d, end_to_end, retrieval, generation in reversed(rows)
    ]


def get_system_status() -> Dict:
    return {
        "rag_pipeline": "Active",
        "vector_db": "Connected",
        "llm_status": "Operational",
        "uptime_percentage": 98.5,
    }
