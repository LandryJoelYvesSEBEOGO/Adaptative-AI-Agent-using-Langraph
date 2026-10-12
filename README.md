# RAG System

Agent de question-réponse à génération augmentée par récupération (RAG) : recherche hybride (vecteurs + BM25), reranking cross-encoder, orchestration LangGraph et repli sur la recherche web. Interface de chat React et tableau de bord d'administration.

> **Statut** : en cours de mise à niveau vers un MVP. Voir le [cahier des charges d'améliorations](docs/CAHIER_DES_CHARGES_AMELIORATIONS.md).

## Structure du dépôt

```
.
├── Backend/              API FastAPI + pipeline RAG (Python)
│   ├── api/              Application FastAPI : routes, modèles, services, accès base
│   ├── config/           Configuration (Config.py)
│   ├── src/
│   │   ├── core/         Briques transverses : logs, métriques, retry, fallback, clés Groq
│   │   └── rag/          Pipeline RAG : ingestion, prompts, graphe LangGraph
│   ├── scripts/          Scripts utilitaires (reconstruction d'index, métriques, GPU)
│   ├── tests/            Tests
│   ├── data/             Données locales (non versionnées sauf few_shot_examples.json)
│   └── run_api.py        Point d'entrée de l'API
├── Frontend/             Application React (Vite + TypeScript + Tailwind + shadcn/ui)
└── docs/                 Documentation du projet
```

## Démarrage rapide

**Prérequis** : Python 3.11+, Node.js 20+.

### 1. Backend

```bash
cd Backend
uv sync
cp .env.example .env        # puis renseigner les clés
uv run python run_api.py
```

L'API écoute sur http://127.0.0.1:8000 (documentation interactive : `/docs`).

### 2. Frontend

```bash
cd Frontend
npm install
cp .env.example .env.local
npm run dev
```

L'application est servie sur http://localhost:8080.

### 3. Données

Placer les PDF à indexer dans `Backend/data/raw/` (dossier non versionné), puis construire l'index :

```bash
cd Backend
python scripts/rebuild_index.py
```

## Documentation

| Document | Contenu |
|---|---|
| [Cahier des charges d'améliorations](docs/CAHIER_DES_CHARGES_AMELIORATIONS.md) | Audit, stack cible et feuille de route vers le MVP |
| [Architecture](docs/architecture.md) | Architecture détaillée du pipeline RAG et des métriques |
| [Rotation des clés Groq](docs/rotation-cles-groq.md) | Fonctionnement du gestionnaire de clés |
| [Modèles de métadonnées](docs/installation-modeles-metadonnees.md) | Installation des modèles locaux (spaCy, KeyBERT…) |
