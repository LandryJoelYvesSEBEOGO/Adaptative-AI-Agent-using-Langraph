# Backend — RAG System API

API FastAPI exposant le pipeline RAG (LangGraph), l'authentification, l'historique des conversations et les métriques d'administration.

## Installation

```bash
uv sync                # crée .venv et installe les dépendances figées (uv.lock)
cp .env.example .env
```

Qualité du code : `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest`.

Renseigner au minimum `GROQ_API_KEY`, `JWT_SECRET_KEY` et, pour la recherche, `DATABASE_URL` (PostgreSQL + pgvector) dans `.env` ; `TAVILY_API_KEY` active le repli web ; `ADMIN_EMAIL` / `ADMIN_PASSWORD` créent le premier administrateur (voir `.env.example`).

## Lancement

```bash
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
| `api/routes/` | Endpoints : `auth` (cookies de session), `chat` (requête, streaming SSE, feedback), `conversation`, `documents`, `admin` |
| `api/services/` | Logique métier appelée par les routes |
| `api/models/` | Schémas Pydantic des requêtes et réponses |
| `api/database.py`, `api/db_models.py`, `alembic/` | SQLAlchemy 2 (PostgreSQL ou SQLite) et migrations Alembic |
| `config/settings.py` | Configuration (pydantic-settings) : tout se règle par variable d'environnement ou `.env` |
| `src/rag/` | Pipeline RAG : `pipeline.py` (graphe LangGraph `analyze → retrieve → web_search → generate`, normal et streaming), `store.py` (pgvector + plein texte, fusion RRF), `embeddings.py`, `rerankers.py`, `search.py`, `query_analysis.py` |
| `src/ingestion/` | Ingestion des PDF : parsing Docling, chunking par sections, métadonnées |
| `scripts/ingest_corpus.py` | Indexe un dossier de PDF : `uv run python -m scripts.ingest_corpus data/raw` |
| `evaluation/` | Évaluation FinanceBench (voir `evaluation/README.md`) |
| `scripts/` | `ingest_corpus` (indexation d'un dossier), `export_openapi` (schéma pour le client TypeScript) |
| `tests/` | Tests ; `tests/e2e_server.py` sert les parcours navigateur (vraie API, LLM simulé) |
| `data/` | Données locales : PDF (`raw/`, `uploads/`), base SQLite de repli, logs |

## Base de données

PostgreSQL + pgvector en production (`DATABASE_URL`), migrations Alembic appliquées au démarrage (`AUTO_MIGRATE`) :

```bash
uv run alembic upgrade head      # ou le faire à la main
uv run alembic revision --autogenerate -m "description"   # après modification de api/db_models.py
```

## Tests

```bash
uv run pytest                    # SQLite (la recherche vectorielle et l'ingestion sont ignorées)
DATABASE_URL=postgresql+psycopg://rag:rag@localhost:5432/rag RAG_TEST_RESET_DB=1 uv run pytest
```

`RAG_TEST_RESET_DB=1` vide le schéma PostgreSQL avant les tests : **base jetable uniquement**. Les tests n'appellent aucune API externe (LLM, Tavily, embeddings simulés).
