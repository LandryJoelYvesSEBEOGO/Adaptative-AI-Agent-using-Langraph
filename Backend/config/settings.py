"""Configuration de l'application, chargée depuis l'environnement (et `.env`).

Aucune valeur sensible n'est définie ici : les secrets viennent exclusivement de
l'environnement. Les réglages du pipeline gardent leurs valeurs par défaut et
peuvent tous être surchargés par une variable d'environnement du même nom.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Environnement ---
    ENVIRONMENT: Literal["dev", "prod"] = "dev"

    # --- Secrets et clés d'API (jamais de valeur par défaut) ---
    JWT_SECRET_KEY: str = ""
    GROQ_API_KEY: str | None = None  # clé principale
    GROQ_API_KEYS_STR: str = Field(default="", validation_alias="GROQ_API_KEYS")
    TAVILY_API_KEY: str | None = None
    LANGSMITH_API_KEY: str | None = None

    # --- Tracing LangSmith (désactivé par défaut) ---
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_PROJECT: str = "rag-system"

    # --- CORS : origines autorisées, séparées par des virgules ---
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,"
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080,http://127.0.0.1:8080,"
        "http://localhost:8081,http://127.0.0.1:8081"
    )

    # --- Base de données ---
    # URL SQLAlchemy, ex. postgresql+psycopg://user:pass@host:5432/rag. Vide : SQLite local.
    DATABASE_URL: str = ""
    RAG_DB_PATH: str = str(DATA_DIR / "rag.db")  # utilisé uniquement si DATABASE_URL est vide
    AUTO_MIGRATE: bool = True  # applique `alembic upgrade head` au démarrage de l'API

    # --- Embeddings et reranking : fournisseurs hébergés ou modèles locaux ---
    OPENAI_API_KEY: str | None = None
    COHERE_API_KEY: str | None = None
    EMBEDDING_PROVIDER: Literal["nomic-local", "openai", "cohere"] = "nomic-local"
    EMBEDDING_MODEL: str = ""  # vide : modèle par défaut du fournisseur
    EMBEDDING_DIM: int = 768  # dimension de la colonne pgvector (changer = nouvelle migration)
    RERANKER_PROVIDER: Literal["none", "local", "cohere"] = "local"
    RERANK_MIN_SCORE: float = 0.1  # sous ce score (0-1), la recherche web prend le relais
    SEARCH_CANDIDATES: int = 40  # candidats par branche (dense / lexicale) avant fusion RRF
    RRF_K: int = 60  # constante de la fusion par rangs réciproques

    # --- Modèles ---
    GROQ_model: str = "openai/gpt-oss-120b"
    NomicEmbeddings_model: str = "nomic-embed-text-v1.5"

    # --- Périphérique de calcul : "auto" (CUDA si disponible, sinon CPU), "cuda" ou "cpu" ---
    DEVICE_PREFERENCE: Literal["auto", "cuda", "cpu"] = "auto"

    # --- Chemins ---
    LOGS_DIR: str = str(DATA_DIR / "logs")
    RETRIEVAL_METRICS_FILE: str = str(DATA_DIR / "metrics" / "retrieval_results.jsonl")
    FEW_SHOT_EXAMPLES_FILE: str = str(DATA_DIR / "few_shot_examples.json")

    # --- Réglages du pipeline ---
    DISABLE_WARNINGS: bool = True  # Désactiver les warnings Python/Transformers
    SHOW_PROGRESS_BARS: bool = True  # Afficher les barres de progression (tqdm)
    DEBUG_METADATA: bool = True  # Activer le debug des métadonnées pour diagnostiquer les problèmes
    MAX_RETRIES: int = 3  # Nombre maximum de tentatives en cas d'échec
    RETRY_BACKOFF_FACTOR: int = 2  # Facteur d'exponentiel backoff
    RETRY_INITIAL_DELAY: int = 1  # Délai initial en secondes
    LLM_TIMEOUT: int = 30
    RETRIEVAL_TIMEOUT: int = 10
    WEB_SEARCH_TIMEOUT: int = 15
    ALERT_LATENCY_THRESHOLD: float = 10.0  # Alerter si latence > 10s
    ALERT_ERROR_RATE_THRESHOLD: float = 0.05  # Alerter si taux d'erreur > 5%
    HYBRID_SEARCH_ENABLED: bool = True  # Activer/désactiver hybrid search
    VECTOR_SEARCH_WEIGHT: float = 0.7  # Poids pour recherche vectorielle (70%)
    BM25_SEARCH_WEIGHT: float = 0.3  # Poids pour recherche BM25 (30%)
    RERANKER_ENABLED: bool = True  # Activer/désactiver le reranker
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # Modèle cross-encoder
    RERANKER_TOP_K: int = 20  # Nombre de documents à récupérer avant reranking
    RERANKER_FINAL_K: int = 3  # Nombre de documents à retourner après reranking
    MULTI_CRITERIA_GRADING_ENABLED: bool = True  # Activer/désactiver le grading multi-critères
    GRADING_RELEVANCE_WEIGHT: float = 0.35  # Poids pour Relevance (35%)
    GRADING_COVERAGE_WEIGHT: float = 0.25  # Poids pour Coverage (25%)
    GRADING_FRESHNESS_WEIGHT: float = 0.15  # Poids pour Freshness (15%)
    GRADING_AUTHORITY_WEIGHT: float = 0.15  # Poids pour Authority (15%)
    GRADING_CLARITY_WEIGHT: float = 0.1  # Poids pour Clarity (10%)
    GRADING_ACCEPTANCE_THRESHOLD: float = 0.6  # Seuil d'acceptation (0-1)
    GRADING_ADAPTIVE_THRESHOLD: bool = True  # Seuil adaptatif basé sur les scores moyens
    METADATA_ENRICHMENT_ENABLED: bool = True  # Activer/désactiver l'enrichissement
    METADATA_USE_LOCAL_MODELS: bool = True
    METADATA_DETECT_LANGUAGE: bool = (
        False  # Détection de langue (False = "en" par défaut pour l'instant)
    )
    METADATA_EXTRACT_ENTITIES: bool = True  # Extraire les entités nommées
    METADATA_EXTRACT_KEYWORDS: bool = True  # Extraire les mots-clés
    METADATA_EXTRACT_TOPICS: bool = True  # Extraire les sujets
    METADATA_EXTRACT_SUMMARY: bool = True  # Générer un résumé
    METADATA_MAX_KEYWORDS: int = 5  # Nombre maximum de mots-clés
    METADATA_MAX_ENTITIES: int = 10  # Nombre maximum d'entités
    METADATA_MAX_TOPICS: int = 3  # Nombre maximum de sujets
    METADATA_SUMMARY_MAX_LENGTH: int = 100  # Longueur max du résumé en mots
    RETRIEVAL_METRICS_ENABLED: bool = True  # Enregistrer les résultats de retrieval
    CITATIONS_ENABLED: bool = True  # Activer/désactiver les citations automatiques
    CITATION_FORMAT: str = "numeric"
    ANSWER_QUALITY_SCORING_ENABLED: bool = (
        True  # Activer/désactiver le scoring de qualité de réponse
    )
    ANSWER_QUALITY_RELEVANCE_WEIGHT: float = 0.3  # Poids pour Relevance (30%)
    ANSWER_QUALITY_COMPLETENESS_WEIGHT: float = 0.25  # Poids pour Completeness (25%)
    ANSWER_QUALITY_CONCISENESS_WEIGHT: float = 0.15  # Poids pour Conciseness (15%)
    ANSWER_QUALITY_ACCURACY_WEIGHT: float = 0.2  # Poids pour Accuracy (20%)
    ANSWER_QUALITY_COHERENCE_WEIGHT: float = 0.1  # Poids pour Coherence (10%)
    ANSWER_QUALITY_ACCEPTANCE_THRESHOLD: float = 0.65  # Seuil d'acceptation (0-1)
    ANSWER_QUALITY_ADAPTIVE_THRESHOLD: bool = True  # Seuil adaptatif basé sur les scores moyens
    STREAMING_ENABLED: bool = True  # Activer/désactiver le streaming
    STREAMING_CHUNK_SIZE: int = 1  # Nombre de tokens à streamer à la fois (1 = token par token)
    RETRY_JITTER_ENABLED: bool = True  # Activer le jitter aléatoire
    RETRY_JITTER_MAX: float = 0.3  # Jitter maximum (30% du délai)
    CIRCUIT_BREAKER_ENABLED: bool = True  # Activer le circuit breaker
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5  # Nombre d'échecs avant ouverture
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = 60  # Temps avant tentative de récupération (secondes)
    CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS: int = 3  # Nombre max d'appels en half-open
    FALLBACK_MODELS_ENABLED: bool = True  # Activer les modèles de fallback
    FALLBACK_MODEL_SECONDARY: str = "meta-llama/llama-prompt-guard-2-86m"
    FALLBACK_MODEL_FAST: str = "openai/gpt-oss-120b"  # Modèle rapide (si disponible)
    RECOVERY_STRATEGY_ENABLED: bool = True  # Activer les stratégies de recovery
    RECOVERY_INCREASE_TEMPERATURE: bool = True  # Augmenter température pour hallucinations
    RECOVERY_TEMPERATURE_INCREASE: float = 0.2  # Augmentation de température
    RECOVERY_EXPAND_SEARCH: bool = True  # Élargir la recherche pour "not useful"
    RECOVERY_SEARCH_EXPANSION_FACTOR: float = 1.5  # Facteur d'expansion (k * factor)
    FEW_SHOT_ENABLED: bool = True
    FEW_SHOT_NUM_EXAMPLES: int = 2  # Nombre d'exemples à inclure (2-3 recommandé)
    FEW_SHOT_SIMILARITY_THRESHOLD: float = 0.7  # Seuil de similarité pour sélection
    CHAIN_OF_THOUGHT_ENABLED: bool = True
    CHAIN_OF_THOUGHT_FOR_COMPLEX: bool = True  # Activer CoT pour questions complexes uniquement
    CHAIN_OF_THOUGHT_COMPLEXITY_THRESHOLD: int = 50  # Nombre de mots pour considérer comme complexe
    ROLE_BASED_PROMPTING_ENABLED: bool = True
    ROLE_DETECTION_ENABLED: bool = True  # Détecter automatiquement le rôle selon le contexte
    STRUCTURED_OUTPUT_ENABLED: bool = False  # Désactivé par défaut (peut augmenter tokens)
    STRUCTURED_OUTPUT_FORMAT: str = "markdown"  # "markdown" ou "json"
    CONVERSATION_CONTEXT_TURNS: int = 6  # Nombre de tours (user+assistant) à injecter
    CONVERSATION_CONTEXT_MAX_CHARS: int = 2000  # Taille max du contexte conversationnel

    @field_validator(
        "GROQ_API_KEY",
        "TAVILY_API_KEY",
        "LANGSMITH_API_KEY",
        "OPENAI_API_KEY",
        "COHERE_API_KEY",
        mode="before",
    )
    @classmethod
    def _empty_to_none(cls, value):
        return value or None

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL or f"sqlite:///{self.RAG_DB_PATH}"

    @property
    def GROQ_API_KEYS(self) -> list[str]:
        """Clés Groq dédupliquées (clé principale d'abord)."""
        extra = [k.strip() for k in self.GROQ_API_KEYS_STR.split(",") if k.strip()]
        keys = ([self.GROQ_API_KEY] if self.GROQ_API_KEY else []) + extra
        return list(dict.fromkeys(keys))

    def export_runtime_env(self) -> None:
        """Exporte vers `os.environ` ce que les bibliothèques tierces lisent elles-mêmes.

        À appeler explicitement au démarrage du moteur RAG (pas à l'import).
        """
        if self.TAVILY_API_KEY:
            os.environ["TAVILY_API_KEY"] = self.TAVILY_API_KEY
        if self.LANGCHAIN_TRACING_V2 and self.LANGSMITH_API_KEY:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = self.LANGSMITH_API_KEY
            os.environ["LANGCHAIN_PROJECT"] = self.LANGCHAIN_PROJECT
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "true")
        os.environ.setdefault("USER_AGENT", "RagSystem/1.0")


@lru_cache
def get_settings() -> Settings:
    return Settings()
