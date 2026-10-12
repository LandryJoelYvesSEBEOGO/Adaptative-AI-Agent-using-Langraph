# RAG System

Assistant de question-réponse **sourcé** sur un corpus de documents financiers (rapports 10-K / 10-Q) : recherche hybride (vecteurs + plein texte PostgreSQL, fusion RRF), reranking, génération en streaming avec citations cliquables vers la page du PDF, et repli sur la recherche web quand le corpus ne suffit pas. Interface de chat React et tableau de bord d'administration.

> **Statut** : MVP en cours de mise en production. Voir le [cahier des charges d'améliorations](docs/CAHIER_DES_CHARGES_AMELIORATIONS.md) pour l'avancement par lot.

## Structure du dépôt

```
.
├── Backend/              API FastAPI + pipeline RAG (Python, uv)
│   ├── api/              Routes, modèles Pydantic, services, base de données (SQLAlchemy)
│   ├── alembic/          Migrations de la base
│   ├── config/           Configuration (pydantic-settings)
│   ├── src/rag/          Pipeline : analyse, recherche hybride, rerank, génération (LangGraph)
│   ├── src/ingestion/    Ingestion des PDF : parsing, chunking par sections, métadonnées
│   ├── evaluation/       Évaluation de la qualité (FinanceBench)
│   ├── scripts/          Indexation du corpus, export du schéma OpenAPI
│   └── tests/            Tests (API, base, pipeline, ingestion, recherche, évaluation)
├── Frontend/             React 19 + Vite + Tailwind 4 + TypeScript strict
│   ├── src/api/          Client généré depuis l'OpenAPI, flux SSE, hooks TanStack Query
│   ├── e2e/              Parcours navigateur (Playwright)
│   └── openapi.json      Schéma de l'API (source du client, contrôlé en CI)
├── docs/                 Documentation et cahier des charges
├── docker-compose.yml    api + PostgreSQL/pgvector + frontend (nginx)
└── .github/workflows/    CI (lint, typage, tests, e2e) et évaluation à la demande
```

## Démarrage rapide

### Docker (une commande)

```bash
cp Backend/.env.example Backend/.env   # renseigner GROQ_API_KEY, TAVILY_API_KEY, JWT_SECRET_KEY, ADMIN_*
docker compose up --build
```

Application : http://localhost:8080 — documentation de l'API : http://localhost:8000/docs.

Indexer le corpus (PDF placés dans le volume `ragdata`) ou, plus simplement, les téléverser depuis l'interface d'administration (page *Documents*) :

```bash
docker compose exec api python -m scripts.ingest_corpus data/raw
```

### Développement local

**Prérequis** : Python 3.11+ avec [uv](https://docs.astral.sh/uv/), Node.js 22+, et PostgreSQL avec l'extension pgvector pour la recherche (`docker compose up postgres` suffit).

```bash
# Backend
cd Backend
uv sync
cp .env.example .env        # DATABASE_URL=postgresql+psycopg://rag:rag@localhost:5432/rag, clés, etc.
uv run uvicorn api.main:app --reload

# Frontend (autre terminal) : /api est relayé vers le backend, même origine
cd Frontend
npm install
npm run dev                 # http://localhost:8080
```

Sans `DATABASE_URL`, l'API utilise SQLite (comptes, conversations, métriques) mais la **recherche documentaire exige PostgreSQL + pgvector**.

## Qualité

| Quoi | Commande |
|---|---|
| Backend : lint, format, typage, tests | `cd Backend && uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest` |
| Frontend : typage, lint, tests | `cd Frontend && npm run typecheck && npx eslint . && npm test` |
| Parcours navigateur | `cd Frontend && npm run build && npm run test:e2e` |
| Qualité des réponses (FinanceBench) | voir [Backend/evaluation/README.md](Backend/evaluation/README.md) |

Après toute modification de l'API : `cd Backend && uv run python -m scripts.export_openapi` puis `cd Frontend && npm run api:generate` (la CI vérifie la cohérence).

## Documentation

| Document | Contenu |
|---|---|
| [Cahier des charges d'améliorations](docs/CAHIER_DES_CHARGES_AMELIORATIONS.md) | Audit, stack cible, feuille de route et avancement |
| [Architecture (historique)](docs/architecture.md) | Pipeline *avant* le lot 3 ; l'actuel est dans `Backend/src/rag/pipeline.py` |
