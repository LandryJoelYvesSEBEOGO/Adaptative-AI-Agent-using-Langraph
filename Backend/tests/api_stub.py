"""Environnement de test partagé pour les tests d'API (sans moteur RAG réel).

Le moteur RAG (LLM Groq, Tavily, index vectoriel) n'est pas disponible en test unitaire :
`install()` positionne l'environnement minimal et remplace `api.services.chat_service` par un
faux module. Les tests partagent la même instance (un seul `api.main` par processus pytest) ;
`rag_delay` permet de simuler un appel LLM lent et bloquant.
"""

import os
import sys
import tempfile
import time
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

fake = types.ModuleType("api.services.chat_service")
fake.rag_delay = 0.0


def _answer(**kwargs):
    if fake.rag_delay:
        time.sleep(fake.rag_delay)
    return {
        "response": "ok",
        "citations": [],
        "success": True,
        "conversation_id": kwargs["conversation_id"],
    }


fake.process_rag_query = _answer
fake.process_rag_query_stream = lambda **kw: iter(["ok"])


def install() -> types.ModuleType:
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-" + "x" * 40)
    os.environ.setdefault("RAG_DB_PATH", str(Path(tempfile.mkdtemp()) / "test.db"))
    os.environ.setdefault("ADMIN_EMAIL", "boss@example.com")
    os.environ.setdefault("ADMIN_PASSWORD", "Sup3rS3cret!")
    sys.modules.setdefault("api.services.chat_service", fake)
    return fake
