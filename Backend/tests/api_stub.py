"""Environnement de test partagé pour les tests d'API.

`install()` positionne l'environnement minimal et remplace les composants externes du pipeline
(LLM Groq, Tavily, index vectoriel) par des doubles. Le reste du service (routes, auth, base,
graphe LangGraph) est réel. `search_delay` simule une recherche lente et *bloquante* ;
`llm.reply` / `llm.delay` pilotent le faux modèle.
"""

import os
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

state = SimpleNamespace(search_delay=0.0, llm=None, deps=None)


def install() -> SimpleNamespace:
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-" + "x" * 40)
    os.environ.setdefault("RAG_DB_PATH", str(Path(tempfile.mkdtemp()) / "test.db"))
    os.environ.setdefault("ADMIN_EMAIL", "boss@example.com")
    os.environ.setdefault("ADMIN_PASSWORD", "Sup3rS3cret!")

    if state.deps is None:
        from src.rag import pipeline
        from src.rag.search import SearchResult
        from tests.fakes import SlowStreamingLLM, make_deps, retrieved

        state.llm = SlowStreamingLLM(calls=[], delay=0.0)
        deps = make_deps(state.llm)

        def blocking_search(query, filters):
            if state.search_delay:
                time.sleep(state.search_delay)  # appel bloquant, comme un vrai accès base
            return SearchResult([retrieved(1)], 0.9)

        deps.search = blocking_search
        state.deps = deps
        pipeline.get_dependencies = lambda: deps
    return state
