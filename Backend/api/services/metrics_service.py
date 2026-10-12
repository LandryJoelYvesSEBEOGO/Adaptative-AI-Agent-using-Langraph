import json
import uuid
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

from api.db import get_connection

ISO = "%Y-%m-%dT%H:%M:%S.%fZ"


def _now() -> str:
    return datetime.utcnow().strftime(ISO)


def _parse_date(date_str: str) -> date:
    return datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(len(sorted_values) * pct)
    if index >= len(sorted_values):
        index = len(sorted_values) - 1
    return float(sorted_values[index])


def record_request(
    conversation_id: str,
    user_email: Optional[str],
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
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO rag_requests (
            id,
            conversation_id,
            user_email,
            question,
            status,
            error,
            latency_end_to_end,
            latency_retrieval,
            latency_generation,
            latency_grading,
            latency_web_search,
            latency_reranking,
            latency_answer_quality,
            docs_count,
            response_length,
            answer_quality_score,
            answer_quality_scores,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            conversation_id,
            user_email,
            question,
            status,
            error,
            latencies.get("end_to_end"),
            latencies.get("retrieval"),
            latencies.get("generation"),
            latencies.get("grading"),
            latencies.get("web_search"),
            latencies.get("reranking"),
            latencies.get("answer_quality"),
            docs_count,
            response_length,
            answer_quality_score,
            json.dumps(answer_quality_scores) if answer_quality_scores else None,
            _now(),
        ),
    )
    conn.commit()
    conn.close()


def get_metrics_overview() -> Dict:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS total FROM rag_requests")
    total_requests = cur.fetchone()["total"] or 0

    cur.execute("SELECT COUNT(*) AS total FROM rag_requests WHERE status = 'error'")
    total_errors = cur.fetchone()["total"] or 0

    cur.execute("SELECT AVG(latency_end_to_end) AS avg_latency FROM rag_requests")
    avg_latency = cur.fetchone()["avg_latency"] or 0.0

    today = datetime.utcnow().date().isoformat()
    cur.execute(
        "SELECT COUNT(*) AS total FROM rag_requests WHERE substr(created_at, 1, 10) = ?",
        (today,),
    )
    requests_today = cur.fetchone()["total"] or 0

    conn.close()

    success_rate = (
        ((total_requests - total_errors) / total_requests) * 100
        if total_requests > 0
        else 0.0
    )

    return {
        "total_requests": total_requests,
        "requests_today": requests_today,
        "success_rate": success_rate,
        "average_latency": avg_latency,
        "error_count": total_errors,
    }


def get_requests_chart_data(days: int = 7) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            substr(created_at, 1, 10) AS date,
            COUNT(*) AS requests,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success,
            SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS errors
        FROM rag_requests
        GROUP BY substr(created_at, 1, 10)
        ORDER BY date DESC
        LIMIT ?
        """,
        (days,),
    )
    rows = cur.fetchall()
    conn.close()

    result = []
    for row in rows[::-1]:
        date_obj = datetime.fromisoformat(row["date"])
        result.append(
            {
                "date": date_obj.strftime("%d %b"),
                "requests": row["requests"],
                "success": row["success"],
                "errors": row["errors"],
            }
        )

    return result


def get_error_distribution() -> Dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT error FROM rag_requests WHERE status = 'error' AND error IS NOT NULL")
    rows = cur.fetchall()
    conn.close()

    distribution = {
        "timeout": 0,
        "llm_error": 0,
        "retrieval": 0,
        "web_search": 0,
        "other": 0,
    }

    for row in rows:
        error = (row["error"] or "").lower()
        if "timeout" in error:
            distribution["timeout"] += 1
        elif "llm" in error or "generation" in error:
            distribution["llm_error"] += 1
        elif "retrieval" in error or "retrieve" in error:
            distribution["retrieval"] += 1
        elif "web" in error or "search" in error:
            distribution["web_search"] += 1
        else:
            distribution["other"] += 1

    return distribution


def get_recent_requests(limit: int = 10) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, created_at, user_email, question, status, latency_end_to_end
        FROM rag_requests
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()

    formatted = []
    for row in rows:
        question = row["question"] or ""
        formatted.append(
            {
                "id": row["id"],
                "timestamp": row["created_at"],
                "user": row["user_email"] or "unknown",
                "question": question[:50] + "..." if len(question) > 50 else question,
                "status": row["status"],
                "latency": row["latency_end_to_end"] or 0.0,
            }
        )

    return formatted


def get_request_details(limit: int = 50) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, created_at, user_email, question, status, latency_end_to_end, docs_count, answer_quality_score
        FROM rag_requests
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append(
            {
                "id": row["id"],
                "timestamp": row["created_at"],
                "user": row["user_email"] or "unknown",
                "question": row["question"],
                "status": row["status"],
                "latency": row["latency_end_to_end"] or 0.0,
                "docs_count": row["docs_count"] or 0,
                "quality": row["answer_quality_score"] or 0.0,
            }
        )
    return result


def get_latency_component_stats() -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            latency_end_to_end,
            latency_retrieval,
            latency_generation,
            latency_grading,
            latency_web_search
        FROM rag_requests
        WHERE status = 'success'
        """
    )
    rows = cur.fetchall()
    conn.close()

    buckets = {
        "End-to-End": [],
        "Retrieval": [],
        "Generation": [],
        "Grading": [],
        "Web Search": [],
    }

    for row in rows:
        if row["latency_end_to_end"] is not None:
            buckets["End-to-End"].append(row["latency_end_to_end"])
        if row["latency_retrieval"] is not None:
            buckets["Retrieval"].append(row["latency_retrieval"])
        if row["latency_generation"] is not None:
            buckets["Generation"].append(row["latency_generation"])
        if row["latency_grading"] is not None:
            buckets["Grading"].append(row["latency_grading"])
        if row["latency_web_search"] is not None:
            buckets["Web Search"].append(row["latency_web_search"])

    result = []
    for name, values in buckets.items():
        avg = sum(values) / len(values) if values else 0.0
        result.append(
            {
                "name": name,
                "avg": avg,
                "p95": _percentile(values, 0.95),
                "p99": _percentile(values, 0.99),
            }
        )
    return result


def get_latency_trend(days: int = 7) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            substr(created_at, 1, 10) AS date,
            AVG(latency_end_to_end) AS end_to_end,
            AVG(latency_retrieval) AS retrieval,
            AVG(latency_generation) AS generation
        FROM rag_requests
        WHERE status = 'success'
        GROUP BY substr(created_at, 1, 10)
        ORDER BY date DESC
        LIMIT ?
        """,
        (days,),
    )
    rows = cur.fetchall()
    conn.close()

    result = []
    for row in rows[::-1]:
        date_obj = datetime.fromisoformat(row["date"])
        result.append(
            {
                "date": date_obj.strftime("%d %b"),
                "endToEnd": row["end_to_end"] or 0.0,
                "retrieval": row["retrieval"] or 0.0,
                "generation": row["generation"] or 0.0,
            }
        )
    return result


def get_system_status() -> Dict:
    return {
        "rag_pipeline": "Active",
        "vector_db": "Connected",
        "llm_status": "Operational",
        "uptime_percentage": 98.5,
    }
import json
import uuid
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

from api.db import get_connection

ISO = "%Y-%m-%dT%H:%M:%S.%fZ"


def _now() -> str:
    return datetime.utcnow().strftime(ISO)


def _parse_date(date_str: str) -> date:
    return datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(len(sorted_values) * pct)
    if index >= len(sorted_values):
        index = len(sorted_values) - 1
    return float(sorted_values[index])


def record_request(
    conversation_id: str,
    user_email: Optional[str],
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
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO rag_requests (
            id,
            conversation_id,
            user_email,
            question,
            status,
            error,
            latency_end_to_end,
            latency_retrieval,
            latency_generation,
            latency_grading,
            latency_web_search,
            latency_reranking,
            latency_answer_quality,
            docs_count,
            response_length,
            answer_quality_score,
            answer_quality_scores,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            conversation_id,
            user_email,
            question,
            status,
            error,
            latencies.get("end_to_end"),
            latencies.get("retrieval"),
            latencies.get("generation"),
            latencies.get("grading"),
            latencies.get("web_search"),
            latencies.get("reranking"),
            latencies.get("answer_quality"),
            docs_count,
            response_length,
            answer_quality_score,
            json.dumps(answer_quality_scores) if answer_quality_scores else None,
            _now(),
        ),
    )
    conn.commit()
    conn.close()


def get_metrics_overview() -> Dict:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS total FROM rag_requests")
    total_requests = cur.fetchone()["total"] or 0

    cur.execute("SELECT COUNT(*) AS total FROM rag_requests WHERE status = 'error'")
    total_errors = cur.fetchone()["total"] or 0

    cur.execute("SELECT AVG(latency_end_to_end) AS avg_latency FROM rag_requests")
    avg_latency = cur.fetchone()["avg_latency"] or 0.0

    today = datetime.utcnow().date().isoformat()
    cur.execute(
        "SELECT COUNT(*) AS total FROM rag_requests WHERE substr(created_at, 1, 10) = ?",
        (today,),
    )
    requests_today = cur.fetchone()["total"] or 0

    conn.close()

    success_rate = (
        ((total_requests - total_errors) / total_requests) * 100
        if total_requests > 0
        else 0.0
    )

    return {
        "total_requests": total_requests,
        "requests_today": requests_today,
        "success_rate": success_rate,
        "average_latency": avg_latency,
        "error_count": total_errors,
    }


def get_requests_chart_data(days: int = 7) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            substr(created_at, 1, 10) AS date,
            COUNT(*) AS requests,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success,
            SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS errors
        FROM rag_requests
        GROUP BY substr(created_at, 1, 10)
        ORDER BY date DESC
        LIMIT ?
        """,
        (days,),
    )
    rows = cur.fetchall()
    conn.close()

    result = []
    for row in rows[::-1]:
        date_obj = datetime.fromisoformat(row["date"])
        result.append(
            {
                "date": date_obj.strftime("%d %b"),
                "requests": row["requests"],
                "success": row["success"],
                "errors": row["errors"],
            }
        )

    return result


def get_error_distribution() -> Dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT error FROM rag_requests WHERE status = 'error' AND error IS NOT NULL")
    rows = cur.fetchall()
    conn.close()

    distribution = {
        "timeout": 0,
        "llm_error": 0,
        "retrieval": 0,
        "web_search": 0,
        "other": 0,
    }

    for row in rows:
        error = (row["error"] or "").lower()
        if "timeout" in error:
            distribution["timeout"] += 1
        elif "llm" in error or "generation" in error:
            distribution["llm_error"] += 1
        elif "retrieval" in error or "retrieve" in error:
            distribution["retrieval"] += 1
        elif "web" in error or "search" in error:
            distribution["web_search"] += 1
        else:
            distribution["other"] += 1

    return distribution


def get_recent_requests(limit: int = 10) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, created_at, user_email, question, status, latency_end_to_end
        FROM rag_requests
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()

    formatted = []
    for row in rows:
        question = row["question"] or ""
        formatted.append(
            {
                "id": row["id"],
                "timestamp": row["created_at"],
                "user": row["user_email"] or "unknown",
                "question": question[:50] + "..." if len(question) > 50 else question,
                "status": row["status"],
                "latency": row["latency_end_to_end"] or 0.0,
            }
        )

    return formatted


def get_request_details(limit: int = 50) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, created_at, user_email, question, status, latency_end_to_end, docs_count, answer_quality_score
        FROM rag_requests
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append(
            {
                "id": row["id"],
                "timestamp": row["created_at"],
                "user": row["user_email"] or "unknown",
                "question": row["question"],
                "status": row["status"],
                "latency": row["latency_end_to_end"] or 0.0,
                "docs_count": row["docs_count"] or 0,
                "quality": row["answer_quality_score"] or 0.0,
            }
        )
    return result


def get_latency_component_stats() -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            latency_end_to_end,
            latency_retrieval,
            latency_generation,
            latency_grading,
            latency_web_search
        FROM rag_requests
        WHERE status = 'success'
        """
    )
    rows = cur.fetchall()
    conn.close()

    buckets = {
        "End-to-End": [],
        "Retrieval": [],
        "Generation": [],
        "Grading": [],
        "Web Search": [],
    }

    for row in rows:
        if row["latency_end_to_end"] is not None:
            buckets["End-to-End"].append(row["latency_end_to_end"])
        if row["latency_retrieval"] is not None:
            buckets["Retrieval"].append(row["latency_retrieval"])
        if row["latency_generation"] is not None:
            buckets["Generation"].append(row["latency_generation"])
        if row["latency_grading"] is not None:
            buckets["Grading"].append(row["latency_grading"])
        if row["latency_web_search"] is not None:
            buckets["Web Search"].append(row["latency_web_search"])

    result = []
    for name, values in buckets.items():
        avg = sum(values) / len(values) if values else 0.0
        result.append(
            {
                "name": name,
                "avg": avg,
                "p95": _percentile(values, 0.95),
                "p99": _percentile(values, 0.99),
            }
        )
    return result


def get_latency_trend(days: int = 7) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            substr(created_at, 1, 10) AS date,
            AVG(latency_end_to_end) AS end_to_end,
            AVG(latency_retrieval) AS retrieval,
            AVG(latency_generation) AS generation
        FROM rag_requests
        WHERE status = 'success'
        GROUP BY substr(created_at, 1, 10)
        ORDER BY date DESC
        LIMIT ?
        """,
        (days,),
    )
    rows = cur.fetchall()
    conn.close()

    result = []
    for row in rows[::-1]:
        date_obj = datetime.fromisoformat(row["date"])
        result.append(
            {
                "date": date_obj.strftime("%d %b"),
                "endToEnd": row["end_to_end"] or 0.0,
                "retrieval": row["retrieval"] or 0.0,
                "generation": row["generation"] or 0.0,
            }
        )
    return result


def get_system_status() -> Dict:
    return {
        "rag_pipeline": "Active",
        "vector_db": "Connected",
        "llm_status": "Operational",
        "uptime_percentage": 98.5,
    }
