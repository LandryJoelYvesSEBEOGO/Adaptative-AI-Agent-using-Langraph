import os

from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

# Définir project_root pour les chemins
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class Config:
    # Configuration des environnements
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "local-llama32-rag"
    os.environ["TOKENIZERS_PARALLELISM"] = "true"
    os.environ["USER_AGENT"] = "MyCustomUserAgent/1.0"

    # Configuration des Keys
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY
    LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")

    # Clés API Groq multiples (séparées par des virgules dans .env)
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # Clé principale
    GROQ_API_KEYS_STR = os.getenv("GROQ_API_KEYS", "")  # Clés supplémentaires
    # Nettoyer et parser les clés supplémentaires
    GROQ_API_KEYS = [key.strip() for key in GROQ_API_KEYS_STR.split(",") if key.strip()]
    # Ajouter la clé principale si elle existe
    if GROQ_API_KEY:
        all_keys = [GROQ_API_KEY] + GROQ_API_KEYS
        # Supprimer les doublons en gardant l'ordre
        GROQ_API_KEYS = list(dict.fromkeys(all_keys))
    else:
        GROQ_API_KEYS = GROQ_API_KEYS if GROQ_API_KEYS else []

    # Configuration des models
    GROQ_model = "openai/gpt-oss-120b"
    NomicEmbeddings_model = "nomic-embed-text-v1.5"

    # Configuration Device (GPU/CPU)
    FORCE_GPU = True  # Forcer l'utilisation du GPU (CUDA) même si la détection échoue
    DEVICE_PREFERENCE = "cuda"  # "cuda" pour GPU, "cpu" pour CPU, "auto" pour détection automatique

    # Configuration Warnings et Logs
    DISABLE_WARNINGS = True  # Désactiver les warnings Python/Transformers
    SHOW_PROGRESS_BARS = True  # Afficher les barres de progression (tqdm)
    DEBUG_METADATA = True  # Activer le debug des métadonnées pour diagnostiquer les problèmes

    # Configuration du workflow
    MAX_RETRIES = 3  # Nombre maximum de tentatives en cas d'échec
    RETRY_BACKOFF_FACTOR = 2  # Facteur d'exponentiel backoff
    RETRY_INITIAL_DELAY = 1  # Délai initial en secondes

    # Timeouts (en secondes)
    LLM_TIMEOUT = 30
    RETRIEVAL_TIMEOUT = 10
    WEB_SEARCH_TIMEOUT = 15

    # Configuration des métriques
    METRICS_ENABLED = True  # Activer/désactiver les métriques
    METRICS_DIR = os.path.join(project_root, "data", "metrics")
    LOGS_DIR = os.path.join(project_root, "data", "logs")

    # Seuils d'alerte (en secondes)
    ALERT_LATENCY_THRESHOLD = 10.0  # Alerter si latence > 10s
    ALERT_ERROR_RATE_THRESHOLD = 0.05  # Alerter si taux d'erreur > 5%

    # Configuration Hybrid Search
    HYBRID_SEARCH_ENABLED = True  # Activer/désactiver hybrid search
    VECTOR_SEARCH_WEIGHT = 0.7  # Poids pour recherche vectorielle (70%)
    BM25_SEARCH_WEIGHT = 0.3  # Poids pour recherche BM25 (30%)
    # Configuration Reranker
    RERANKER_ENABLED = True  # Activer/désactiver le reranker
    RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # Modèle cross-encoder
    RERANKER_TOP_K = 20  # Nombre de documents à récupérer avant reranking
    RERANKER_FINAL_K = 3  # Nombre de documents à retourner après reranking
    # Configuration Document Grading Multi-Critères
    MULTI_CRITERIA_GRADING_ENABLED = True  # Activer/désactiver le grading multi-critères
    GRADING_RELEVANCE_WEIGHT = 0.35  # Poids pour Relevance (35%)
    GRADING_COVERAGE_WEIGHT = 0.25  # Poids pour Coverage (25%)
    GRADING_FRESHNESS_WEIGHT = 0.15  # Poids pour Freshness (15%)
    GRADING_AUTHORITY_WEIGHT = 0.15  # Poids pour Authority (15%)
    GRADING_CLARITY_WEIGHT = 0.10  # Poids pour Clarity (10%)
    GRADING_ACCEPTANCE_THRESHOLD = 0.6  # Seuil d'acceptation (0-1)
    GRADING_ADAPTIVE_THRESHOLD = True  # Seuil adaptatif basé sur les scores moyens
    # Configuration Enrichissement Métadonnées
    METADATA_ENRICHMENT_ENABLED = True  # Activer/désactiver l'enrichissement
    METADATA_USE_LOCAL_MODELS = (
        True  # Si True, utilise modèles locaux (KeyBERT, spaCy, etc.), sinon utilise LLM (Groq)
    )
    METADATA_DETECT_LANGUAGE = False  # Détection de langue (False = "en" par défaut pour l'instant)
    METADATA_EXTRACT_ENTITIES = True  # Extraire les entités nommées
    METADATA_EXTRACT_KEYWORDS = True  # Extraire les mots-clés
    METADATA_EXTRACT_TOPICS = True  # Extraire les sujets
    METADATA_EXTRACT_SUMMARY = True  # Générer un résumé
    METADATA_MAX_KEYWORDS = 5  # Nombre maximum de mots-clés
    METADATA_MAX_ENTITIES = 10  # Nombre maximum d'entités
    METADATA_MAX_TOPICS = 3  # Nombre maximum de sujets
    METADATA_SUMMARY_MAX_LENGTH = 100  # Longueur max du résumé en mots
    # Configuration Métriques Retrieval
    RETRIEVAL_METRICS_ENABLED = True  # Activer/désactiver l'enregistrement des résultats retrieval
    RETRIEVAL_METRICS_FILE = os.path.join(
        project_root, "data", "metrics", "retrieval_results.jsonl"
    )
    # Configuration Citations Automatiques
    CITATIONS_ENABLED = True  # Activer/désactiver les citations automatiques
    CITATION_FORMAT = (
        "numeric"  # Format des citations: "numeric" ([1], [2]) ou "inline" (source name)
    )
    # Configuration Answer Quality Scoring
    ANSWER_QUALITY_SCORING_ENABLED = True  # Activer/désactiver le scoring de qualité de réponse
    ANSWER_QUALITY_RELEVANCE_WEIGHT = 0.30  # Poids pour Relevance (30%)
    ANSWER_QUALITY_COMPLETENESS_WEIGHT = 0.25  # Poids pour Completeness (25%)
    ANSWER_QUALITY_CONCISENESS_WEIGHT = 0.15  # Poids pour Conciseness (15%)
    ANSWER_QUALITY_ACCURACY_WEIGHT = 0.20  # Poids pour Accuracy (20%)
    ANSWER_QUALITY_COHERENCE_WEIGHT = 0.10  # Poids pour Coherence (10%)
    ANSWER_QUALITY_ACCEPTANCE_THRESHOLD = 0.65  # Seuil d'acceptation (0-1)
    ANSWER_QUALITY_ADAPTIVE_THRESHOLD = True  # Seuil adaptatif basé sur les scores moyens
    # Configuration Streaming des Réponses
    STREAMING_ENABLED = True  # Activer/désactiver le streaming
    STREAMING_CHUNK_SIZE = 1  # Nombre de tokens à streamer à la fois (1 = token par token)
    # Configuration Retry Policy Sophistiquée
    RETRY_JITTER_ENABLED = True  # Activer le jitter aléatoire
    RETRY_JITTER_MAX = 0.3  # Jitter maximum (30% du délai)
    CIRCUIT_BREAKER_ENABLED = True  # Activer le circuit breaker
    CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5  # Nombre d'échecs avant ouverture
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT = 60  # Temps avant tentative de récupération (secondes)
    CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS = 3  # Nombre max d'appels en half-open

    # Configuration Fallback Models
    FALLBACK_MODELS_ENABLED = True  # Activer les modèles de fallback
    FALLBACK_MODEL_SECONDARY = (
        "meta-llama/llama-prompt-guard-2-86m"  # Modèle secondaire (si disponible)
    )
    FALLBACK_MODEL_FAST = "openai/gpt-oss-120b"  # Modèle rapide (si disponible)

    # Configuration Stratégies de Recovery
    RECOVERY_STRATEGY_ENABLED = True  # Activer les stratégies de recovery
    RECOVERY_INCREASE_TEMPERATURE = True  # Augmenter température pour hallucinations
    RECOVERY_TEMPERATURE_INCREASE = 0.2  # Augmentation de température
    RECOVERY_EXPAND_SEARCH = True  # Élargir la recherche pour "not useful"
    RECOVERY_SEARCH_EXPANSION_FACTOR = 1.5  # Facteur d'expansion (k * factor)
    # ===== PROMPT ENGINEERING AVANCÉ =====
    # Few-Shot Learning
    FEW_SHOT_ENABLED = True
    FEW_SHOT_NUM_EXAMPLES = 2  # Nombre d'exemples à inclure (2-3 recommandé)
    FEW_SHOT_EXAMPLES_FILE = os.path.join(project_root, "data", "few_shot_examples.json")
    FEW_SHOT_SIMILARITY_THRESHOLD = 0.7  # Seuil de similarité pour sélection

    # Chain-of-Thought
    CHAIN_OF_THOUGHT_ENABLED = True
    CHAIN_OF_THOUGHT_FOR_COMPLEX = True  # Activer CoT pour questions complexes uniquement
    CHAIN_OF_THOUGHT_COMPLEXITY_THRESHOLD = 50  # Nombre de mots pour considérer comme complexe

    # Role-Based Prompting
    ROLE_BASED_PROMPTING_ENABLED = True
    ROLE_DETECTION_ENABLED = True  # Détecter automatiquement le rôle selon le contexte

    # Structured Output
    STRUCTURED_OUTPUT_ENABLED = False  # Désactivé par défaut (peut augmenter tokens)
    STRUCTURED_OUTPUT_FORMAT = "markdown"  # "markdown" ou "json"

    # Conversation context (mémoire)
    CONVERSATION_CONTEXT_TURNS = 6  # Nombre de tours (user+assistant) à injecter
    CONVERSATION_CONTEXT_MAX_CHARS = 2000  # Taille max du contexte conversationnel


# Global variables
class SPEAKER_TYPES:
    USER = "user"
    BOT = "bot"


# if __name__ == "__main__":
# print(Config.GROQ_API_KEY)
# print(Config.GROQ_model)
# print(Config.NomicEmbeddings_model)
# print(Config.TAVILY_API_KEY)
# print(Config.LANGSMITH_API_KEY)
# print(SPEAKER_TYPES.USER)
# print(SPEAKER_TYPES.BOT)

# Data_processing.py

# print("Nom du module :", __name__)
# print("Package du module :", __package__)
