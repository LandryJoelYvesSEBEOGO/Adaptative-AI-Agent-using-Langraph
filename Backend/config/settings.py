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

    # --- Sessions (cookies httpOnly) ---
    ACCESS_TOKEN_MINUTES: int = 30
    REFRESH_TOKEN_DAYS: int = 7
    COOKIE_SECURE: bool = False  # true en production (HTTPS)
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"

    # --- Limites d'usage ---
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_AUTH_PER_MINUTE: int = 20  # connexions / inscriptions, par adresse IP
    RATE_LIMIT_LOGIN_ACCOUNT_PER_MINUTE: int = 5  # tentatives de connexion, par compte
    RATE_LIMIT_CHAT_PER_MINUTE: int = 20  # questions, par utilisateur
    DAILY_QUESTION_QUOTA: int = 200  # questions par utilisateur et par jour (0 = illimité) ; admins exemptés
    # true derrière un reverse proxy de confiance : l'IP du client est lue dans X-Forwarded-For
    TRUST_PROXY_HEADERS: bool = False

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

    # --- Ingestion des documents ---
    UPLOAD_DIR: str = str(DATA_DIR / "uploads")
    MAX_UPLOAD_MB: int = 50
    INGEST_PARSER: Literal["docling", "pypdf"] = "docling"
    INGEST_CHUNK_MAX_CHARS: int = 3000

    # --- Réglages du pipeline ---
    MAX_RETRIES: int = 3  # Nombre maximum de tentatives en cas d'échec
    LLM_TIMEOUT: int = 30
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # Modèle cross-encoder
    RERANKER_TOP_K: int = 20  # Nombre de documents à récupérer avant reranking
    RERANKER_FINAL_K: int = 3  # Nombre de documents à retourner après reranking
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
