# Backend — RAG System API

API FastAPI exposant le pipeline RAG (LangGraph), l'authentification, l'historique des conversations et les métriques d'administration.

## Installation

```bash
uv sync                # crée .venv et installe les dépendances figées (uv.lock)
cp .env.example .env
```

Qualité du code : `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest`.

Renseigner au minimum `GROQ_API_KEY`, `TAVILY_API_KEY` et `JWT_SECRET_KEY` dans `.env` (voir `.env.example`).

## Lancement

```bash
uv run python run_api.py
# ou
uv run uvicorn api.main:app --reload --port 8000
```

| URL | Rôle |
|---|---|
| http://127.0.0.1:8000/health | Health check |
| http://127.0.0.1:8000/docs | Documentation Swagger |
| http://127.0.0.1:8000/redoc | Documentation ReDoc |

## Organisation

| Dossier | Contenu |
|---|---|
| `api/routes/` | Endpoints : `auth`, `chat` (requête, streaming SSE, feedback), `conversation`, `admin` |
| `api/services/` | Logique métier appelée par les routes |
| `api/models/` | Schémas Pydantic des requêtes et réponses |
| `api/database.py`, `api/db_models.py`, `alembic/` | SQLAlchemy 2 (PostgreSQL ou SQLite) et migrations Alembic |
| `config/Config.py` | Paramètres du pipeline (modèles, reranker, hybrid search, grading…) |
| `src/rag/` | Ingestion (`Data_processing.py`), prompts, et moteur RAG découpé : `retrieval/`, `generation/`, `grading/`, `routing.py`, `graph.py` (LangGraph), `answer.py` ; `Rag_model.py` reste une façade de compatibilité |
| `src/core/` | Logs, métriques, retry / circuit breaker, fallback, rotation des clés Groq |
| `scripts/` | Utilitaires lancés à la main |
| `tests/` | Tests |
| `data/` | Données locales : PDF sources (`raw/`), index Chroma, cache BM25, base SQLite, logs |

## Scripts

```bash
python scripts/rebuild_index.py   # Reconstruit l'index Chroma et le cache BM25 depuis data/raw/
python scripts/check_gpu.py       # Vérifie la disponibilité de CUDA
```

## Tests

```bash
pytest tests/
```

Certains tests appellent les API externes (Groq, Tavily) ou nécessitent l'index local.
