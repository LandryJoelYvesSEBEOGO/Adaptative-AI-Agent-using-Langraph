"""Exécute le jeu de questions contre l'API et note chaque réponse."""

import statistics
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import httpx

from evaluation.dataset import Example, normalize_doc_name
from evaluation.judge import Judge


@dataclass
class Result:
    id: str
    question: str
    reference_answer: str
    answer: str = ""
    success: bool = True
    error: str | None = None
    latency: float = 0.0
    sources: list[str] = field(default_factory=list)
    retrieval_doc_hit: bool = False
    retrieval_page_hit: bool = False
    correct: bool | None = None
    faithful: bool | None = None
    rationale: str = ""


def login(client: httpx.Client, email: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    body = response.json()
    if not body.get("success"):
        raise RuntimeError(f"Connexion impossible : {body.get('error')}")
    return {"Authorization": f"Bearer {body['token']}"}


def retrieval_hits(example: Example, citations: list[dict]) -> tuple[bool, bool]:
    """Le document (et la page) annotés comme preuve figurent-ils parmi les citations ?"""
    cited_docs = {normalize_doc_name(c.get("source", "")) for c in citations}
    cited_pages = {
        (normalize_doc_name(c.get("source", "")), int((c.get("metadata") or {}).get("page", -1)))
        for c in citations
    }
    doc_hit = bool(example.evidence_docs & cited_docs)
    page_hit = bool(example.evidence_pages & cited_pages)
    return doc_hit, page_hit


def evaluate_example(
    client: httpx.Client, headers: dict[str, str], example: Example, judge: Judge | None
) -> Result:
    result = Result(example.id, example.question, example.reference_answer)
    started = time.perf_counter()
    try:
        response = client.post(
            "/chat/query", json={"question": example.question}, headers=headers, timeout=180
        )
        body: dict[str, Any] = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        result.success, result.error = False, f"{type(exc).__name__}: {exc}"
        result.latency = time.perf_counter() - started
        return result
    result.latency = time.perf_counter() - started

    result.answer = body.get("response", "") or ""
    result.success = bool(body.get("success", response.is_success)) and response.is_success
    result.error = body.get("error")
    citations = body.get("citations") or []
    result.sources = sorted({c.get("source", "") for c in citations})
    result.retrieval_doc_hit, result.retrieval_page_hit = retrieval_hits(example, citations)

    if judge is not None and result.success:
        verdict = judge.judge(
            example.question,
            example.reference_answer,
            result.answer,
            [c.get("excerpt", "") for c in citations],
        )
        result.correct, result.faithful, result.rationale = (
            verdict.correct,
            verdict.faithful,
            verdict.rationale,
        )
    return result


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(int(len(ordered) * pct), len(ordered) - 1)]


def summarize(results: list[Result]) -> dict[str, Any]:
    total = len(results)
    judged = [r for r in results if r.correct is not None]
    latencies = [r.latency for r in results if r.success]

    def rate(flags: list[bool]) -> float | None:
        return sum(flags) / len(flags) if flags else None

    return {
        "questions": total,
        "error_rate": rate([not r.success for r in results]),
        "accuracy": rate([bool(r.correct) for r in judged]),
        "faithfulness": rate([bool(r.faithful) for r in judged]),
        "retrieval_doc_hit": rate([r.retrieval_doc_hit for r in results]),
        "retrieval_page_hit": rate([r.retrieval_page_hit for r in results]),
        "latency_mean": statistics.fmean(latencies) if latencies else None,
        "latency_p95": _percentile(latencies, 0.95) if latencies else None,
    }


def run_evaluation(
    examples: list[Example],
    base_url: str,
    email: str,
    password: str,
    judge: Judge | None,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    with httpx.Client(base_url=base_url, transport=transport, timeout=60) as client:
        headers = login(client, email, password)
        results = [evaluate_example(client, headers, ex, judge) for ex in examples]
    return {"summary": summarize(results), "results": [asdict(r) for r in results]}
