"""L3.1 : outillage d'évaluation (jeu FinanceBench, runner, juge, comparaison)."""

from pathlib import Path

import httpx
import pytest

from evaluation.compare import compare
from evaluation.dataset import load_dataset, normalize_doc_name
from evaluation.judge import Verdict
from evaluation.runner import retrieval_hits, run_evaluation, summarize

SAMPLE = Path(__file__).parent / "fixtures" / "financebench_sample.jsonl"


def test_dataset_loading_and_reproducible_subset():
    examples = load_dataset(SAMPLE)
    assert [e.id for e in examples] == ["fb_001", "fb_002", "fb_003"]
    assert examples[0].evidence_docs == {"3m2018" + "10k"}
    assert examples[0].evidence_pages == {("3m201810k", 60)}
    assert load_dataset(SAMPLE, limit=2, seed=1) == load_dataset(SAMPLE, limit=2, seed=1)
    assert len(load_dataset(SAMPLE, limit=2)) == 2


def test_doc_name_normalization():
    assert normalize_doc_name("3M_2018_10K.pdf") == normalize_doc_name("3m 2018 10k")


def test_retrieval_hits_use_document_and_page():
    example = load_dataset(SAMPLE)[0]
    good = [{"source": "3M_2018_10K.pdf", "metadata": {"page": 60}}]
    wrong_page = [{"source": "3M_2018_10K.pdf", "metadata": {"page": 3}}]
    other_doc = [{"source": "ADOBE_2022_10K.pdf", "metadata": {"page": 60}}]
    assert retrieval_hits(example, good) == (True, True)
    assert retrieval_hits(example, wrong_page) == (True, False)
    assert retrieval_hits(example, other_doc) == (False, False)


class FakeJudge:
    def judge(self, question, reference, answer, contexts):
        return Verdict(correct="1577" in answer, faithful=bool(contexts), rationale="test")


def _fake_api() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/login"):
            return httpx.Response(200, json={"success": True, "token": "t"})
        assert request.headers["authorization"] == "Bearer t"
        question = request.read().decode()
        if "3M" in question:
            return httpx.Response(
                200,
                json={
                    "response": "3M spent $1577 million.",
                    "success": True,
                    "citations": [
                        {
                            "id": 1,
                            "source": "3M_2018_10K.pdf",
                            "excerpt": "PP&E (1,577)",
                            "metadata": {"page": 60},
                        }
                    ],
                },
            )
        if "Adobe" in question:
            return httpx.Response(500, json={"success": False, "error": "boom"})
        return httpx.Response(
            200, json={"response": "Je ne sais pas.", "success": True, "citations": []}
        )

    return httpx.MockTransport(handler)


def test_run_evaluation_end_to_end_with_fake_api():
    report = run_evaluation(
        load_dataset(SAMPLE), "http://api/api/v1", "a@b.c", "pw", FakeJudge(), _fake_api()
    )
    summary = report["summary"]
    by_id = {r["id"]: r for r in report["results"]}
    assert by_id["fb_001"]["correct"] is True and by_id["fb_001"]["retrieval_page_hit"] is True
    assert by_id["fb_002"]["success"] is False
    assert by_id["fb_003"]["correct"] is False and by_id["fb_003"]["faithful"] is False
    assert summary["questions"] == 3
    assert summary["error_rate"] == pytest.approx(1 / 3)
    assert summary["accuracy"] == pytest.approx(1 / 2)  # 2 réponses jugées (l'erreur est exclue)
    assert summary["retrieval_page_hit"] == pytest.approx(1 / 3)


def test_compare_flags_quality_regressions_but_not_latency():
    baseline = {"accuracy": 0.60, "faithfulness": 0.80, "error_rate": 0.0, "latency_mean": 20.0}
    better = {"accuracy": 0.65, "faithfulness": 0.80, "error_rate": 0.0, "latency_mean": 5.0}
    worse = {"accuracy": 0.50, "faithfulness": 0.80, "error_rate": 0.1, "latency_mean": 1.0}
    assert compare(baseline, better)[1] == []
    _, regressions = compare(baseline, worse)
    assert any("Exactitude" in r for r in regressions)
    assert any("erreur" in r for r in regressions)
    assert not any("Latence" in r for r in regressions)


def test_summarize_empty():
    assert summarize([])["questions"] == 0
