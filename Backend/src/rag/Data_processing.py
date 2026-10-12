import os
import sys
import pickle
import uuid
import json
import warnings
from datetime import datetime
from langchain_core.documents import Document
import re
from langchain_core.messages import HumanMessage
from langchain_community.document_loaders import WebBaseLoader, PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_nomic.embeddings import NomicEmbeddings
from typing import List

# Ajouter le répertoire racine du projet au sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.Config import Config
import shutil

# Désactiver les warnings si configuré
if getattr(Config, 'DISABLE_WARNINGS', True):
    # Désactiver tous les warnings Python
    warnings.filterwarnings('ignore')
    
    # Intercepter sys.stderr pour filtrer les warnings embedInternal qui sont affichés via print()
    if not hasattr(sys.stderr, '_is_filtered'):
        original_stderr = sys.stderr
        
        class FilteredStderr:
            """Filtre les messages embedInternal avant de les écrire dans stderr."""
            def __init__(self, original):
                self.original = original
                self._is_filtered = True
            
            def write(self, text):
                # Filtrer les messages embedInternal
                if text and isinstance(text, str):
                    if not re.search(r'embedInternal.*zero tokens', text, re.I) and \
                       not re.search(r'chunking tokenized text.*zero tokens', text, re.I):
                        self.original.write(text)
                else:
                    self.original.write(text)
            
            def flush(self):
                self.original.flush()
            
            def __getattr__(self, name):
                return getattr(self.original, name)
        
        # Remplacer sys.stderr par notre version filtrée
        sys.stderr = FilteredStderr(original_stderr)
    
    # Filtrer aussi via le système de warnings Python
    original_showwarning = warnings.showwarning
    def filtered_showwarning(message, category, filename, lineno, file=None, line=None, **kwargs):
        """Filtre les warnings embedInternal avant de les afficher."""
        msg_str = str(message) if message else ""
        if re.search(r'embedInternal.*zero tokens', msg_str, re.I) or \
           re.search(r'chunking tokenized text.*zero tokens', msg_str, re.I):
            return
        original_showwarning(message, category, filename, lineno, file, line, **kwargs)
    
    warnings.showwarning = filtered_showwarning
    os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'

# Importer tqdm pour les barres de progression
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = getattr(Config, 'SHOW_PROGRESS_BARS', True)
except ImportError:
    TQDM_AVAILABLE = False
    # Créer une fonction dummy pour tqdm si non disponible
    def tqdm(iterable, *args, **kwargs):
        return iterable

os.environ["USER_AGENT"] = "MyCustomUserAgent/1.0"

# Liste des URLs à scraper
urls = [
    "https://arxiv.org/abs/2403.06779",   # Machine Learning in Empirical Asset Pricing
    "https://arxiv.org/abs/2005.02347",   # Differential Machine Learning (Pricing & Risk)
    "https://arxiv.org/abs/2003.03051",   # Cost-Sensitive Portfolio Selection (DRL)
    "https://arxiv.org/abs/2409.17266",   # LLM Agent-based Asset Pricing Models
    "https://arxiv.org/abs/2502.05878",   # RAG for Financial Time-Series Forecasting
    "https://arxiv.org/abs/2511.09754",   # Macro-Contextual Retrieval for Finance
    "https://arxiv.org/abs/2503.00549",   # Uncertainty in ML Asset Pricing
    "https://arxiv.org/abs/2601.10279",   # Selecting and Testing Asset Pricing Models
    "https://arxiv.org/abs/2510.16503",   # Sentiment and Volatility in Financial Markets
    "https://arxiv.org/abs/2506.21591",   # FinEval: Evaluating LLMs in Finance
    "https://arxiv.org/abs/2505.19617",   # Econometrics + ML for Financial Forecasting
    "https://arxiv.org/abs/2503.22693",   # Bridging LLMs and Financial Analysis
    "https://arxiv.org/abs/2511.20837",   # Deep Learning for Pricing & Hedging
    "https://arxiv.org/abs/2306.17519",   # GPT-FinRE: Financial Relation Extraction
    "https://arxiv.org/abs/2304.14544",   # Text Mining for Financial Time Series
    "https://arxiv.org/abs/2401.01751",   # Text Mining Analysis of Quant Finance Papers
    "https://arxiv.org/abs/2509.04812",   # Deep Learning for Conditional Asset Pricing
    "https://arxiv.org/abs/1307.5336",    # Semantic Orientation in Financial Texts
    "https://arxiv.org/abs/2510.03129",   # Transformer for Asset Allocation
    "https://arxiv.org/abs/2508.14052"    # FinAgentBench: Agentic Retrieval in Finance
]

# Répertoire pour ChromaDB (chemin absolu basé sur le répertoire racine du projet)
CHROMA_DB_DIR = os.path.join(project_root, "data", "chroma_db")

# Cache pour les documents BM25
BM25_DOCS_CACHE = os.path.join(project_root, "data", "bm25_docs_cache.pkl")


def load_web_documents(urls: List[str]):
    """Charge les documents à partir d'URLs en s'assurant que la métadonnée 'source' est définie."""
    all_docs = []
    url_iter = tqdm(urls, desc="Chargement URLs", unit="URL", disable=not TQDM_AVAILABLE) if TQDM_AVAILABLE and len(urls) > 1 else urls
    for url in url_iter:
        try:
            docs = WebBaseLoader(url).load()
            for doc in docs:
                # S'assurer que chaque document a une métadonnée 'source'
                if not doc.metadata.get("source"):
                    doc.metadata["source"] = url
                # Ajouter un titre lisible si absent
                if not doc.metadata.get("title"):
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    # Exemple: lilianweng.github.io/posts/2023-06-23-agent/ -> lilianweng.github.io_posts_2023-06-23-agent
                    title = parsed.netloc + parsed.path.replace("/", "_")
                    doc.metadata["title"] = title
            all_docs.extend(docs)
        except Exception as e:
            if not getattr(Config, 'DISABLE_WARNINGS', True):
                print(f"⚠️ Erreur lors du chargement de {url}: {str(e)}")
    return all_docs

def load_pdf_documents(pdf_paths: List[str]):
    """Charge les documents à partir de fichiers PDF en s'assurant que 'source' et 'title' sont définis."""
    all_docs = []
    pdf_iter = tqdm(pdf_paths, desc="Chargement PDFs", unit="PDF", disable=not TQDM_AVAILABLE) if TQDM_AVAILABLE and len(pdf_paths) > 1 else pdf_paths
    for path in pdf_iter:
        try:
            docs = PyPDFLoader(path).load()
            for doc in docs:
                # S'assurer que chaque document a une métadonnée 'source'
                if not doc.metadata.get("source"):
                    doc.metadata["source"] = path
                # Utiliser le nom de fichier comme titre si absent
                if not doc.metadata.get("title"):
                    source_path = doc.metadata.get("source", "")
                    if source_path:
                        filename = os.path.basename(source_path.replace("\\", "/"))
                        # Enlever l'extension .pdf pour un titre plus propre
                        if filename.endswith('.pdf'):
                            doc.metadata["title"] = filename[:-4]
                        else:
                            doc.metadata["title"] = filename
                    else:
                        # Si pas de source, utiliser un titre générique basé sur l'index
                        doc.metadata["title"] = f"PDF Document"
            all_docs.extend(docs)
        except Exception as e:
            if not getattr(Config, 'DISABLE_WARNINGS', True):
                print(f"⚠️ Erreur lors du chargement de {path}: {str(e)}")
    return all_docs

def split_documents(docs_list: List, chunk_size: int = 1000, chunk_overlap: int = 200):
    """Divise les documents en morceaux pour un traitement plus efficace."""
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]  # Ordre des séparateurs pour éviter les chunks trop petits
    )
    doc_splits = text_splitter.split_documents(docs_list)
    
    # Filtrer les chunks vides ou trop courts pour éviter les warnings "zero tokens"
    filtered_splits = []
    min_chunk_length = 10  # Minimum 10 caractères (hors espaces)
    skipped_count = 0
    
    for doc in doc_splits:
        cleaned_text = doc.page_content.strip()
        if len(cleaned_text) >= min_chunk_length:
            filtered_splits.append(doc)
        else:
            skipped_count += 1
    
    if skipped_count > 0:
        print(f"[INFO] {skipped_count} chunks ignorés (trop courts ou vides, < {min_chunk_length} caractères)")
    
    # Enrichir les métadonnées
    enriched_splits = enrich_document_metadata(filtered_splits)
    
    return enriched_splits


def _save_bm25_documents(doc_splits):
    """Sauvegarde les documents pour BM25 dans un fichier cache."""
    try:
        os.makedirs(os.path.dirname(BM25_DOCS_CACHE), exist_ok=True)
        with open(BM25_DOCS_CACHE, 'wb') as f:
            pickle.dump(doc_splits, f)
        print("[INFO] Documents sauvegardes pour BM25 cache")
    except Exception as e:
        print(f"[WARNING] Impossible de sauvegarder BM25 cache: {str(e)}")


def _load_bm25_documents():
    """Charge les documents pour BM25 depuis le cache."""
    try:
        if os.path.exists(BM25_DOCS_CACHE):
            with open(BM25_DOCS_CACHE, 'rb') as f:
                return pickle.load(f)
    except Exception as e:
        print(f"[WARNING] Impossible de charger BM25 cache: {str(e)}")
    return None

# LLM global pour l'extraction de métadonnées (utilise le gestionnaire de clés)
_groq_key_manager = None

def _get_metadata_llm():
    """Récupère le gestionnaire de clés pour l'extraction de métadonnées."""
    global _groq_key_manager
    if _groq_key_manager is None:
        # Import lazy pour éviter les dépendances circulaires
        from src.core.groq_key_manager import get_groq_key_manager
        _groq_key_manager = get_groq_key_manager()
    return _groq_key_manager

def _extract_advanced_metadata(doc: Document) -> dict:
    """
    Extrait des métadonnées avancées d'un document.
    Utilise soit des modèles locaux (KeyBERT, spaCy, BERTopic, T5) soit un LLM (Groq)
    selon la configuration METADATA_USE_LOCAL_MODELS.
    
    Args:
        doc: Document LangChain à analyser
    
    Returns:
        Dictionnaire avec entities, keywords, topics, summary
    """
    # Vérifier si on doit utiliser les modèles locaux ou le LLM
    use_local_models = getattr(Config, 'METADATA_USE_LOCAL_MODELS', True)
    
    if use_local_models:
        # Utiliser les modèles locaux (KeyBERT, spaCy, BERTopic, T5)
        try:
            from src.rag.local_metadata_extractor import extract_metadata_local
            return extract_metadata_local(doc)
        except ImportError as e:
            print(f"[WARNING] Impossible d'importer local_metadata_extractor: {e}")
            print("[INFO] Fallback sur extraction LLM...")
            # Fallback sur LLM si les modèles locaux ne sont pas disponibles
            use_local_models = False
    
    if not use_local_models:
        # Utiliser le LLM (ancienne méthode)
        return _extract_advanced_metadata_llm(doc)
    
    return {}


def _extract_advanced_metadata_llm(doc: Document) -> dict:
    """
    Extrait des métadonnées avancées d'un document en utilisant le LLM (méthode originale).
    
    Args:
        doc: Document LangChain à analyser
    
    Returns:
        Dictionnaire avec entities, keywords, topics, summary
    """
    advanced_metadata = {}
    
    # Vérifier quelles extractions sont activées
    extract_entities = getattr(Config, 'METADATA_EXTRACT_ENTITIES', True)
    extract_keywords = getattr(Config, 'METADATA_EXTRACT_KEYWORDS', True)
    extract_topics = getattr(Config, 'METADATA_EXTRACT_TOPICS', True)
    extract_summary = getattr(Config, 'METADATA_EXTRACT_SUMMARY', True)
    
    # Si aucune extraction n'est activée, retourner vide
    if not any([extract_entities, extract_keywords, extract_topics, extract_summary]):
        return advanced_metadata
    
    try:
        # Pour les documents complets (tous les chunks concaténés), on peut utiliser plus de texte
        # Limiter à 10000 caractères pour les documents complets (au lieu de 3000 pour un chunk)
        # Cela permet d'avoir un meilleur contexte pour l'extraction de métadonnées via LLM
        max_content_length = 10000 if len(doc.page_content) > 5000 else 3000
        content = doc.page_content[:max_content_length]
        
        if not content.strip():
            return advanced_metadata
        
        # Préparer le prompt pour l'extraction
        max_keywords = getattr(Config, 'METADATA_MAX_KEYWORDS', 5)
        max_entities = getattr(Config, 'METADATA_MAX_ENTITIES', 10)
        max_topics = getattr(Config, 'METADATA_MAX_TOPICS', 3)
        summary_length = getattr(Config, 'METADATA_SUMMARY_MAX_LENGTH', 100)
        
        extraction_prompt = f"""Analyze the following text and extract metadata. Return a JSON object with:
"""
        
        if extract_keywords:
            extraction_prompt += f"- 'keywords': list of {max_keywords} most important keywords (max {max_keywords} items)\n"
        
        if extract_entities:
            extraction_prompt += f"- 'entities': list of named entities (persons, organizations, locations, etc., max {max_entities} items)\n"
        
        if extract_topics:
            extraction_prompt += f"- 'topics': list of {max_topics} main topics/subjects (max {max_topics} items)\n"
        
        if extract_summary:
            extraction_prompt += f"- 'summary': a brief summary in max {summary_length} words\n"
        
        extraction_prompt += f"""
Text to analyze:
{content}

Return only valid JSON, no additional text."""

        # Appeler le LLM avec fallback automatique sur les clés API
        key_manager = _get_metadata_llm()
        response = key_manager.invoke_with_fallback(
            [HumanMessage(content=extraction_prompt)],
            json_mode=True
        )
        
        # Parser la réponse JSON
        if hasattr(response, 'content'):
            extracted_data = json.loads(response.content)
            
            if extract_keywords and 'keywords' in extracted_data:
                keywords = extracted_data['keywords']
                if isinstance(keywords, list):
                    advanced_metadata['keywords'] = keywords[:max_keywords]
            
            if extract_entities and 'entities' in extracted_data:
                entities = extracted_data['entities']
                if isinstance(entities, list):
                    advanced_metadata['entities'] = entities[:max_entities]
            
            if extract_topics and 'topics' in extracted_data:
                topics = extracted_data['topics']
                if isinstance(topics, list):
                    advanced_metadata['topics'] = topics[:max_topics]
            
            if extract_summary and 'summary' in extracted_data:
                summary = extracted_data['summary']
                if isinstance(summary, str):
                    advanced_metadata['summary'] = summary
        
    except json.JSONDecodeError as e:
        print(f"[WARNING] Erreur parsing JSON pour extraction métadonnées: {str(e)}")
    except Exception as e:
        print(f"[WARNING] Erreur lors de l'extraction de métadonnées avancées (LLM): {str(e)}")
        # En cas d'erreur, continuer sans ces métadonnées
    
    return advanced_metadata


def _normalize_metadata_for_chromadb(metadata: dict) -> dict:
    """
    Normalise les métadonnées pour ChromaDB.
    ChromaDB n'accepte que str, int, float, bool, None, SparseVector.
    Convertit les listes en chaînes séparées par des virgules.
    
    Args:
        metadata: Dictionnaire de métadonnées à normaliser
    
    Returns:
        Dictionnaire avec métadonnées normalisées
    """
    normalized = {}
    for key, value in metadata.items():
        if value is None:
            normalized[key] = None
        elif isinstance(value, (str, int, float, bool)):
            normalized[key] = value
        elif isinstance(value, list):
            # Convertir les listes en chaînes séparées par des virgules
            if len(value) > 0:
                # Convertir chaque élément en string et joindre
                normalized[key] = ", ".join(str(item) for item in value)
            else:
                normalized[key] = ""  # Liste vide -> chaîne vide
        elif isinstance(value, dict):
            # Convertir les dicts en JSON string
            normalized[key] = json.dumps(value)
        elif isinstance(value, set):
            # Convertir les sets en chaînes
            normalized[key] = ", ".join(str(item) for item in value)
        else:
            # Pour tout autre type, convertir en string
            normalized[key] = str(value)
    
    return normalized


def enrich_document_metadata(doc_splits: List[Document]) -> List[Document]:
    """
    Enrichit les métadonnées des documents avec des informations structurelles.
    
    OPTIMISATION: Les métadonnées sémantiques (keywords, entities, topics, summary) 
    sont calculées UNE SEULE FOIS par document parent, puis héritées par tous les chunks.
    
    Args:
        doc_splits: Liste de documents (chunks) à enrichir
    
    Returns:
        Liste de documents avec métadonnées enrichies
    """
    if not doc_splits:
        return doc_splits
    
    metadata_enabled = getattr(Config, 'METADATA_ENRICHMENT_ENABLED', True)
    if not metadata_enabled:
        print("[INFO] Enrichissement des métadonnées désactivé")
        return doc_splits
    
    print("[INFO] Enrichissement des métadonnées des documents...")
    print("[INFO] ⚡ Optimisation: métadonnées sémantiques calculées 1x par document (pas par chunk)")
    
    # Grouper les chunks par document parent (basé sur source)
    parent_groups = {}
    for idx, doc in enumerate(doc_splits):
        # Extraire la source avec plusieurs fallbacks pour éviter "unknown_"
        source = doc.metadata.get('source', '')
        if not source or source.startswith('unknown_'):
            # Essayer d'autres métadonnées comme fallback
            source = doc.metadata.get('title', '')
            if not source:
                # Utiliser le parent_doc_id ou chunk_id comme dernier recours
                source = doc.metadata.get('parent_doc_id', '') or doc.metadata.get('chunk_id', '')
            if not source or source.startswith('unknown_'):
                # Dernier recours : utiliser un identifiant basé sur l'index
                source = f'document_{idx}'
        
        if source not in parent_groups:
            parent_groups[source] = []
        parent_groups[source].append((idx, doc))
    
    # Générer un ID unique pour chaque document parent
    parent_ids = {}
    for source in parent_groups:
        parent_ids[source] = str(uuid.uuid4())
    
    # Enrichir chaque document parent (calcul des métadonnées sémantiques)
    enriched_docs = []
    processed_at = datetime.now().isoformat()
    
    # Utiliser tqdm pour la barre de progression si disponible
    groups_iter = tqdm(parent_groups.items(), desc="Enrichissement métadonnées", unit="doc", disable=not TQDM_AVAILABLE) if TQDM_AVAILABLE and len(parent_groups) > 5 else parent_groups.items()
    
    for source, chunks in groups_iter:
        parent_doc_id = parent_ids[source]
        total_chunks = len(chunks)
        
        # ✅ OPTIMISATION: Calculer les métadonnées sémantiques UNE SEULE FOIS pour tout le document
        # En concaténant tous les chunks du document parent
        full_document_text = "\n\n".join([doc.page_content for _, doc in chunks])
        
        # Créer un document temporaire avec le texte complet pour l'extraction
        full_document = Document(
            page_content=full_document_text,
            metadata=chunks[0][1].metadata.copy() if chunks[0][1].metadata else {}
        )
        
        # Extraire les métadonnées sémantiques UNE SEULE FOIS pour le document complet
        semantic_metadata = _extract_advanced_metadata(full_document)
        
        # Maintenant, enrichir chaque chunk avec:
        # 1. Métadonnées structurelles (spécifiques au chunk)
        # 2. Métadonnées sémantiques (héritées du document parent)
        for chunk_index, (original_idx, doc) in enumerate(chunks):
            # Créer une copie des métadonnées existantes
            # ✅ IMPORTANT : Cela préserve automatiquement 'page' (numéro de page des PDFs)
            enriched_metadata = doc.metadata.copy() if doc.metadata else {}

            # 🔴 IMPORTANT : Préserver/normaliser la métadonnée 'source'
            # Toujours s'assurer qu'on a une source valide (pas "unknown_" ou vide)
            current_source = enriched_metadata.get("source", "")
            if not current_source or current_source.startswith('unknown_'):
                enriched_metadata["source"] = source
            # Si la source du groupe est meilleure (pas unknown_), l'utiliser
            elif source and not source.startswith('unknown_') and not source.startswith('document_'):
                enriched_metadata["source"] = source

            # S'assurer qu'on a un titre exploitable pour l'affichage
            # JAMAIS "Unknown source" - toujours un nom valide
            if not enriched_metadata.get("title") or enriched_metadata.get("title") == "Unknown source":
                src_val = enriched_metadata.get("source", "")
                if src_val and not src_val.startswith('unknown_') and not src_val.startswith('document_'):
                    # Vérifier si c'est une URL
                    if src_val.startswith('http://') or src_val.startswith('https://'):
                        # C'est une URL web : formater le nom de la page
                        from urllib.parse import urlparse
                        try:
                            parsed = urlparse(src_val)
                            domain = parsed.netloc.replace('www.', '')
                            path = parsed.path.strip('/').replace('/', ' - ')
                            if path:
                                enriched_metadata["title"] = f"{domain} - {path}"
                            else:
                                enriched_metadata["title"] = domain
                        except:
                            enriched_metadata["title"] = src_val
                    # Vérifier si c'est un chemin de fichier (PDF)
                    elif "/" in src_val or "\\" in src_val:
                        # Extraire le nom de fichier depuis le chemin
                        filename = os.path.basename(src_val.replace("\\", "/"))
                        # Enlever l'extension si c'est un PDF
                        if filename.endswith('.pdf'):
                            filename = filename[:-4]
                        enriched_metadata["title"] = filename
                    else:
                        enriched_metadata["title"] = src_val
                
                # Si toujours pas de titre valide, utiliser un titre générique
                if not enriched_metadata.get("title") or enriched_metadata.get("title") == "Unknown source":
                    enriched_metadata["title"] = f"Document {chunk_index + 1}"
            
            # ✅ Métadonnées structurelles (chunk-level)
            enriched_metadata['chunk_id'] = str(uuid.uuid4())
            enriched_metadata['parent_doc_id'] = parent_doc_id
            enriched_metadata['chunk_index'] = chunk_index
            enriched_metadata['total_chunks'] = total_chunks
            
            # Métadonnées techniques
            enriched_metadata['processed_at'] = processed_at
            if 'created_at' not in enriched_metadata:
                enriched_metadata['created_at'] = processed_at
            
            # Langue (détection simple pour l'instant)
            detect_language = getattr(Config, 'METADATA_DETECT_LANGUAGE', False)
            if detect_language:
                enriched_metadata['language'] = 'en'  # Par défaut
            else:
                enriched_metadata['language'] = 'en'  # Par défaut pour l'instant
            
            # ✅ Métadonnées sémantiques (document-level) - HÉRITÉES du document parent
            # Pas de recalcul, juste héritage
            enriched_metadata.update(semantic_metadata)
            
            # 🔴 IMPORTANT: Normaliser les métadonnées pour ChromaDB
            # ChromaDB n'accepte que str, int, float, bool, None
            # Convertir les listes (keywords, entities, topics) en chaînes
            enriched_metadata = _normalize_metadata_for_chromadb(enriched_metadata)
            
            # Créer un nouveau document avec les métadonnées enrichies
            enriched_doc = Document(
                page_content=doc.page_content,
                metadata=enriched_metadata
            )
            enriched_docs.append((original_idx, enriched_doc))
    
    # Réorganiser selon l'ordre original et retourner uniquement les documents
    enriched_docs.sort(key=lambda x: x[0])
    result = [doc for _, doc in enriched_docs]
    
    print(f"[INFO] ✅ {len(result)} chunks enrichis")
    print(f"[INFO]   - {len(parent_groups)} documents parents traités")
    print(f"[INFO]   - Métadonnées sémantiques calculées {len(parent_groups)} fois (au lieu de {len(result)} fois)")
    
    return result

def get_or_create_chroma_db(doc_splits: List, persist_directory: str = CHROMA_DB_DIR, clear_db: bool = False):
    """ 
    Vérifie si ChromaDB existe déjà et met à jour uniquement avec les nouveaux documents.
    Si clear_db est True, supprime complètement le dossier contenant la base et le recrée.
    """
    # Configuration du device (GPU/CPU)
    device = "cpu"
    try:
        import torch
        if Config.DEVICE_PREFERENCE == "cuda":
            device = "cuda"
            if torch.cuda.is_available():
                print(f"[INFO] CUDA détecté pour ChromaDB: {torch.cuda.get_device_name(0)}")
                print(f"[INFO] Utilisation du GPU pour ChromaDB")
            else:
                print("[WARNING] CUDA non disponible, mais utilisation forcée du GPU (peut causer des erreurs)")
        elif Config.DEVICE_PREFERENCE == "auto":
            if torch.cuda.is_available():
                device = "cuda"
                print(f"[INFO] CUDA détecté pour ChromaDB: {torch.cuda.get_device_name(0)}")
            else:
                print("[INFO] CUDA non disponible pour ChromaDB, utilisation du CPU")
        else:
            print(f"[INFO] Utilisation du CPU (configuré dans Config.DEVICE_PREFERENCE)")
    except Exception as e:
        if Config.DEVICE_PREFERENCE == "cuda":
            device = "cuda"
            print(f"[WARNING] Erreur détection CUDA: {e}, mais utilisation forcée du GPU")
        else:
            print(f"[INFO] Détection CUDA impossible: {e}, utilisation du CPU")
    
    embedding_model = NomicEmbeddings(
        model=Config.NomicEmbeddings_model, 
        inference_mode="local", 
        device=device
    )

    # 🔴 Si clear_db est True, on supprime totalement le dossier
    if clear_db:
        print(f"[INFO] Suppression complète de ChromaDB dans {persist_directory}...")
        # Supprimer le dossier s'il existe, ignorer l'erreur s'il n'existe pas
        shutil.rmtree(persist_directory, ignore_errors=True)
        print("[INFO] ChromaDB supprimée (ou n'existait pas). Recréation en cours...")
        vectorstore = Chroma.from_documents(
            documents=doc_splits,
            embedding=embedding_model,
            persist_directory=persist_directory
        )

    else:
        # 💡 La base existe déjà → Chargement sans recréation
        print("[INFO] ChromaDB déjà existante. Chargement en cours...")
        vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embedding_model)
        print("[INFO] ChromaDB chargée.")

    return vectorstore


def load_pdf_documents_from_folder(folder_path: str):
    """Charge tous les fichiers PDF présents dans un dossier donné."""
    
    pdf_paths = [
        os.path.join(folder_path, file)
        for file in os.listdir(folder_path)
        if file.endswith(".pdf")
    ]

    return load_pdf_documents(pdf_paths)

class EnsembleRetriever:
    """
    Implémentation personnalisée d'EnsembleRetriever pour combiner plusieurs retrievers.
    Combine les résultats de plusieurs retrievers avec des poids.
    """
    def __init__(self, retrievers, weights=None):
        """
        Args:
            retrievers: Liste de retrievers à combiner
            weights: Liste de poids pour chaque retriever (doit sommer à 1.0)
        """
        self.retrievers = retrievers
        if weights is None:
            # Poids égaux par défaut
            self.weights = [1.0 / len(retrievers)] * len(retrievers)
        else:
            self.weights = weights
            # Normaliser les poids pour qu'ils somment à 1.0
            total = sum(self.weights)
            if total > 0:
                self.weights = [w / total for w in self.weights]
    
    def get_relevant_documents(self, query: str):
        """Récupère les documents pertinents en combinant les résultats des retrievers."""
        from collections import defaultdict
        import hashlib
        
        # Récupérer les documents de chaque retriever
        doc_scores = defaultdict(float)
        doc_objects = {}
        
        for retriever, weight in zip(self.retrievers, self.weights):
            try:
                docs = retriever.get_relevant_documents(query)
                # Attribuer un score basé sur la position et le poids
                for i, doc in enumerate(docs):
                    # Créer un identifiant unique basé sur le contenu et les métadonnées
                    # Utiliser hash pour identifier les documents similaires
                    doc_content = doc.page_content[:100]  # Premiers 100 caractères
                    doc_source = doc.metadata.get('source', '')
                    doc_key = f"{doc_content}_{doc_source}"
                    doc_hash = hashlib.md5(doc_key.encode()).hexdigest()
                    
                    # Score décroissant avec la position (premier = meilleur)
                    # Plus le document est haut dans les résultats, plus son score est élevé
                    score = weight * (1.0 / (i + 1))
                    doc_scores[doc_hash] += score
                    if doc_hash not in doc_objects:
                        doc_objects[doc_hash] = doc
            except Exception as e:
                print(f"[WARNING] Erreur dans un retriever: {e}")
                continue
        
        # Trier par score décroissant
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Retourner les documents dans l'ordre de score
        result = [doc_objects[doc_hash] for doc_hash, _ in sorted_docs]
        
        return result
    
    def invoke(self, query: str, **kwargs):
        """Méthode invoke pour compatibilité avec LangChain."""
        return self.get_relevant_documents(query)


def get_retriever(k: int = 3, use_hybrid: bool = None):
    """
    Crée un retriever pour récupérer les documents les plus pertinents.
    
    Args:
        k: Nombre de documents à retourner
        use_hybrid: Si True, utilise hybrid search (vector + BM25). 
                    Si None, utilise la config HYBRID_SEARCH_ENABLED
    """
    from langchain_community.retrievers import BM25Retriever
    
    # Utiliser la config si use_hybrid n'est pas spécifié
    if use_hybrid is None:
        use_hybrid = getattr(Config, 'HYBRID_SEARCH_ENABLED', True)
    
    # Répertoire pour ChromaDB
    chroma_db_path = CHROMA_DB_DIR
    
    # Vérifier si ChromaDB existe déjà
    if os.path.exists(chroma_db_path) and os.listdir(chroma_db_path):
        # Si ChromaDB existe, juste charger le retriever sans recharger les documents
        print("[INFO] ChromaDB existe. Chargement du retriever uniquement...")
        
        # Configuration du device (GPU/CPU)
        device = "cpu"
        try:
            import torch
            if Config.DEVICE_PREFERENCE == "cuda":
                device = "cuda"
                if torch.cuda.is_available():
                    print(f"[INFO] CUDA détecté: {torch.cuda.get_device_name(0)}")
                    print(f"[INFO] Utilisation du GPU")
                else:
                    print("[WARNING] CUDA non disponible, mais utilisation forcée du GPU (peut causer des erreurs)")
            elif Config.DEVICE_PREFERENCE == "auto":
                if torch.cuda.is_available():
                    device = "cuda"
                    print(f"[INFO] CUDA détecté: {torch.cuda.get_device_name(0)}")
                else:
                    print("[INFO] CUDA non disponible, utilisation du CPU")
            else:
                print(f"[INFO] Utilisation du CPU (configuré dans Config.DEVICE_PREFERENCE)")
        except ImportError:
            if Config.DEVICE_PREFERENCE == "cuda":
                device = "cuda"
                print("[WARNING] PyTorch non disponible, mais tentative d'utilisation du GPU")
            else:
                print("[INFO] PyTorch non disponible, utilisation du CPU")
        except Exception as e:
            if Config.DEVICE_PREFERENCE == "cuda":
                device = "cuda"
                print(f"[WARNING] Erreur détection CUDA: {str(e)}, mais tentative d'utilisation du GPU")
            else:
                print(f"[INFO] Erreur détection CUDA: {str(e)}, utilisation du CPU")
        
        embedding_model = NomicEmbeddings(
            model=Config.NomicEmbeddings_model, 
            inference_mode="local", 
            device=device
        )
        vectorstore = Chroma(persist_directory=chroma_db_path, embedding_function=embedding_model)
        print(f"[INFO] Vectorstore charge depuis ChromaDB existante (device: {device}).")
        
        # Créer le retriever vectoriel
        vector_retriever = vectorstore.as_retriever(search_kwargs={"k": k})
        
        # Si hybrid search est activé, créer ensemble retriever
        if use_hybrid:
            print("[INFO] Activation du Hybrid Search (Vector + BM25)...")
            
            # Essayer d'abord de charger depuis le cache pickle
            bm25_documents = _load_bm25_documents()
            
            if bm25_documents:
                print("[INFO] Documents BM25 charges depuis le cache")
            else:
                # Fallback: essayer de charger depuis ChromaDB
                print("[INFO] Cache BM25 non trouve, tentative de chargement depuis ChromaDB...")
                try:
                    all_docs = vectorstore.get()
                    if all_docs and 'documents' in all_docs and len(all_docs['documents']) > 0:
                        # Créer des Document objects à partir des données ChromaDB
                        from langchain_core.documents import Document
                        bm25_documents = []
                        for i, doc_text in enumerate(all_docs['documents']):
                            metadata = all_docs.get('metadatas', [{}])[i] if 'metadatas' in all_docs else {}
                            bm25_documents.append(Document(page_content=doc_text, metadata=metadata))
                        print("[INFO] Documents BM25 charges depuis ChromaDB")
                    else:
                        raise ValueError("Pas de documents dans ChromaDB")
                except Exception as e:
                    print(f"[WARNING] Impossible de charger les documents pour BM25: {str(e)}")
                    print("[INFO] Utilisation du retriever vectoriel uniquement")
                    return vector_retriever
            
            # Créer le retriever BM25 avec les documents chargés
            try:
                bm25_retriever = BM25Retriever.from_documents(bm25_documents)
                bm25_retriever.k = k
                
                # Créer l'ensemble retriever avec poids
                vector_weight = getattr(Config, 'VECTOR_SEARCH_WEIGHT', 0.7)
                bm25_weight = getattr(Config, 'BM25_SEARCH_WEIGHT', 0.3)
                
                ensemble_retriever = EnsembleRetriever(
                    retrievers=[vector_retriever, bm25_retriever],
                    weights=[vector_weight, bm25_weight]
                )
                
                print(f"[INFO] Hybrid Search configure (Vector: {vector_weight*100}%, BM25: {bm25_weight*100}%)")
                return ensemble_retriever
            except Exception as e:
                print(f"[WARNING] Erreur lors de la creation du retriever BM25: {str(e)}")
                print("[INFO] Utilisation du retriever vectoriel uniquement")
                return vector_retriever
        else:
            print("[INFO] Hybrid Search desactive, utilisation du retriever vectoriel uniquement")
            return vector_retriever
    
    # Si ChromaDB n'existe pas, charger et indexer les documents
    print("[INFO] ChromaDB n'existe pas. Chargement des documents...")
    print("[INFO] ⏳ Cette étape peut prendre plusieurs minutes la première fois...")
    
    # Charger les documents web
    print("[INFO] Chargement des documents web...")
    try:
        web_docs = load_web_documents(urls)
        print(f"[INFO] {len(web_docs)} documents web chargés.")
    except Exception as e:
        print(f"⚠️ Erreur lors du chargement des documents web: {str(e)}")
        web_docs = []
    
    # Charger automatiquement tous les PDFs du dossier "data/raw"
    raw_data_folder = os.path.join(project_root, "data", "raw")
    pdf_docs = []
    if os.path.exists(raw_data_folder):
        try:
            pdf_docs = load_pdf_documents_from_folder(raw_data_folder)
            print(f"[INFO] {len(pdf_docs)} documents PDF chargés.")
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement des PDFs: {str(e)}")
    else:
        print(f"[INFO] Dossier {raw_data_folder} n'existe pas. Aucun PDF chargé.")
    
    # Fusionner les deux listes de documents
    all_docs = web_docs + pdf_docs
    
    if not all_docs:
        raise Exception("Aucun document trouvé à indexer. Vérifiez vos sources de documents.")
    
    # Diviser les documents en segments
    print("[INFO] Segmentation des documents...")
    doc_splits = split_documents(all_docs)
    print(f"[INFO] {len(doc_splits)} chunks créés.")
    
    # Créer la base ChromaDB
    print("[INFO] Création de la base vectorielle ChromaDB...")
    vectorstore = get_or_create_chroma_db(doc_splits, CHROMA_DB_DIR, clear_db=False)
    print("[INFO] ChromaDB créée avec succès.")
    
    # Sauvegarder les documents pour BM25 cache
    _save_bm25_documents(doc_splits)
    
    # Créer le retriever vectoriel
    vector_retriever = vectorstore.as_retriever(search_kwargs={"k": k})
    
    # Si hybrid search est activé, créer ensemble retriever
    if use_hybrid:
        print("[INFO] Activation du Hybrid Search (Vector + BM25)...")
        try:
            # Créer le retriever BM25 avec les documents splits
            bm25_retriever = BM25Retriever.from_documents(doc_splits)
            bm25_retriever.k = k
            
            # Créer l'ensemble retriever avec poids
            vector_weight = getattr(Config, 'VECTOR_SEARCH_WEIGHT', 0.7)
            bm25_weight = getattr(Config, 'BM25_SEARCH_WEIGHT', 0.3)
            
            ensemble_retriever = EnsembleRetriever(
                retrievers=[vector_retriever, bm25_retriever],
                weights=[vector_weight, bm25_weight]
            )
            
            print(f"[INFO] Hybrid Search configure (Vector: {vector_weight*100}%, BM25: {bm25_weight*100}%)")
            return ensemble_retriever
        except Exception as e:
            print(f"[WARNING] Erreur lors de la creation du retriever BM25: {str(e)}")
            print("[INFO] Utilisation du retriever vectoriel uniquement")
            return vector_retriever
    else:
        print("[INFO] Hybrid Search desactive, utilisation du retriever vectoriel uniquement")
        return vector_retriever


if __name__ == "__main__":
    retriever = get_retriever()
    #print(retriever.search("What is a transformer?"))