# Architecture Détaillée du Système RAG avec Métriques Admin

## Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture Générale](#architecture-générale)
3. [Composants Principaux](#composants-principaux)
4. [Workflow LangGraph](#workflow-langgraph)
5. [Pipeline de Traitement des Documents](#pipeline-de-traitement-des-documents)
6. [Système de Métriques](#système-de-métriques)
7. [Métriques Admin - Calcul et Extraction](#métriques-admin---calcul-et-extraction)
8. [Métriques de Retrieval](#métriques-de-retrieval)
9. [Stockage et Persistance](#stockage-et-persistance)
10. [APIs Admin](#apis-admin)

---

## 1. Vue d'ensemble

Le système RAG (Retrieval-Augmented Generation) est un agent intelligent qui combine plusieurs technologies pour fournir des réponses précises et contextuelles basées sur une base de connaissances.

### Technologies Utilisées

- **LangGraph** : Orchestration du workflow adaptatif avec graphe d'états
- **Groq API** : Modèle de langage pour la génération (LLaMA 3 / GPT-OSS-120B)
- **ChromaDB** : Base de données vectorielle pour la recherche sémantique
- **Nomic Embeddings** : Modèle d'embedding pour la représentation vectorielle
- **Tavily** : Recherche web pour les informations récentes
- **Cross-Encoder (Reranker)** : Modèle pour reranker les documents récupérés
- **FastAPI** : API REST pour l'exposition des services
- **FastAPI + React** : Interface utilisateur web

### Caractéristiques Principales

- **Adaptatif** : Décide automatiquement si utiliser la base vectorielle ou la recherche web
- **Reranking** : Améliore la pertinence des documents récupérés
- **Multi-critères** : Évaluation de qualité des documents et réponses
- **Streaming** : Génération de réponse en temps réel
- **Métriques complètes** : Suivi détaillé de toutes les opérations
- **Fallback automatique** : Rotation des clés API et modèles de secours

---

## 2. Architecture Générale

### Architecture en Couches

```
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE PRÉSENTATION                       │
│              (Frontend React + FastAPI)                      │
│  - Interface utilisateur web                                │
│  - Dashboard admin                                          │
│  - Gestion des interactions chat                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    COUCHE API                                │
│              (api/routes/*.py)                               │
│  - Routes chat (/api/v1/chat)                               │
│  - Routes admin (/api/v1/admin)                             │
│  - Routes auth (/api/v1/auth)                               │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    COUCHE SERVICES                           │
│              (api/services/*.py)                              │
│  - chat_service.py : Traitement des requêtes RAG            │
│  - metrics_service.py : Calcul des métriques admin          │
│  - auth_service.py : Authentification                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    COUCHE ORCHESTRATION                       │
│              (src/rag/Rag_model.py - LangGraph)              │
│  - Workflow LangGraph avec graphe d'états                    │
│  - Gestion des états                                         │
│  - Routing intelligent                                       │
│  - Validation et grading                                     │
└───────────────┬────────────────────────────┬─────────────────┘
                │                            │
┌───────────────▼────────────┐  ┌───────────▼─────────────────┐
│   COUCHE RETRIEVAL          │  │   COUCHE GÉNÉRATION          │
│  (src/rag/Data_processing) │  │   (Groq API)                 │
│  - Chargement documents    │  │   - Génération de réponse    │
│  - Embeddings               │  │   - Réécriture de requête   │
│  - Base vectorielle ChromaDB│  │   - Évaluation de qualité   │
│  - Hybrid Search (Vector+BM25)│ │   - Streaming              │
│  - Reranking (Cross-Encoder)│  │                             │
└─────────────────────────────┘  └─────────────────────────────┘
                │                            │
                └────────────┬───────────────┘
                             │
                ┌────────────▼──────────────┐
                │   COUCHE MÉTRIQUES         │
                │   (src/core/metrics.py)   │
                │   - Collecte métriques    │
                │   - Stockage JSONL        │
                │   - Calcul statistiques   │
                └───────────────────────────┘
                             │
                ┌────────────▼──────────────┐
                │   COUCHE CONFIGURATION     │
                │   (config/Config.py)      │
                │   - Variables d'env        │
                │   - Clés API               │
                │   - Configuration modèles  │
                └───────────────────────────┘
```

---

## 3. Composants Principaux

### 3.1 Couche API (FastAPI)

#### Routes Chat (`api/routes/chat.py`)
- **POST `/api/v1/chat`** : Traitement d'une question RAG
- **POST `/api/v1/chat/stream`** : Traitement avec streaming

#### Routes Admin (`api/routes/admin.py`)
- **GET `/api/v1/admin/metrics/overview`** : Aperçu des métriques
- **GET `/api/v1/admin/metrics/requests`** : Données pour graphiques
- **GET `/api/v1/admin/metrics/recent`** : Requêtes récentes
- **GET `/api/v1/admin/metrics/errors`** : Répartition des erreurs
- **GET `/api/v1/admin/system/status`** : Statut du système

### 3.2 Couche Services

#### `api/services/chat_service.py`
Fonctions principales :
- `process_rag_query()` : Traite une question et retourne la réponse avec citations
- `process_rag_query_stream()` : Version streaming
- `extract_citations()` : Extrait les citations de la réponse

#### `api/services/metrics_service.py`
Fonctions principales :
- `get_metrics_overview()` : Calcule l'aperçu des métriques
- `get_requests_chart_data()` : Données pour graphiques temporels
- `get_error_distribution()` : Répartition des erreurs
- `get_recent_requests()` : Requêtes récentes formatées
- `get_system_status()` : Statut du système

### 3.3 Couche Orchestration (LangGraph)

#### `src/rag/Rag_model.py`

**GraphState** (TypedDict) :
```python
{
    "question": str,                    # Question réécrite
    "generation": str,                  # Réponse générée
    "web_search": str,                  # "Yes" ou "No"
    "max_retries": int,                 # Limite de tentatives
    "answers": int,                     # Non utilisé
    "loop_step": int,                   # Compteur d'itérations
    "documents": List[Document],         # Documents récupérés
    "error_history": List[str],         # Historique des erreurs
    "conversation_id": str,             # ID de conversation
    "latencies": Dict[str, float],      # Latences par étape
    "answer_quality_scores": Dict       # Scores de qualité
}
```

**Nœuds du graphe** :
1. `route_question()` : Décide vectorstore ou websearch
2. `retrieve()` : Récupère documents depuis ChromaDB
3. `grade_documents()` : Évalue pertinence des documents
4. `web_search()` : Recherche web via Tavily
5. `generate()` : Génère la réponse avec LLM
6. `grade_answer_quality()` : Évalue qualité de la réponse
7. `grade_generation_v_documents_and_question()` : Validation finale

**Fonctions de routing** :
- `decide_to_generate()` : Décide si générer ou ajouter web search
- `grade_generation_v_documents_and_question()` : Validation avec retry

### 3.4 Couche Retrieval

#### `src/rag/Data_processing.py`

**Fonctions principales** :
- `load_web_documents()` : Charge documents depuis URLs
- `load_pdf_documents()` : Charge documents PDF
- `split_documents()` : Segmente en chunks (1000 tokens, overlap 200)
- `enrich_document_metadata()` : Enrichit métadonnées (keywords, entities, topics)
- `get_or_create_chroma_db()` : Gère ChromaDB
- `get_retriever()` : Crée retriever (vectoriel ou hybride)

**Hybrid Search** :
- Combine recherche vectorielle (ChromaDB) et BM25
- Poids configurables (par défaut: 70% vector, 30% BM25)

**Reranking** :
- Utilise Cross-Encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`)
- Rerank les top-k documents récupérés (par défaut: top-20 → top-3)

---

## 4. Workflow LangGraph

### Flux Complet

```
                    ┌─────────────┐
                    │   QUERY     │
                    │  (Question) │
                    └──────┬──────┘
                           │
                    ┌──────▼──────────────┐
                    │  Rewrite_query()    │
                    │  (Réécriture)       │
                    └──────┬──────────────┘
                           │
                    ┌──────▼──────────────────────┐
                    │   route_question()           │
                    │   (Routing initial)         │
                    └──────┬──────────────────────┘
                           │
            ┌──────────────┴──────────────┐
            │                             │
    ┌───────▼───────┐          ┌─────────▼──────────┐
    │  websearch    │          │    retrieve        │
    │  (Tavily)     │          │  (ChromaDB)        │
    └───────┬───────┘          └─────────┬──────────┘
            │                            │
            │                    ┌───────▼──────────────┐
            │                    │  grade_documents     │
            │                    │  (Évaluation docs)   │
            │                    └───────┬──────────────┘
            │                            │
            │              ┌─────────────┴─────────────┐
            │              │                           │
    ┌───────▼──────────────▼──────────┐      ┌────────▼────────┐
    │   decide_to_generate()          │      │  (Retour web    │
    │   (Si docs non pertinents)      │      │   search)       │
    └───────┬──────────────────────────┘      └─────────────────┘
            │
    ┌───────▼────────┐
    │    generate    │
    │  (Génération)  │
    └───────┬────────┘
            │
    ┌───────▼──────────────────────────────────┐
    │ grade_answer_quality()                   │
    │ (Scoring qualité réponse)                 │
    └───────┬──────────────────────────────────┘
            │
    ┌───────▼──────────────────────────────────┐
    │ grade_generation_v_documents_and_question│
    │ (Validation réponse)                      │
    └───────┬──────────────────────────────────┘
            │
    ┌───────┴────────────────────────────────────┐
    │                                            │
    ├─ "useful" → END (Réponse finale)          │
    ├─ "not useful" → websearch (recherche web) │
    ├─ "not supported" → generate (retry)       │
    └─ "max retries" → END (limite atteinte)    │
```

### Détails des Étapes

#### Étape 1 : Réécriture de la requête (`Rewrite_query`)
- **Objectif** : Améliorer clarté et précision
- **Processus** : LLM avec `Rewritting_prompt`
- **Résultat** : Requête optimisée

#### Étape 2 : Routing initial (`route_question`)
- **Objectif** : Décider vectorstore ou websearch
- **Critères** :
  - **Vectorstore** : Questions sur contenu indexé (agents, prompt engineering, LLMs)
  - **Websearch** : Événements récents, informations non indexées
- **Processus** : LLM en mode JSON analyse la question
- **Résultat** : `"vectorstore"` ou `"websearch"`

#### Étape 3A : Récupération vectorielle (`retrieve`)
- **Objectif** : Trouver documents pertinents dans ChromaDB
- **Processus** :
  1. Convertit question en embedding (Nomic Embeddings)
  2. Recherche k documents (par défaut k=20 si reranker activé)
  3. **Reranking** : Si activé, rerank avec Cross-Encoder (top-20 → top-3)
  4. Retourne liste de documents
- **Métriques enregistrées** :
  - Latence retrieval
  - Latence reranking
  - Nombre de documents récupérés
  - IDs des documents récupérés (pour métriques retrieval)

#### Étape 3B : Recherche web (`web_search`)
- **Objectif** : Obtenir informations récentes depuis web
- **Processus** :
  1. Utilise TavilySearchResults (k=3 résultats)
  2. Combine résultats en un document
  3. Ajoute au contexte existant si documents déjà récupérés
- **Métriques enregistrées** :
  - Latence web_search

#### Étape 4 : Évaluation des documents (`grade_documents`)
- **Objectif** : Filtrer documents non pertinents
- **Processus** :
  - **Multi-critères** (si activé) :
    - Score de pertinence (relevance)
    - Score de couverture (coverage)
    - Score de fraîcheur (freshness)
    - Score d'autorité (authority)
    - Score de clarté (clarity)
    - Score pondéré global
    - Seuil adaptatif (moyenne des scores * 0.8)
  - **Binaire** (fallback) :
    - Évaluation yes/no par document
- **Résultat** : Documents filtrés + flag `web_search = "Yes"` si non pertinents
- **Métriques enregistrées** :
  - Latence grading
  - Nombre de documents filtrés
  - Scores moyens

#### Étape 5 : Décision de génération (`decide_to_generate`)
- **Objectif** : Décider si générer directement ou ajouter web search
- **Processus** : Si `web_search == "Yes"` → route vers web_search, sinon → generate

#### Étape 6 : Génération de réponse (`generate`)
- **Objectif** : Générer réponse basée sur documents récupérés
- **Processus** :
  1. Formate documents (avec ou sans citations)
  2. Construit prompt RAG avec contexte et question
  3. Appelle LLM (Groq) pour générer réponse
  4. Traite citations si activées
  5. Incrémente `loop_step`
- **Métriques enregistrées** :
  - Latence generation
  - Longueur de la réponse
  - Citations extraites

#### Étape 7 : Évaluation qualité réponse (`grade_answer_quality`)
- **Objectif** : Évaluer qualité de la réponse sur 5 critères
- **Critères** :
  - **Relevance** (30%) : Pertinence par rapport à la question
  - **Completeness** (25%) : Complétude de la réponse
  - **Conciseness** (15%) : Concision
  - **Accuracy** (20%) : Exactitude
  - **Coherence** (10%) : Cohérence
- **Processus** : LLM en mode JSON évalue chaque critère
- **Résultat** : Scores détaillés + score global pondéré
- **Métriques enregistrées** :
  - Latence answer_quality
  - Scores détaillés (relevance, completeness, conciseness, accuracy, coherence)
  - Score global

#### Étape 8 : Validation finale (`grade_generation_v_documents_and_question`)
- **Objectif** : Vérifier qualité finale de la réponse
- **Double vérification** :
  - **Hallucination** : Réponse basée sur les faits (grounded)
  - **Utilité** : Réponse répond à la question
- **Décisions** :
  - `"useful"` → Réponse acceptée → END
  - `"not useful"` → Réponse insuffisante → web_search
  - `"not supported"` → Hallucination détectée → generate (retry)
  - `"max retries"` → Limite atteinte → END

---

## 5. Pipeline de Traitement des Documents

### Phase d'Indexation (Première Exécution)

#### 1. Chargement des Sources
- **Documents web** : URLs configurées dans `urls` (Data_processing.py)
- **PDFs** : Automatiquement depuis `data/raw/`

#### 2. Segmentation
- **Chunk size** : 1000 tokens
- **Overlap** : 200 tokens
- **Tokenizer** : tiktoken (comptage précis)
- **Filtrage** : Chunks vides ou < 10 caractères ignorés

#### 3. Enrichissement Métadonnées
- **Structurelles** (par chunk) :
  - `chunk_id` : UUID unique
  - `parent_doc_id` : UUID du document parent
  - `chunk_index` : Index dans le document
  - `total_chunks` : Nombre total de chunks
  - `source` : Source du document (URL ou chemin)
  - `title` : Titre du document
  - `page` : Numéro de page (pour PDFs)
- **Sémantiques** (par document parent, héritées par chunks) :
  - `keywords` : Mots-clés importants
  - `entities` : Entités nommées
  - `topics` : Sujets principaux
  - `summary` : Résumé du document
- **Optimisation** : Métadonnées sémantiques calculées 1x par document (pas par chunk)

#### 4. Embedding
- **Modèle** : `nomic-embed-text-v1.5`
- **Mode** : local (inference_mode="local")
- **Device** : CUDA si disponible, sinon CPU

#### 5. Stockage
- **Base** : ChromaDB
- **Persistance** : `data/chroma_db/`
- **Index** : Automatique par ChromaDB

### Phase de Recherche (À Chaque Requête)

#### 1. Question → Embedding
- Conversion de la question en vecteur avec Nomic Embeddings

#### 2. Recherche Vectorielle
- Recherche des k documents les plus similaires
- Si reranker activé : k=20 initialement

#### 3. Reranking (Si Activé)
- Cross-Encoder calcule scores de pertinence
- Sélection des top-k finaux (par défaut: top-3)

#### 4. Retour
- Liste de Documents avec scores de similarité

---

## 6. Système de Métriques

### Architecture des Métriques

Le système de métriques est composé de plusieurs collecteurs :

1. **MetricsCollector** (`src/core/metrics.py`) : Métriques générales
2. **RetrievalMetricsCollector** (`src/core/retrieval_metrics.py`) : Métriques de retrieval
3. **MetricsService** (`api/services/metrics_service.py`) : Calcul des métriques admin

### Collecte des Métriques

#### Point d'Enregistrement Principal

Dans `Rag_model.py`, fonction `get_final_response()` :

```python
# Enregistrer les métriques
if getattr(Config, 'METRICS_ENABLED', True):
    answer_quality_scores = final_state.get("answer_quality_scores")
    metrics.record_request(
        conversation_id=conversation_id,
        query=query,
        latencies=latencies,
        success=True,
        num_documents=len(final_state.get("documents", [])),
        response_length=len(response) if response else 0,
        answer_quality_score=answer_quality_scores.get("overall_score") if answer_quality_scores else None,
        answer_quality_scores=answer_quality_scores
    )
```

#### Métriques Collectées par Étape

**Retrieval** (`retrieve`) :
- Latence retrieval
- Latence reranking (si activé)
- Nombre de documents récupérés
- IDs des documents récupérés (enregistrés séparément)

**Grading** (`grade_documents`) :
- Latence grading
- Nombre de documents filtrés
- Scores moyens (si multi-critères)

**Web Search** (`web_search`) :
- Latence web_search

**Generation** (`generate`) :
- Latence generation
- Longueur de la réponse

**Answer Quality** (`grade_answer_quality`) :
- Latence answer_quality
- Scores détaillés (relevance, completeness, conciseness, accuracy, coherence)
- Score global

**End-to-End** :
- Latence totale (depuis début jusqu'à fin)

### Format des Métriques

#### Fichier `metrics.jsonl` (Une ligne par requête)

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "conversation_id": "uuid-1234-5678",
  "query": "What is a transformer?",
  "success": true,
  "error": null,
  "latencies": {
    "retrieval": 0.234,
    "reranking": 0.045,
    "grading": 0.567,
    "web_search": 0.0,
    "generation": 1.234,
    "answer_quality": 0.456,
    "end_to_end": 2.536
  },
  "num_documents": 3,
  "response_length": 450,
  "answer_quality_score": 0.85,
  "answer_quality_scores": {
    "relevance": 0.9,
    "completeness": 0.8,
    "conciseness": 0.85,
    "accuracy": 0.9,
    "coherence": 0.8,
    "overall_score": 0.85,
    "accepted": true,
    "reasoning": "The answer is relevant and complete..."
  }
}
```

#### Fichier `summary.json` (Résumé agrégé)

```json
{
  "total_requests": 1500,
  "total_errors": 45,
  "latencies": {
    "end_to_end": [2.1, 2.3, 1.9, ...],
    "retrieval": [0.2, 0.25, 0.18, ...],
    "generation": [1.1, 1.2, 0.9, ...],
    ...
  },
  "answer_quality_scores": [0.85, 0.9, 0.78, ...],
  "answer_quality_breakdown": {
    "relevance": [0.9, 0.85, 0.88, ...],
    "completeness": [0.8, 0.85, 0.75, ...],
    ...
  },
  "last_updated": "2024-01-15T10:30:45.123456"
}
```

---

## 7. Métriques Admin - Calcul et Extraction

### 7.1 Aperçu des Métriques (`get_metrics_overview`)

**Endpoint** : `GET /api/v1/admin/metrics/overview`

**Calcul** :

1. **Chargement du résumé** :
   ```python
   summary = load_metrics_summary()  # Charge summary.json
   ```

2. **Calcul métriques du jour** :
   ```python
   today_metrics = calculate_today_metrics()
   # Filtre les requêtes du jour depuis metrics.jsonl
   # Calcule: count, success, errors, success_rate, average_latency
   ```

3. **Calcul métriques globales** :
   ```python
   total_requests = summary.get("total_requests", 0)
   total_errors = summary.get("total_errors", 0)
   
   # Latence moyenne globale
   end_to_end_latencies = summary.get("latencies", {}).get("end_to_end", [])
   avg_latency = sum(end_to_end_latencies) / len(end_to_end_latencies) if end_to_end_latencies else 0.0
   
   # Taux de succès global
   global_success_rate = ((total_requests - total_errors) / total_requests * 100) if total_requests > 0 else 0.0
   ```

4. **Retour** :
   ```python
   {
     "total_requests": total_requests,
     "requests_today": today_metrics["count"],
     "success_rate": global_success_rate,  # En pourcentage
     "average_latency": avg_latency,  # En secondes
     "error_count": total_errors
   }
   ```

### 7.2 Données pour Graphiques (`get_requests_chart_data`)

**Endpoint** : `GET /api/v1/admin/metrics/requests?days=7`

**Calcul** :

1. **Chargement des requêtes récentes** :
   ```python
   requests = load_recent_requests(limit=10000)
   # Lit les dernières lignes de metrics.jsonl
   ```

2. **Groupement par date** :
   ```python
   date_groups = {}
   for req in requests:
       date = req.get("timestamp", "")[:10]  # YYYY-MM-DD
       if date not in date_groups:
           date_groups[date] = {"requests": 0, "success": 0, "errors": 0}
       
       date_groups[date]["requests"] += 1
       if req.get("success", False):
           date_groups[date]["success"] += 1
       else:
           date_groups[date]["errors"] += 1
   ```

3. **Formatage et tri** :
   ```python
   # Trier par date (plus récent en premier)
   # Formater dates (ex: "22 Dec")
   # Limiter aux N derniers jours
   ```

4. **Retour** :
   ```python
   [
     {
       "date": "22 Dec",
       "requests": 150,
       "success": 145,
       "errors": 5
     },
     ...
   ]
   ```

### 7.3 Requêtes Récentes (`get_recent_requests`)

**Endpoint** : `GET /api/v1/admin/metrics/recent?limit=10`

**Calcul** :

1. **Chargement** :
   ```python
   requests = load_recent_requests(limit=limit)
   # Lit les N dernières lignes de metrics.jsonl
   # Trie par timestamp (plus récent en premier)
   ```

2. **Formatage** :
   ```python
   for req in requests:
       formatted.append({
           "id": req.get("conversation_id", "unknown"),
           "timestamp": req.get("timestamp", ""),
           "user": "user@rag-system.io",  # TODO: Récupérer depuis JWT
           "question": req.get("query", "")[:50] + "...",
           "status": "success" if req.get("success", False) else "error",
           "latency": req.get("latencies", {}).get("end_to_end", 0.0)
       })
   ```

### 7.4 Répartition des Erreurs (`get_error_distribution`)

**Endpoint** : `GET /api/v1/admin/metrics/errors`

**Calcul** :

1. **Chargement des requêtes récentes** :
   ```python
   requests = load_recent_requests(limit=1000)
   ```

2. **Catégorisation des erreurs** :
   ```python
   distribution = {
       "timeout": 0,
       "llm_error": 0,
       "retrieval": 0,
       "web_search": 0,
       "other": 0
   }
   
   for req in requests:
       if not req.get("success", False):
           error = req.get("error", "").lower()
           
           if "timeout" in error:
               distribution["timeout"] += 1
           elif "llm" in error or "generation" in error:
               distribution["llm_error"] += 1
           elif "retrieval" in error or "retrieve" in error:
               distribution["retrieval"] += 1
           elif "web" in error or "search" in error:
               distribution["web_search"] += 1
           else:
               distribution["other"] += 1
   ```

### 7.5 Statut du Système (`get_system_status`)

**Endpoint** : `GET /api/v1/admin/system/status`

**Retour** (statique pour l'instant) :
```python
{
  "rag_pipeline": "Active",
  "vector_db": "Connected",
  "llm_status": "Operational",
  "uptime_percentage": 98.5
}
```

**Note** : Dans une implémentation complète, on vérifierait :
- Connexion à ChromaDB
- Disponibilité de l'API Groq
- Disponibilité de Tavily
- Health checks des services

---

## 8. Métriques de Retrieval

### 8.1 Collecte des Métriques de Retrieval

Dans `Rag_model.py`, fonction `retrieve()` :

```python
# Enregistrer les résultats de retrieval pour les métriques
retrieval_metrics_enabled = getattr(Config, 'RETRIEVAL_METRICS_ENABLED', True)
if retrieval_metrics_enabled:
    retrieval_collector = get_retrieval_metrics_collector()
    
    # Extraire les IDs des documents récupérés
    retrieved_doc_ids = []
    retrieved_sources = []
    for doc in documents:
        doc_id = doc.metadata.get('parent_doc_id') or doc.metadata.get('chunk_id') or doc.metadata.get('source', 'unknown')
        retrieved_doc_ids.append(str(doc_id))
        source = doc.metadata.get('source', 'unknown')
        retrieved_sources.append(str(source))
    
    retrieval_collector.record_retrieval(
        conversation_id=conversation_id,
        query=state["question"],
        retrieved_doc_ids=retrieved_doc_ids,
        retrieved_sources=retrieved_sources
    )
```

### 8.2 Format des Métriques de Retrieval

**Fichier** : `data/metrics/retrieval_results.jsonl`

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "conversation_id": "uuid-1234-5678",
  "query": "What is a transformer?",
  "retrieved_doc_ids": ["doc-uuid-1", "doc-uuid-2", "doc-uuid-3"],
  "retrieved_sources": ["https://example.com/doc1", "data/raw/doc2.pdf"],
  "num_retrieved": 3
}
```

### 8.3 Calcul des Métriques de Retrieval

#### Precision@k

```python
def calculate_precision_at_k(retrieved_ids, relevant_ids, k):
    """
    Precision@k = (Nombre de documents pertinents dans les k premiers) / k
    """
    top_k_retrieved = retrieved_ids[:k]
    relevant_retrieved = sum(1 for doc_id in top_k_retrieved if doc_id in relevant_ids)
    return relevant_retrieved / min(k, len(top_k_retrieved))
```

#### Recall@k

```python
def calculate_recall_at_k(retrieved_ids, relevant_ids, k):
    """
    Recall@k = (Nombre de documents pertinents récupérés) / (Total documents pertinents)
    """
    top_k_retrieved = retrieved_ids[:k]
    relevant_retrieved = sum(1 for doc_id in top_k_retrieved if doc_id in relevant_ids)
    return relevant_retrieved / len(relevant_ids) if relevant_ids else 0.0
```

#### Average Precision (AP)

```python
def calculate_average_precision(retrieved_ids, relevant_ids):
    """
    AP = Moyenne des précisions à chaque position où on trouve un document pertinent
    """
    precisions = []
    relevant_count = 0
    
    for i, doc_id in enumerate(retrieved_ids):
        if doc_id in relevant_ids:
            relevant_count += 1
            precision_at_i = relevant_count / (i + 1)
            precisions.append(precision_at_i)
    
    return sum(precisions) / len(relevant_ids) if precisions else 0.0
```

#### Mean Average Precision (MAP)

```python
def calculate_mean_average_precision(retrieval_results, ground_truth):
    """
    MAP = Moyenne des Average Precisions sur toutes les requêtes
    """
    average_precisions = []
    
    for result in retrieval_results:
        query = result.get('query', '').strip()
        retrieved_ids = result.get('retrieved_doc_ids', [])
        relevant_ids = ground_truth.get(query, set())
        
        if relevant_ids:
            ap = calculate_average_precision(retrieved_ids, relevant_ids)
            average_precisions.append(ap)
    
    return sum(average_precisions) / len(average_precisions) if average_precisions else 0.0
```

**Note** : Ces métriques nécessitent un ground truth (documents pertinents pour chaque requête) pour être calculées.

---

## 9. Stockage et Persistance

### 9.1 Fichiers de Métriques

**Répertoire** : `data/metrics/`

**Fichiers** :
- `metrics.jsonl` : Une ligne JSON par requête (métriques générales)
- `summary.json` : Résumé agrégé (mis à jour à chaque requête)
- `retrieval_results.jsonl` : Une ligne JSON par retrieval (métriques de retrieval)

### 9.2 Mise à Jour du Résumé

Dans `MetricsCollector._update_summary()` :

1. **Chargement** : Lit `summary.json`
2. **Mise à jour** :
   - Incrémente `total_requests`
   - Incrémente `total_errors` si échec
   - Ajoute latences (garde les 1000 dernières)
   - Ajoute scores de qualité (garde les 1000 dernières)
3. **Sauvegarde** : Écrit `summary.json`

### 9.3 Thread-Safety

Utilisation de locks pour garantir thread-safety :
```python
_metrics_lock = threading.Lock()
_retrieval_metrics_lock = threading.Lock()
```

---

## 10. APIs Admin

### 10.1 Modèles de Réponse

#### `MetricOverview`
```python
{
  "total_requests": int,
  "requests_today": int,
  "success_rate": float,  # En pourcentage
  "average_latency": float,  # En secondes
  "error_count": int
}
```

#### `RequestDataPoint`
```python
{
  "date": str,  # Format: "22 Dec"
  "requests": int,
  "success": int,
  "errors": int
}
```

#### `RecentRequest`
```python
{
  "id": str,  # conversation_id
  "timestamp": str,
  "user": str,
  "question": str,
  "status": str,  # "success" | "error"
  "latency": float
}
```

#### `ErrorDistribution`
```python
{
  "timeout": int,
  "llm_error": int,
  "retrieval": int,
  "web_search": int,
  "other": int
}
```

#### `SystemStatus`
```python
{
  "rag_pipeline": str,  # "Active" | "Inactive"
  "vector_db": str,  # "Connected" | "Disconnected"
  "llm_status": str,  # "Operational" | "Degraded" | "Down"
  "uptime_percentage": float
}
```

### 10.2 Endpoints

Tous les endpoints sont préfixés par `/api/v1/admin` :

- `GET /metrics/overview` → `MetricOverview`
- `GET /metrics/requests?days=7` → `List[RequestDataPoint]`
- `GET /metrics/recent?limit=10` → `List[RecentRequest]`
- `GET /metrics/errors` → `ErrorDistribution`
- `GET /system/status` → `SystemStatus`

### 10.3 Authentification

**Note** : L'authentification admin est préparée mais commentée :
```python
# TODO: Ajouter une dépendance d'authentification pour vérifier le role "admin"
# from api.dependencies import require_admin

@router.get("/metrics/overview")
async def get_overview():
    # await require_admin()  # À décommenter une fois l'auth implémentée
    ...
```

---

## Conclusion

Ce document détaille l'architecture complète du système RAG, depuis le traitement des documents jusqu'à la génération de réponses, en passant par le système de métriques et leur extraction pour le dashboard admin.

### Points Clés

1. **Architecture modulaire** : Séparation claire des responsabilités
2. **Workflow adaptatif** : Décisions intelligentes selon le contexte
3. **Métriques complètes** : Suivi détaillé de toutes les opérations
4. **Qualité garantie** : Multiples validations (grading, hallucinations, qualité)
5. **Performance** : Reranking, hybrid search, optimisations

### Fichiers Importants

- `Backend/src/rag/Rag_model.py` : Workflow LangGraph principal
- `Backend/src/rag/Data_processing.py` : Traitement et indexation des documents
- `Backend/src/core/metrics.py` : Collecteur de métriques générales
- `Backend/src/core/retrieval_metrics.py` : Collecteur de métriques de retrieval
- `Backend/api/services/metrics_service.py` : Calcul des métriques admin
- `Backend/api/routes/admin.py` : Routes API admin

---

**Date de création** : 2024  
**Version** : 1.0  
**Auteur** : Documentation technique du système RAG
