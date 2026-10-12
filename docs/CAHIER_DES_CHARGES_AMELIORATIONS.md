# Cahier des charges d'améliorations

> **Projet** : RAG System (agent RAG adaptatif — FastAPI + LangGraph + React)
> **Objectif** : amener le projet au niveau d'un MVP déployable
> **Date de l'audit** : 12 octobre 2026
> **Branche de travail** : `Improvements`

---

## 1. Contexte

Le projet a été conçu il y a plusieurs mois et s'est enrichi fonctionnalité après fonctionnalité : recherche hybride (vecteurs + BM25), reranker cross-encoder, orchestration LangGraph, grading multi-critères, rotation de clés Groq, dashboard admin. Entre-temps, l'écosystème a évolué (LangChain 1.x, React 19, Tailwind 4, outils de parsing PDF structurés, rerankers hébergés…) et la sécurité, la persistance et l'industrialisation n'ont pas suivi.

**Verdict de l'audit** : le projet n'est pas déployable en l'état. Il ne faut pas tout réécrire, mais **sécuriser, simplifier et industrialiser**.

## 2. Objectifs du MVP

1. Un utilisateur peut se connecter, poser des questions sur le corpus et obtenir une réponse **sourcée** (citations cliquables vers le document et la page), affichée en streaming réel.
2. Les données (utilisateurs, conversations, documents, métriques) sont persistées dans une vraie base avec migrations.
3. L'API est sécurisée (authentification fiable, rôles appliqués côté serveur, isolation des données entre utilisateurs).
4. La qualité des réponses est **mesurée** sur un jeu d'évaluation de référence, et chaque évolution du pipeline est comparée à cette mesure.
5. Le projet se lance en une commande (`docker compose up`) et est vérifié automatiquement en CI.

## 3. Décision produit préalable

> ⚠️ À trancher avant le lot 3.

| Option | Description | Impact |
|---|---|---|
| **A. Corpus fixe** | Assistant d'analyse financière sur un corpus fixe (rapports 10-K / 10-Q, type FinanceBench) | Ingestion par script, pas de multi-tenant, landing page orientée finance |
| **B. Documents utilisateur** | « Chat avec vos documents » : chaque utilisateur importe ses fichiers | Upload, ingestion asynchrone, isolation des documents par utilisateur, quotas |

---

## 4. État des lieux (constats de l'audit)

### 4.1 Sécurité — 🔴 bloquant

| # | Constat | Fichier |
|---|---|---|
| S1 | Une clé Groq (toujours active) et une clé Tavily sont présentes dans l'historique git (commit `1d35ae8`, branches `main` et `Landry-`). | historique git |
| S2 | Le secret JWT n'est jamais chargé : le code lit `JWT_SECRET_KEY`, le `.env` définit `SECRET_KEY`. Les tokens sont signés avec la valeur par défaut publique → n'importe qui peut forger un token admin. | `Backend/api/services/auth_service.py` |
| S3 | Les routes `/api/v1/admin/*` sont publiques (`require_admin` n'est branché nulle part). | `Backend/api/routes/admin.py` |
| S4 | `/auth/register` accepte un `role` fourni par le client → inscription possible en tant qu'admin. | `Backend/api/routes/auth.py` |
| S5 | IDOR : `/chat/query` et `/chat/query/stream` ne vérifient pas que le `conversation_id` appartient à l'utilisateur (écriture dans la conversation d'autrui, fuite de son historique via la réécriture de requête). | `Backend/api/routes/chat.py` |
| S6 | Utilisateurs en mémoire (`MOCK_USERS`, comptes `admin`/`admin`), perdus à chaque redémarrage. | `Backend/api/services/auth_service.py` |
| S7 | Le handler global d'exceptions renvoie `str(exc)` au client. `/chat/feedback` n'est pas authentifié et n'enregistre rien. | `Backend/api/main.py`, `Backend/api/routes/chat.py` |
| S8 | JWT stocké dans `localStorage` côté frontend ; pas de refresh token. | `Frontend/src/services/apiClient.ts` |

### 4.2 Architecture backend — 🟠

| # | Constat |
|---|---|
| B1 | `src/rag/Rag_model.py` fait ~1 940 lignes, avec des effets de bord à l'import (init LLM, Tavily, compilation du graphe) → non testable unitairement. Import d'`IPython` en code de production. |
| B2 | `api/services/metrics_service.py` contient tout son code **en double** (chaque fonction redéfinie à partir de la ligne 363). |
| B3 | Deux systèmes de métriques parallèles : fichiers JSONL (`src/core/metrics.py`) et table SQLite `rag_requests`. |
| B4 | Routes `async def` qui appellent `graph.invoke()` de façon synchrone → **une requête RAG bloque toute l'API** pendant sa durée. |
| B5 | `config/Config.py` : classe à effets de bord (crash au démarrage si `TAVILY_API_KEY` absente, tracing LangSmith forcé), tous les réglages en dur, `pydantic-settings` installé mais inutilisé. |
| B6 | `FORCE_GPU = True` → plantage sur toute machine sans GPU CUDA (la majorité des hébergements). |
| B7 | Persistance éclatée : SQLite brut (connexion par appel, aucune migration), ChromaDB (1,8 Go), pickle BM25 de 233 Mo chargé entièrement en RAM. |
| B8 | `requirement.txt` incomplet (`langgraph` absent), versions mêlant figées / non figées, aucun lockfile. FastAPI 0.104 (fin 2023). |
| B9 | torch, spaCy, BERTopic, KeyBERT, transformers chargés dans le processus de l'API → image énorme, démarrage lent. |
| B10 | Rotation de plusieurs clés Groq pour contourner les rate limits : fragile et probablement contraire aux CGU pour un usage commercial. |
| B11 | `print()` omniprésents en parallèle du logger. |

### 4.3 Pipeline RAG — 🟠

| # | Constat |
|---|---|
| R1 | **Bug fonctionnel** : le prompt du routeur décrit l'ancien corpus (papiers LLM / agents / prompt engineering) alors que `data/raw` contient 368 rapports financiers 10-K / 10-Q → les questions finance partent en recherche web. (`src/rag/Prompts.py`) |
| R2 | **Streaming factice** : `generate_stream` accumule tous les tokens, puis `chat_service` les renvoie d'un bloc à la fin. L'utilisateur attend la génération complète. |
| R3 | **Deux chemins d'exécution divergents** : le mode normal passe par le graphe LangGraph (avec boucles anti-hallucination), le mode streaming réimplémente les étapes à la main sans ces contrôles. |
| R4 | **8 à 9 appels LLM minimum par question** (réécriture, routage, grading de chaque document, génération, score qualité, hallucination, pertinence), jusqu'à ~20 avec les retries. Le grading LLM par document fait doublon avec le reranker. |
| R5 | Ingestion texte seul (`PyPDFLoader`) : les tableaux financiers — l'essentiel de l'information d'un 10-K — sont perdus. Découpage aveugle à 1 000 tokens. |
| R6 | Pas d'ingestion à la demande : indexation uniquement au démarrage si Chroma est absent ; pas d'upload, de réindexation ni de statut par document. |
| R7 | Aucune évaluation chiffrée de la qualité. Le corpus semble issu de **FinanceBench**, qui fournit des questions/réponses annotées réutilisables comme jeu de référence. |
| R8 | Composants dépréciés : `langchain_community.vectorstores.Chroma`, `TavilySearchResults`, parsing JSON manuel (`json.loads`) au lieu de sorties structurées. |

### 4.4 Frontend — 🟠

| # | Constat |
|---|---|
| F1 | Réponses non rendues en Markdown (`whitespace-pre-wrap` dans `Chat.tsx`) : `**`, `##` et tableaux affichés bruts. |
| F2 | Citations visibles uniquement dans un toast ; pas de panneau des sources ni d'aperçu de la page PDF. |
| F3 | Pages admin **factices** (données en dur) : *Users*, *Settings*, *Answer Quality*. |
| F4 | TypeScript non strict (`strict: false`, `noImplicitAny: false`). |
| F5 | Deux clients API qui se recouvrent (`api.ts` 550 lignes + `apiClient.ts`), URL d'API codée en dur dans `api.ts`, appel à un `/auth/refresh` inexistant. |
| F6 | TanStack Query installé mais non utilisé dans le chat (tout en `useState`/`useEffect`). |
| F7 | Pas de bouton Stop / Régénérer / Copier ; feedback non persisté. |
| F8 | Reliquats Lovable : `lovable-tagger`, ~50 composants shadcn dont la plupart inutilisés, image de fond chargée depuis un domaine externe. |
| F9 | Stack en retard : React 18 → 19, Vite 5 → 8, Tailwind 3 → 4, React Router 6 → 7, Zod 3 → 4, Recharts 2 → 3. |

### 4.5 Dépôt et DevOps — 🟡

| # | Constat |
|---|---|
| D1 | Tests non versionnés : la règle `test_*.py` du `.gitignore` excluait les 17 fichiers de test. |
| D2 | 674 Mo de PDF non suivis, sur le point d'être commités. |
| D3 | Ni Docker, ni CI, ni linter Python. |
| D4 | ~20 notes de travail et scripts de debug éparpillés (`AMELIORATIONS_*.md`, `DIAGNOSTIC.md`, `URL_IMPORTANTE.md`, `.bat` de gestion de port, page HTML générée…). |
| D5 | `.env.example` obsolète (Streamlit, audio) ; `VITE_API_BASE_URL` défini dans le `.env` du backend. |

---

## 5. Stack cible

| Couche | Actuel | Cible |
|---|---|---|
| Paquets Python | `requirement.txt` | **uv** + `pyproject.toml` + `uv.lock` |
| API | FastAPI 0.104, routes bloquantes | FastAPI récent, routes **async**, `pydantic-settings` |
| Base de données | SQLite brut + Chroma + pickle BM25 | **PostgreSQL + pgvector** (dense) + full-text Postgres (lexical), fusion RRF — une seule base à opérer. SQLAlchemy 2 + **Alembic** |
| Authentification | Utilisateurs en mémoire | Table `users` + `fastapi-users` (ou service géré type Supabase Auth / Clerk), cookies httpOnly, refresh token |
| Parsing PDF | PyPDFLoader | **Docling** (tableaux conservés) + chunking par sections |
| Embeddings / rerank | Nomic local + cross-encoder dans l'API | API hébergée (Cohere Rerank, embeddings OpenAI / Cohere) ou conteneur TEI séparé — plus de torch dans l'API |
| Orchestration | Graphe à 8–20 appels LLM | Graphe simplifié, sorties structurées Pydantic, un seul chemin d'exécution, vrai streaming |
| Ingestion | Au démarrage | Endpoint d'upload + tâche de fond (arq, ou `BackgroundTasks` au départ) + table `documents` avec statut |
| Observabilité | JSONL maison | **Langfuse** ou LangSmith + table `rag_requests` pour le dashboard |
| Évaluation | Aucune | Jeu FinanceBench + Ragas / DeepEval, exécuté en CI |
| Frontend | React 18 / Vite 5 / Tailwind 3, TS non strict | React 19, Vite récent, Tailwind 4, **TS strict**, TanStack Query pour tout l'état serveur |
| Client API | Deux clients écrits à la main | **Client généré depuis l'OpenAPI** (`openapi-typescript` + `openapi-fetch`, ou orval) |
| Chat UI | Texte brut | `react-markdown` + `remark-gfm` + `rehype-sanitize`, citations au survol, panneau sources avec aperçu PDF (`react-pdf`) |
| Déploiement | Scripts `.bat` | `docker compose` (api, worker, postgres, frontend) + GitHub Actions |

---

## 6. Lots de travaux

Chaque exigence a un identifiant, une description et un critère d'acceptation vérifiable.

### Lot 0 — Structuration du dépôt *(en cours)*

- [x] **L0.1** Supprimer les scripts de debug et notes de travail obsolètes (toujours récupérables via l'historique git).
- [x] **L0.2** Regrouper la documentation dans `docs/` à la racine.
- [x] **L0.3** Regrouper les scripts utilitaires dans `Backend/scripts/`, les tests dans `Backend/tests/`.
- [x] **L0.4** Corriger le `.gitignore` : versionner les tests, ignorer `data/raw/`.
- [x] **L0.5** README racine + README backend et frontend à jour ; `.env.example` alignés sur les variables réellement lues.
- [ ] **L0.6** Commit dédié au nettoyage, séparé du travail en cours.

### Lot 1 — Sécurité *(terminé — clés révoquées et renouvelées ; la purge de l'historique reste à confirmer côté dépôt)*

- [x] **L1.1** Révoquer les clés Groq et Tavily exposées, en générer de nouvelles, purger l'historique (`git filter-repo`) avant tout push. *Acceptation : aucune clé dans `git log -p`.*
- [x] **L1.2** Charger le secret JWT depuis la bonne variable ; refuser de démarrer si absent. *Acceptation : l'API ne démarre pas sans secret.*
- [x] **L1.3** Protéger toutes les routes admin par `require_admin`. *Acceptation : 401/403 sans token admin.*
- [x] **L1.4** Retirer `role` de l'inscription (rôle `user` forcé côté serveur).
- [x] **L1.5** Vérifier la propriété du `conversation_id` sur toutes les routes de chat. *Acceptation : 404 sur la conversation d'un autre utilisateur.*
- [x] **L1.6** Ne plus renvoyer le détail des exceptions au client ; authentifier et persister `/feedback`.
- [x] **L1.7** Corriger le prompt du routeur pour le corpus actuel (R1).

### Lot 2 — Fondations backend *(terminé)*

- [x] **L2.1** Migrer vers uv + `pyproject.toml` ; ajouter ruff et pyright.
- [x] **L2.2** Configuration via `pydantic-settings` (environnements dev / prod, aucune valeur sensible en dur, `FORCE_GPU` supprimé).
- [x] **L2.3** PostgreSQL + SQLAlchemy 2 + Alembic ; tables `users`, `conversations`, `messages`, `rag_requests`, `feedback`, `documents`.
- [x] **L2.4** Découper `Rag_model.py` en modules (`retrieval/`, `generation/`, `grading/`, `graph.py`) sans effet de bord à l'import.
- [x] **L2.5** Routes async ; le travail bloquant sort de la boucle d'événements. *Acceptation : deux requêtes simultanées sont traitées en parallèle.*
- [x] **L2.6** Supprimer le code dupliqué (`metrics_service.py`) et le système de métriques JSONL redondant.
- [x] **L2.7** `docker compose` (api, postgres, frontend) + CI GitHub Actions (lint, typage, tests, build).

### Lot 3 — Qualité du RAG *(code livré ; mesures qualité à exécuter)*

- [~] **L3.1** Établir une **mesure de référence** sur le jeu FinanceBench (exactitude, fidélité, latence, coût) avant toute modification. *Outillage livré (`Backend/evaluation/`) ; la mesure elle-même reste à exécuter avec vos clés et le corpus (voir `Backend/evaluation/README.md`). Le coût en tokens n'est pas mesuré.*
- [x] **L3.2** Ingestion Docling avec conservation des tableaux, chunking par sections, métadonnées (société, année, type de document, page). *Parsing Docling non exécuté ici (modèles non téléchargeables) ; chunking, métadonnées et repli pypdf testés.*
- [x] **L3.3** Recherche hybride pgvector + full-text avec fusion RRF ; reranker hébergé avec seuil de score. *Recherche validée sur PostgreSQL 16 + pgvector ; clients Cohere / OpenAI testés avec HTTP simulé (pas d'appel réel). Le seuil `RERANK_MIN_SCORE` est à calibrer.*
- [x] **L3.4** Graphe simplifié : réécriture (seulement si historique) → recherche hybride → rerank → génération ; recherche web uniquement si les scores de rerank sont sous le seuil. Suppression du grading LLM par document. *Acceptation : ≤ 3 appels LLM par question dans le cas nominal (vérifié : 1 appel, 2 avec historique), score d'évaluation ≥ référence (**non vérifié** : nécessite la mesure L3.1).*
- [x] **L3.5** Vrai streaming token par token via le graphe (`astream` / `stream_mode="messages"`), un seul chemin d'exécution.
- [x] **L3.6** Sorties structurées (Pydantic) pour toutes les étapes qui renvoient du JSON.
- [x] **L3.7** Endpoint d'upload + ingestion asynchrone + statut par document *(si option B retenue)*. *Réalisé de façon neutre vis-à-vis de la décision produit : upload réservé aux administrateurs (corpus partagé), `owner_id` conservé pour l'option B ; CLI `scripts/ingest_corpus.py` pour l'option A. Tâche de fond FastAPI (`BackgroundTasks`), pas encore arq.*
- [x] **L3.8** Évaluation automatique en CI sur un sous-ensemble du jeu de référence. *Garde-fou de retrieval à chaque PR (testé, y compris par mutation) ; workflow d'évaluation complète lancé à la demande (YAML validé, **jamais exécuté** : nécessite vos secrets).*

### Lot 4 — Frontend *(terminé)*

- [x] **L4.1** Mise à jour React 19, Vite, Tailwind 4, React Router 7 ; TypeScript strict. *Montées : React 19.3, Vite 8.3, Tailwind 4.3, React Router 7.18, Recharts 3.10, TypeScript 5.9 strict ; rendu comparé avant/après par captures (écarts : ombres personnalisées et interlignage des titres, désormais conformes au code).*
- [x] **L4.2** Client API généré depuis l'OpenAPI ; suppression des deux clients manuels. *`openapi-typescript` + `openapi-fetch`, schéma versionné et contrôlé en CI ; renouvellement transparent de session ; flux SSE typé à la main (hors OpenAPI).*
- [x] **L4.3** TanStack Query pour tout l'état serveur. *Session, conversations, messages, avis (mise à jour optimiste) et pages d'administration ; le flux de génération reste un état local par nature.*
- [x] **L4.4** Rendu Markdown sécurisé des réponses (tableaux, code). *`react-markdown` + `remark-gfm` + `rehype-sanitize` ; scripts, `onerror` et liens `javascript:` neutralisés (testés) ; renvois `[n]` rendus en badges.*
- [x] **L4.5** Citations au survol + panneau des sources avec aperçu de la page PDF. *Vérifié en navigateur sur un vrai PDF servi par l'API (pdf.js « legacy », worker local) ; aucune capture sur un vrai 10-K.*
- [x] **L4.6** Boutons Stop (annulation côté serveur), Régénérer, Copier ; feedback persisté. *Vérifié en navigateur : arrêt (réponse partielle conservée et marquée), régénération sans doublon, avis conservé après rechargement.*
- [x] **L4.7** Pages admin réelles (Documents, Utilisateurs) ; suppression ou masquage des pages factices. *Pages « Qualité » et « Paramètres » (données en dur) supprimées ; état du système désormais calculé (base, documents indexés, clé LLM, taux de réussite 24 h) au lieu de valeurs fixes.*
- [x] **L4.8** Suppression des reliquats Lovable et des composants shadcn inutilisés ; auth par cookie httpOnly. *Jeton jamais stocké côté navigateur (plus de `localStorage`), refresh à rotation, contrôle CSRF.*

### Lot 5 — Mise en production

- [x] **L5.1** Déploiement (front statique + API conteneurisée + Postgres managé). *`docker-compose.prod.yml` + Caddy (HTTPS), API non-root, guide `docs/DEPLOIEMENT.md` (VPS ou front statique + base managée). Rien n'a été exécuté (pas de Docker ici) : YAML validé seulement.*
- [x] **L5.2** Rate limiting et quotas par utilisateur. *Fenêtre glissante en mémoire par processus (voir limites dans `api/ratelimit.py`) ; quota quotidien compté en base, donc global.*
- [x] **L5.3** Observabilité (Langfuse / LangSmith, logs structurés, alertes de latence et d'erreurs). *Logs JSON + identifiant de requête, callback Langfuse (testé avec un faux paquet : le paquet réel n'a pas été exécuté), LangSmith par variables d'environnement, alertes journalisées + webhook (non envoyé à un vrai service) et visibles sur le dashboard.*
- [x] **L5.4** Sauvegardes de la base, rotation des secrets. *Scripts `backup_db.sh` / `restore_db.sh` / `verify_backup.sh` testés sur PostgreSQL 16 (sauvegarde, restauration, vérification) ; service Compose `backup` (profil) non lancé faute de Docker ; rotation du JWT sans déconnexion (`JWT_SECRET_KEY_PREVIOUS`) ; procédures dans `docs/EXPLOITATION.md`.*
- [ ] **L5.5** Pages légales (mentions, confidentialité).

---

## 7. Planning indicatif

| Lot | Durée estimée | Dépendances |
|---|---|---|
| 0 — Structuration | 0,5 jour | — |
| 1 — Sécurité | 1–2 jours | Lot 0 |
| 2 — Fondations backend | ~1 semaine | Lot 1 |
| 3 — Qualité RAG | 1–2 semaines | Lot 2 + décision produit (§3) |
| 4 — Frontend | ~1 semaine | Lot 2 (client OpenAPI) ; parallélisable avec le lot 3 |
| 5 — Production | ~1 semaine | Lots 3 et 4 |
