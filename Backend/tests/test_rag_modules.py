"""L2.4 : le moteur RAG est découpé en modules sans effet de bord à l'import."""

import subprocess
import sys
import textwrap
from pathlib import Path

BACKEND = Path(__file__).parent.parent

HEAVY = ("torch", "sentence_transformers", "chromadb", "transformers", "spacy", "IPython")


def _run(code: str) -> str:
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "JWT_SECRET_KEY": "x" * 40, "HOME": "/tmp"},
        timeout=120,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return result.stdout.strip()


def test_import_has_no_side_effect():
    out = _run(
        f"""
        import sys
        import api.services.chat_service
        import src.rag.Rag_model
        from src.rag.runtime import get_runtime
        from src.rag.graph import get_graph
        heavy = [m for m in {HEAVY!r} if m in sys.modules]
        print(heavy, get_runtime.cache_info().currsize, get_graph.cache_info().currsize)
        """
    )
    assert out == "[] 0 0"


def test_missing_api_keys_do_not_break_import_or_graph_compilation():
    out = _run(
        """
        from src.rag.graph import get_graph
        print(sorted(get_graph().get_graph().nodes))
        """
    )
    for node in ("websearch", "retrieve", "grade_documents", "generate", "grade_answer_quality"):
        assert node in out


def test_legacy_facade_still_exposes_public_names():
    out = _run(
        """
        import src.rag.Rag_model as R
        names = ["get_final_response", "get_final_response_stream", "generate_stream",
                 "extract_sources_from_documents", "format_citations", "format_docs",
                 "get_reranker_instance", "rerank_documents", "Rewrite_query", "GraphState"]
        print(all(hasattr(R, n) for n in names))
        """
    )
    assert out == "True"
