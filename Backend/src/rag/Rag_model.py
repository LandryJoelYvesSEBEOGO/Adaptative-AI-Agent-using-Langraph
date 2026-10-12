# Import necessary libraries
import os 
import sys
import time
import re
from typing import Tuple
from urllib.parse import urlparse
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.tools.tavily_search.tool import TavilySearchResults
from langgraph.graph import StateGraph, END
from IPython.display import Image, display
from langchain_core.documents import Document
from typing import List, Annotated, Dict, Optional, Callable
from typing_extensions import TypedDict
from sentence_transformers import CrossEncoder
import json
import operator

# Ajouter le répertoire racine du projet au sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.Config import Config
from src.rag.Prompts import get_prompts
from src.rag.Data_processing import get_retriever
from src.core.exceptions import (
    RetrievalException,
    LLMAPIException,
    LLMTimeoutException,
    LLMQuotaException,
    InvalidResponseException,
    MaxRetriesException,
    WebSearchException,
    HallucinationDetectedException,
    ValidationException,
    GenerationException,  # ✅ utilisé pour les erreurs de génération (streaming et non-streaming)
)
import uuid
from src.core.metrics import get_metrics_collector
from src.core.retrieval_metrics import get_retrieval_metrics_collector
from src.core.logger import get_logger
from src.core.retry_policy import (
    retry_with_backoff_advanced,
    get_circuit_breaker
)
from src.core.recovery_strategies import RecoveryStrategy
from src.core.fallback import get_fallback_manager
from src.core.groq_key_manager import get_groq_key_manager

# Initialiser logger et metrics
logger = get_logger()
metrics = get_metrics_collector()
# Load environment variables
load_dotenv()

# Gestionnaire de clés API Groq avec rotation automatique
groq_key_manager = get_groq_key_manager()

# Circuit breakers pour différents services
llm_circuit_breaker = get_circuit_breaker("llm") if getattr(Config, 'CIRCUIT_BREAKER_ENABLED', True) else None
web_search_circuit_breaker = get_circuit_breaker("web_search") if getattr(Config, 'CIRCUIT_BREAKER_ENABLED', True) else None
retrieval_circuit_breaker = get_circuit_breaker("retrieval") if getattr(Config, 'CIRCUIT_BREAKER_ENABLED', True) else None

# Fallback manager
fallback_manager = get_fallback_manager() if getattr(Config, 'FALLBACK_MODELS_ENABLED', True) else None

# LLM legacy (pour compatibilité, mais utiliser groq_key_manager de préférence)
local_llm = groq_key_manager.get_current_llm(json_mode=False)
llm_json_mode = groq_key_manager.get_current_llm(json_mode=True)

# Dans Rag_model.py, remplacez la ligne 48:
# retriever = get_retriever()

# Par une initialisation lazy:
_retriever = None

def get_retriever_instance():
    """Récupère ou crée le retriever (lazy loading pour éviter blocage à l'import)."""
    global _retriever
    if _retriever is None:
        print("[INIT] ⏳ Initialisation du retriever (première fois, peut prendre du temps)...")
        try:
            # Si reranker activé, récupérer plus de documents pour le reranking
            reranker_enabled = getattr(Config, 'RERANKER_ENABLED', True)
            if reranker_enabled:
                reranker_top_k = getattr(Config, 'RERANKER_TOP_K', 20)
                _retriever = get_retriever(k=reranker_top_k)
                print(f"[INIT] ✅ Retriever créé avec k={reranker_top_k} (pour reranking).")
            else:
                final_k = getattr(Config, 'RERANKER_FINAL_K', 3)
                _retriever = get_retriever(k=final_k)
                print(f"[INIT] ✅ Retriever créé avec k={final_k}.")
            
            # IMPORTANT: Précharger le modèle d'embedding pour éviter le blocage au premier appel
            # Cela force le chargement du modèle en mémoire maintenant plutôt que lors du premier invoke
            print("[INIT] ⏳ Préchargement du modèle d'embedding (peut prendre 10-30s)...")
            try:
                start_preload = time.time()
                # Faire un appel test pour précharger le modèle
                test_docs = _retriever.invoke("test preload")
                preload_time = time.time() - start_preload
                print(f"[INIT] ✅ Modèle préchargé avec succès en {preload_time:.2f}s")
                print("[INIT] Le retriever est maintenant prêt à être utilisé sans blocage.")
            except Exception as preload_error:
                print(f"⚠️ [INIT] Attention: Échec du préchargement: {str(preload_error)}")
                print("[INIT] Le retriever sera initialisé lors du premier appel réel.")
                # On continue quand même, le retriever sera initialisé au premier appel
                
        except Exception as e:
            print(f"❌ [INIT] Erreur lors de l'initialisation du retriever: {str(e)}")
            raise
    return _retriever

web_search_tool = TavilySearchResults(k=3, tavily_api_key=Config.TAVILY_API_KEY)

# Load prompts
prompt = get_prompts()

# Fonction helper pour retry avec backoff (conservée pour compatibilité)
def retry_with_backoff(func: Callable, max_retries: int = None, 
                      initial_delay: int = None) -> any:
    """Retry une fonction avec backoff exponentiel (wrapper pour compatibilité)."""
    # Utiliser la version avancée si activée
    if getattr(Config, 'CIRCUIT_BREAKER_ENABLED', True) or getattr(Config, 'RETRY_JITTER_ENABLED', True):
        # Déterminer quel circuit breaker utiliser selon le contexte
        circuit_breaker = None  # Peut être défini selon le contexte
        
        return retry_with_backoff_advanced(
            func,
            max_retries=max_retries,
            initial_delay=initial_delay,
            circuit_breaker=circuit_breaker
        )
    else:
        # Ancienne implémentation simple
        if max_retries is None:
            max_retries = getattr(Config, 'MAX_RETRIES', 3)
        if initial_delay is None:
            initial_delay = getattr(Config, 'RETRY_INITIAL_DELAY', 1)
        
        backoff_factor = getattr(Config, 'RETRY_BACKOFF_FACTOR', 2)
        
        for attempt in range(max_retries):
            try:
                return func()
            except (LLMTimeoutException, LLMQuotaException, Exception) as e:
                if attempt == max_retries - 1:
                    raise
                delay = initial_delay * (backoff_factor ** attempt)
                print(f"⚠️ Tentative {attempt + 1}/{max_retries} échouée. Retry dans {delay}s...")
                time.sleep(delay)
        raise MaxRetriesException(f"Échec après {max_retries} tentatives")

def get_llm_with_fallback():
    """
    Récupère le LLM actuel, avec fallback automatique si activé.
    Utilise le gestionnaire de clés API pour la rotation automatique.
    """
    if fallback_manager and getattr(Config, 'FALLBACK_MODELS_ENABLED', True):
        llm = fallback_manager.get_current_llm()
        if llm:
            return llm
    
    # Utiliser le gestionnaire de clés API (rotation automatique en cas de rate limit)
    return groq_key_manager.get_current_llm(json_mode=False)

def get_llm_json_with_fallback():
    """
    Récupère le LLM en mode JSON avec fallback automatique.
    Utilise le gestionnaire de clés API pour la rotation automatique.
    """
    if fallback_manager and getattr(Config, 'FALLBACK_MODELS_ENABLED', True):
        current_llm = fallback_manager.get_current_llm()
        if current_llm:
            # Utiliser le gestionnaire de clés pour créer le LLM JSON
            return groq_key_manager.get_current_llm(json_mode=True)
    
    # Utiliser le gestionnaire de clés API (rotation automatique en cas de rate limit)
    return groq_key_manager.get_current_llm(json_mode=True)

def Rewrite_query(query: str, history: Optional[str] = None) -> str:
    """Rewrite the query to be more specific, using optional conversation history."""
    try:
        print("---Rewrite the query---")
        if not query or not query.strip():
            return query
        
        rewritting_prompt_formatted = prompt["Rewritting_prompt"].format(
            query=query,
            history=history or ""
        )
        
        def _call_llm():
            # Utiliser le gestionnaire de clés avec fallback automatique
            return groq_key_manager.invoke_with_fallback(
                [HumanMessage(content=rewritting_prompt_formatted)],
                json_mode=False
            )
        
        generation = retry_with_backoff_advanced(
            _call_llm,
            circuit_breaker=llm_circuit_breaker
        )
        
        if hasattr(generation, "content"):
            return generation.content
        elif isinstance(generation, str):
            return generation
        else:
            raise InvalidResponseException(
                "Format de réponse invalide lors de la réécriture de la requête",
                {"query": query, "response_type": type(generation).__name__}
            )
    except Exception as e:
        # En cas d'erreur, retourner la query originale
        print(f"⚠️ Erreur lors de la réécriture: {str(e)}. Utilisation de la requête originale.")
        return query


# Post-processing function for formatting documents
def format_docs(docs, with_citations: bool = True):
    """
    Format documents for display with optional citation numbers.
    
    Args:
        docs: Liste de documents
        with_citations: Si True, ajoute des numéros de référence [1], [2], etc.
    
    Returns:
        String formatée avec les documents
    """
    if not docs:
        return ""
    
    if not with_citations:
        return "\n\n".join(doc.page_content for doc in docs if hasattr(doc, 'page_content'))
    
    formatted_parts = []
    for idx, doc in enumerate(docs, start=1):
        if hasattr(doc, 'page_content'):
            content = f"[Document {idx}]\n{doc.page_content}"
            formatted_parts.append(content)
    
    return "\n\n".join(formatted_parts)



def extract_sources_from_documents(documents: List[Document]) -> List[Dict[str, str]]:
    """
    Extrait les informations de source de chaque document, incluant le numéro de page.
    
    Args:
        documents: Liste de documents LangChain
    
    Returns:
        Liste de dictionnaires avec les infos de source (incluant page si disponible)
    """
    sources = []
    for idx, doc in enumerate(documents, start=1):
        metadata = doc.metadata if hasattr(doc, 'metadata') else {}
        
        # DEBUG: Afficher les métadonnées pour comprendre le problème
        # (à désactiver en production)
        if getattr(Config, 'DEBUG_METADATA', False):
            print(f"[DEBUG] Document {idx} metadata: {metadata}")
        
        # Extraire le numéro de page (PyPDFLoader utilise 'page', parfois 'page_number')
        page_number = None
        if 'page' in metadata:
            page_number = metadata.get('page')
            # Si c'est un index (0-based), convertir en numéro de page (1-based)
            if isinstance(page_number, int) and page_number >= 0:
                page_number = page_number + 1  # Convertir de 0-based à 1-based
        elif 'page_number' in metadata:
            page_number = metadata.get('page_number')
        
        # Extraire la source brute depuis les métadonnées (essayer plusieurs clés)
        raw_source = (
            metadata.get('source', '') or 
            metadata.get('source_path', '') or 
            metadata.get('file_path', '') or
            ''
        )
        
        # DEBUG: Afficher les métadonnées pour comprendre le problème
        if getattr(Config, 'DEBUG_METADATA', False):
            print(f"\n[DEBUG] Document {idx}:")
            print(f"  - raw_source: {raw_source}")
            print(f"  - title: {metadata.get('title', 'N/A')}")
            print(f"  - metadata keys: {list(metadata.keys())}")
            print(f"  - full metadata: {metadata}")
        
        # Déterminer le nom d'affichage (titre) avec logique intelligente
        display_name = metadata.get('title', '')
        
        # Nettoyer le titre s'il est invalide (détecter tous les "Document N")
        import re
        is_invalid_title = (
            not display_name or
            display_name == 'Unknown source' or
            display_name.startswith('unknown_') or
            display_name.startswith('document_') or
            re.match(r'^Document \d+$', display_name) is not None  # Détecte "Document 1", "Document 2", etc.
        )
        if is_invalid_title:
            display_name = ''
        
        # Si pas de titre valide, extraire depuis la source
        if not display_name:
            if raw_source and raw_source not in ['Unknown source', ''] and not raw_source.startswith('unknown_'):
                # Vérifier si c'est une URL
                if raw_source.startswith('http://') or raw_source.startswith('https://'):
                    # C'est une URL web : formater le nom de la page
                    try:
                        parsed = urlparse(raw_source)
                        # Créer un nom lisible : domaine + chemin simplifié
                        domain = parsed.netloc.replace('www.', '')
                        path = parsed.path.strip('/').replace('/', ' - ')
                        if path:
                            display_name = f"{domain} - {path}"
                        else:
                            display_name = domain
                    except:
                        display_name = raw_source
                # Vérifier si c'est un chemin de fichier (PDF)
                elif '/' in raw_source or '\\' in raw_source:
                    # C'est un fichier : extraire le nom sans extension
                    filename = os.path.basename(raw_source.replace('\\', '/'))
                    if filename.endswith('.pdf'):
                        display_name = filename[:-4]  # Enlever .pdf
                    else:
                        display_name = filename
                else:
                    # Source simple, l'utiliser directement
                    display_name = raw_source
        
        # Si toujours pas de nom valide après tous les essais
        if not display_name or display_name in ['Unknown source', 'Document 1', 'Document 2', 'Document 3'] or re.match(r'^Document \d+$', display_name):
            # Essayer d'autres métadonnées comme dernier recours
            # Chercher dans toutes les métadonnées pour trouver un chemin ou un nom
            for key, value in metadata.items():
                if value and isinstance(value, str):
                    # Si on trouve un chemin de fichier dans n'importe quelle métadonnée
                    if ('/' in value or '\\' in value) and (value.endswith('.pdf') or '.pdf' in value):
                        filename = os.path.basename(value.replace('\\', '/'))
                        if filename.endswith('.pdf'):
                            display_name = filename[:-4]
                        else:
                            display_name = filename
                        break
                    # Si on trouve une URL
                    elif value.startswith('http://') or value.startswith('https://'):
                        try:
                            parsed = urlparse(value)
                            domain = parsed.netloc.replace('www.', '')
                            path = parsed.path.strip('/').replace('/', ' - ')
                            if path:
                                display_name = f"{domain} - {path}"
                            else:
                                display_name = domain
                            break
                        except:
                            pass
            
            # Si toujours rien, utiliser le numéro de page si disponible
            if not display_name or display_name in ['Unknown source', 'Document 1', 'Document 2', 'Document 3'] or re.match(r'^Document \d+$', display_name):
                if page_number is not None:
                    display_name = f'Document (page {page_number})'
                else:
                    # Utiliser l'index mais seulement en dernier recours
                    display_name = f'Document {idx}'
        
        # Pour la source technique, garder la source brute ou utiliser le display_name
        source = raw_source if raw_source and not raw_source.startswith('unknown_') else display_name
        
        source_info = {
            "number": idx,
            "source": source,
            "parent_doc_id": metadata.get('parent_doc_id', ''),
            "chunk_id": metadata.get('chunk_id', ''),
            "title": display_name,  # Utiliser le nom d'affichage calculé
            "page": page_number  # Ajouter le numéro de page
        }
        sources.append(source_info)
    return sources


def format_citations(response: str, sources: List[Dict[str, str]]) -> Tuple[str, str]:
    """
    Parse les citations dans la réponse et formate les références.
    
    Args:
        response: Réponse générée avec citations [1], [2], etc.
        sources: Liste des sources extraites des documents
    
    Returns:
        Tuple (response_with_citations, references_section)
    """
    if not sources:
        return response, ""
    
    # Extraire les numéros de citations utilisés (ex: [1], [2], [12])
    citation_pattern = r'\[(\d+)\]'
    citations_used = set()
    
    def replace_citation(match):
        num = int(match.group(1))
        if 1 <= num <= len(sources):
            citations_used.add(num)
            return f'[{num}]'
        return match.group(0)
    
    # Remplacer les citations par des références formatées
    response_formatted = re.sub(citation_pattern, replace_citation, response)
    
    # Créer la section des références
    if citations_used:
        references_parts = ["\n\n**Références:**"]
        for num in sorted(citations_used):
            source_info = sources[num - 1]  # -1 car les indices commencent à 0
            
            # Déterminer le nom à afficher (toujours utiliser le titre calculé)
            source_display = source_info.get('title', '')
            
            # Si le titre n'est pas valide, extraire depuis la source
            if not source_display or source_display == 'Unknown source' or source_display.startswith('unknown_'):
                source_path = source_info.get('source', '')
                if source_path:
                    # Vérifier si c'est une URL
                    if source_path.startswith('http://') or source_path.startswith('https://'):
                        try:
                            parsed = urlparse(source_path)
                            domain = parsed.netloc.replace('www.', '')
                            path = parsed.path.strip('/').replace('/', ' - ')
                            if path:
                                source_display = f"{domain} - {path}"
                            else:
                                source_display = domain
                        except:
                            source_display = source_path
                    # Vérifier si c'est un chemin de fichier
                    elif '/' in source_path or '\\' in source_path:
                        filename = os.path.basename(source_path.replace('\\', '/'))
                        if filename.endswith('.pdf'):
                            source_display = filename[:-4]
                        else:
                            source_display = filename
                    else:
                        source_display = source_path
                else:
                    source_display = f'Document {num}'
            
            # S'assurer qu'on n'a jamais "Unknown source"
            if source_display == 'Unknown source' or source_display.startswith('unknown_'):
                source_display = f'Document {num}'
            
            # Ajouter le numéro de page si disponible
            page_number = source_info.get('page')
            if page_number is not None:
                # Formater avec le numéro de page
                references_parts.append(f"[{num}] {source_display} (page {page_number})")
            else:
                references_parts.append(f"[{num}] {source_display}")
        
        references_section = "\n".join(references_parts)
    else:
        references_section = ""
    
    return response_formatted, references_section


# GraphState definition
class GraphState(TypedDict):
    question: str
    generation: str
    web_search: str
    max_retries: int
    answers: int
    loop_step: Annotated[int, operator.add]
    documents: List[str]
    error_history: List[str]  # Nouveau : historique des erreurs
    conversation_id: Optional[str]  # ID de conversation pour métriques
    latencies: Optional[Dict[str, float]]  # Latences pour métriques
    answer_quality_scores: Optional[Dict]  # Scores de qualité de la réponse

# Reranker global (lazy loading)
_reranker = None

def get_reranker_instance():
    """Récupère ou crée le reranker cross-encoder (lazy loading)."""
    global _reranker
    if _reranker is None:
        reranker_enabled = getattr(Config, 'RERANKER_ENABLED', True)
        if not reranker_enabled:
            return None
        
        reranker_model = getattr(Config, 'RERANKER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
        print(f"[RERANKER] ⏳ Initialisation du reranker: {reranker_model}...")
        try:
            _reranker = CrossEncoder(reranker_model)
            print("[RERANKER] ✅ Reranker initialisé avec succès")
        except Exception as e:
            print(f"[RERANKER] ❌ Erreur lors de l'initialisation: {str(e)}")
            print("[RERANKER] Le reranking sera désactivé pour cette session")
            return None
    return _reranker

def rerank_documents(query: str, documents: List[Document], top_k: int = None) -> List[Document]:
    """
    Rerank les documents avec un cross-encoder.
    
    Args:
        query: La question de l'utilisateur
        documents: Liste de documents à reranker
        top_k: Nombre de documents à retourner après reranking
    
    Returns:
        Liste de documents rerankés (top_k premiers)
    """
    if not documents or len(documents) == 0:
        return documents
    
    reranker = get_reranker_instance()
    if reranker is None:
        # Si reranker non disponible, retourner les documents originaux
        return documents[:top_k] if top_k else documents
    
    if top_k is None:
        top_k = getattr(Config, 'RERANKER_FINAL_K', 3)
    
    try:
        # Préparer les paires (query, document) pour le cross-encoder
        pairs = [[query, doc.page_content] for doc in documents]
        
        # Calculer les scores de pertinence
        scores = reranker.predict(pairs)
        
        # Créer une liste de tuples (score, document) et trier par score décroissant
        scored_docs = list(zip(scores, documents))
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        
        # Retourner les top_k documents
        reranked_docs = [doc for _, doc in scored_docs[:top_k]]
        
        return reranked_docs
        
    except Exception as e:
        print(f"[RERANKER] ⚠️ Erreur lors du reranking: {str(e)}")
        print("[RERANKER] Retour des documents originaux (sans reranking)")
        return documents[:top_k] if top_k else documents

        
# Node functions
def retrieve(state: Dict) -> Dict:
    """Retrieve documents from the vector store."""
    start_time = time.time()
    conversation_id = state.get("conversation_id", "unknown")
    latencies = state.get("latencies", {})
    
    try:
        logger.info("Retrieval started", extra={"component": "retrieval", "conversation_id": conversation_id})
        print("---RETRIEVE---")
        if not state.get("question"):
            raise RetrievalException("Question manquante pour la récupération")
        
        print(f"[RETRIEVE] Recherche de documents pour: {state['question'][:50]}...")
        
        # Obtenir le retriever (lazy loading)
        print("[RETRIEVE] Obtention du retriever...")
        current_retriever = get_retriever_instance()
        print("[RETRIEVE] ✅ Retriever obtenu.")
        
        print("[RETRIEVE] Appel retriever.invoke()...")
        print("[RETRIEVE] Cette etape va:")
        print("[RETRIEVE]   1. Generer l'embedding de la question")
        print("[RETRIEVE]   2. Rechercher dans ChromaDB")
        print("[RETRIEVE] ⏳ Veuillez patienter...")
        
        # IMPORTANT: LangGraph exécute les nœuds directement, sans threading supplémentaire
        # Le threading peut causer des conflits avec le runtime de LangGraph
        # Appel direct: si ça bloque, c'est que le problème vient de NomicEmbeddings/ChromaDB
        try:
            # Déterminer les paramètres du reranker
            reranker_enabled = getattr(Config, 'RERANKER_ENABLED', True)
            final_k = getattr(Config, 'RERANKER_FINAL_K', 3)
            
            # Le retriever a déjà été configuré avec le bon k dans get_retriever_instance
            print("[RETRIEVE] ⏳ Début de retriever.invoke()...")
            documents = current_retriever.invoke(state["question"])
            
            # Appliquer le reranking si activé
            if reranker_enabled and len(documents) > 1:
                print(f"[RETRIEVE] ⏳ Reranking de {len(documents)} documents (top-{final_k})...")
                rerank_start = time.time()
                documents = rerank_documents(state["question"], documents, top_k=final_k)
                rerank_time = time.time() - rerank_start
                latencies["reranking"] = rerank_time
                print(f"[RETRIEVE] ✅ Reranking terminé en {rerank_time:.3f}s ({len(documents)} documents finaux)")
            elif not reranker_enabled:
                # Si reranker désactivé, prendre les k premiers
                documents = documents[:final_k]
            
            elapsed_time = time.time() - start_time
            latencies["retrieval"] = elapsed_time
            print(f"[RETRIEVE] ✅ retriever.invoke() terminé avec succès en {elapsed_time:.2f}s")
        except Exception as e:
            elapsed_time = time.time() - start_time
            latencies["retrieval"] = elapsed_time
            print(f"[RETRIEVE] ❌ Exception apres {elapsed_time:.2f}s: {type(e).__name__}: {str(e)}")
            import traceback
            print("[RETRIEVE] Stack trace complete:")
            traceback.print_exc()
            raise RetrievalException(f"Erreur lors de l'invocation du retriever: {str(e)}") from e
        
        if documents is None:
            print("❌ [RETRIEVE] Aucun resultat retourne (None)")
            raise RetrievalException("Aucun resultat retourne par le retriever")
        
        if not documents or len(documents) == 0:
            print("⚠️ [RETRIEVE] Aucun document trouve")
            logger.warning(
                "No documents found",
                extra={"component": "retrieval", "conversation_id": conversation_id}
            )
            return {
                "documents": [],
                "error_history": state.get("error_history", []) + ["Aucun document trouve"],
                "latencies": latencies,
                "question": state.get("question"),  # Préserver la question
                "conversation_id": conversation_id
            }
        
        print(f"[RETRIEVE] ✅ {len(documents)} documents trouves en {elapsed_time:.2f}s.")
        
        # Enregistrer les résultats de retrieval pour les métriques
        retrieval_metrics_enabled = getattr(Config, 'RETRIEVAL_METRICS_ENABLED', True)
        if retrieval_metrics_enabled:
            try:
                retrieval_collector = get_retrieval_metrics_collector()
                # Extraire les IDs des documents récupérés
                retrieved_doc_ids = []
                retrieved_sources = []
                for doc in documents:
                    # Utiliser parent_doc_id si disponible, sinon chunk_id, sinon source
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
            except Exception as e:
                # Ne pas faire échouer le retrieval si l'enregistrement échoue
                print(f"[WARNING] Erreur lors de l'enregistrement des métriques retrieval: {str(e)}")
        
        logger.info(
            "Retrieval completed",
            extra={
                "component": "retrieval",
                "conversation_id": conversation_id,
                "data": {"latency": elapsed_time, "num_documents": len(documents)}
            }
        )
        # Préserver tous les champs du state, notamment la question
        return {
            "documents": documents,
            "latencies": latencies,
            "question": state.get("question"),  # Préserver la question
            "conversation_id": conversation_id,
            "error_history": state.get("error_history", [])
        }
        
    except RetrievalException:
        raise
    except Exception as e:
        elapsed_time = time.time() - start_time
        latencies["retrieval"] = elapsed_time
        print(f"❌ [RETRIEVE] Exception non capturee: {str(e)}")
        logger.error(
            "Retrieval failed",
            extra={"component": "retrieval", "conversation_id": conversation_id},
            exc_info=True
        )
        import traceback
        traceback.print_exc()
        raise RetrievalException(f"Erreur recuperation: {str(e)}") from e


def generate(state: Dict) -> Dict:
    """Generate an answer using RAG on the retrieved documents."""
    start_time = time.time()
    conversation_id = state.get("conversation_id", "unknown")
    latencies = state.get("latencies", {})
    
    try:
        logger.info("Generation started", extra={"component": "generation", "conversation_id": conversation_id})
        print("---GENERATE---")
        
        if not state.get("documents"):
            raise GenerationException("Aucun document disponible pour la génération")
        
        # Vérifier si les citations sont activées
        citations_enabled = getattr(Config, 'CITATIONS_ENABLED', True)
        
        # Formater les documents (avec ou sans numéros de citation)
        docs_txt = format_docs(state["documents"], with_citations=citations_enabled)
        prompt = get_prompts(question=state["question"])  # Passer la question
        
        rag_prompt_formatted = prompt["rag_prompt"].format(
            context=docs_txt, 
            question=state["question"]
        )
        
        def _generate():
            # Utiliser le gestionnaire de clés avec fallback automatique
            return groq_key_manager.invoke_with_fallback(
                [HumanMessage(content=rag_prompt_formatted)],
                json_mode=False
            )
        
        try:
            generation = retry_with_backoff_advanced(
                _generate,
                circuit_breaker=llm_circuit_breaker
            )
        except MaxRetriesException as e:
            # Essayer avec le modèle de fallback suivant
            if fallback_manager and fallback_manager.try_next_model():
                print(f"[FALLBACK] Tentative avec modèle: {fallback_manager.get_current_model_name()}")
                try:
                    generation = retry_with_backoff_advanced(
                        _generate,
                        circuit_breaker=llm_circuit_breaker
                    )
                except Exception:
                    # Réinitialiser au modèle principal
                    fallback_manager.reset()
                    raise
            else:
                if fallback_manager:
                    fallback_manager.reset()
                raise
        
        if not generation:
            raise InvalidResponseException("Réponse vide du LLM")
        
        # Extraire le contenu de la réponse
        generation_content = generation.content if hasattr(generation, 'content') else str(generation)
        
        # Traiter les citations si activées
        if citations_enabled:
            sources = extract_sources_from_documents(state["documents"])
            generation_content, references = format_citations(generation_content, sources)
            
            # Ajouter les références à la réponse si elles existent
            if references:
                generation_content = generation_content + references
        
        elapsed_time = time.time() - start_time
        latencies["generation"] = elapsed_time
        
        logger.info(
            "Generation completed",
            extra={
                "component": "generation",
                "conversation_id": conversation_id,
                "data": {"latency": elapsed_time, "citations_enabled": citations_enabled}
            }
        )
        
        return {
            "generation": generation_content,
            "loop_step": state.get("loop_step", 0) + 1,
            "latencies": latencies
        }
    except LLMQuotaException as e:
        elapsed_time = time.time() - start_time
        latencies["generation"] = elapsed_time
        raise LLMQuotaException(
            "Quota API dépassé. Veuillez réessayer plus tard.",
            {"loop_step": state.get("loop_step", 0)}
        ) from e
    except Exception as e:
        elapsed_time = time.time() - start_time
        latencies["generation"] = elapsed_time
        error_msg = f"Erreur lors de la génération: {str(e)}"
        print(f"❌ {error_msg}")
        logger.error(
            "Generation failed",
            extra={"component": "generation", "conversation_id": conversation_id},
            exc_info=True,
        )
        # Lever une exception métier claire, déjà importée en haut du fichier
        raise GenerationException(error_msg) from e

def generate_stream(state: Dict, stream_callback=None):
    """
    Génère une réponse avec streaming token par token.
    
    Args:
        state: État du graph
        stream_callback: Fonction callback appelée pour chaque chunk (chunk: str) -> None
    
    Returns:
        Dict avec la génération complète
    """
    start_time = time.time()
    conversation_id = state.get("conversation_id", "unknown")
    latencies = state.get("latencies", {})
    
    try:
        logger.info("Generation with streaming started", extra={"component": "generation", "conversation_id": conversation_id})
        print("---GENERATE (STREAMING)---")
        
        if not state.get("documents"):
            raise GenerationException("Aucun document disponible pour la génération")
        
        # Vérifier si les citations sont activées
        citations_enabled = getattr(Config, 'CITATIONS_ENABLED', True)
        
        # Formater les documents
        docs_txt = format_docs(state["documents"], with_citations=citations_enabled)
        
        # Obtenir les prompts avec la question pour few-shot et role detection
        prompt = get_prompts(question=state["question"])
        
        rag_prompt_formatted = prompt["rag_prompt"].format(
            context=docs_txt, 
            question=state["question"]
        )
        
        # Accumulateur pour la réponse complète
        full_response = ""
        
        # Streamer la réponse avec fallback automatique sur les clés
        try:
            stream = groq_key_manager.stream_with_fallback(
                [HumanMessage(content=rag_prompt_formatted)],
                json_mode=False
            )
            
            for chunk in stream:
                if hasattr(chunk, 'content') and chunk.content:
                    chunk_text = chunk.content
                    full_response += chunk_text
                    
                    # Appeler le callback si fourni
                    if stream_callback:
                        stream_callback(chunk_text)
            
            # Traiter les citations si activées
            if citations_enabled:
                sources = extract_sources_from_documents(state["documents"])
                full_response, references = format_citations(full_response, sources)
                
                # Streamer les références aussi
                if references:
                    if stream_callback:
                        stream_callback(references)
                    full_response = full_response + references
            
        except Exception as stream_error:
            # Fallback sur génération non-streaming en cas d'erreur
            print(f"⚠️ Erreur streaming, fallback sur génération normale: {str(stream_error)}")
            logger.warning(
                "Streaming failed, falling back to non-streaming",
                extra={"component": "generation", "conversation_id": conversation_id, "error": str(stream_error)}
            )
            
            # S'assurer que le prompt est bien formaté avec la question
            prompt = get_prompts(question=state["question"])
            rag_prompt_formatted = prompt["rag_prompt"].format(
                context=docs_txt, 
                question=state["question"]
            )
            
            def _generate():
                # Utiliser le gestionnaire de clés avec fallback automatique
                return groq_key_manager.invoke_with_fallback(
                    [HumanMessage(content=rag_prompt_formatted)],
                    json_mode=False
                )
            
            generation = retry_with_backoff_advanced(
                _generate,
                circuit_breaker=llm_circuit_breaker
            )
            full_response = generation.content if hasattr(generation, 'content') else str(generation)
            
            # Traiter les citations
            if citations_enabled:
                sources = extract_sources_from_documents(state["documents"])
                full_response, references = format_citations(full_response, sources)
                if references:
                    full_response = full_response + references
        
        elapsed_time = time.time() - start_time
        latencies["generation"] = elapsed_time
        
        logger.info(
            "Generation with streaming completed",
            extra={
                "component": "generation",
                "conversation_id": conversation_id,
                "data": {"latency": elapsed_time, "citations_enabled": citations_enabled}
            }
        )
        
        return {
            "generation": full_response,
            "loop_step": state.get("loop_step", 0) + 1,
            "latencies": latencies
        }
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        latencies["generation"] = elapsed_time
        error_msg = f"Erreur lors de la génération avec streaming: {str(e)}"
        print(f"❌ {error_msg}")
        logger.error(
            "Generation with streaming failed",
            extra={"component": "generation", "conversation_id": conversation_id},
            exc_info=True,
        )
        # Lever une exception métier claire, déjà importée en haut du fichier
        raise GenerationException(error_msg) from e


def grade_documents(state: Dict) -> Dict:
    """Grade the relevance of retrieved documents using multi-criteria evaluation."""
    start_time = time.time()
    conversation_id = state.get("conversation_id", "unknown")
    latencies = state.get("latencies", {})
    
    try:
        logger.info("Document grading started", extra={"component": "grading", "conversation_id": conversation_id})
        print("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
        filtered_docs = []
        web_search = "No"
        
        # Vérifier que la question est présente
        question = state.get("question")
        if not question:
            print("⚠️ Question manquante dans le state pour le grading")
            elapsed_time = time.time() - start_time
            latencies["grading"] = elapsed_time
            return {
                "documents": [],
                "web_search": "Yes",
                "latencies": latencies,
                "question": None,  # Question manquante
                "conversation_id": conversation_id,
                "error_history": state.get("error_history", []) + ["Question manquante pour grading"]
            }
        
        if not state.get("documents"):
            elapsed_time = time.time() - start_time
            latencies["grading"] = elapsed_time
            return {
                "documents": [],
                "web_search": "Yes",
                "latencies": latencies,
                "question": question,  # Préserver la question
                "conversation_id": conversation_id,
                "error_history": state.get("error_history", [])
            }
        
        # Obtenir les prompts avec la question
        prompt = get_prompts(question=question)
        
        # Vérifier si multi-criteria grading est activé
        multi_criteria_enabled = getattr(Config, 'MULTI_CRITERIA_GRADING_ENABLED', True)
        
        all_scores = []  # Pour seuil adaptatif
        
        for doc in state["documents"]:
            try:
                multi_criteria_failed = False                
                if multi_criteria_enabled:
                    # Grading multi-critères
                    grader_prompt_formatted = prompt["multi_criteria_grader_prompt"].format(
                        document=doc.page_content[:4000],  # Limiter la longueur pour éviter token limit
                        question=question
                    )
                    
                    def _grade():
                        # Utiliser le gestionnaire de clés avec fallback automatique (mode JSON)
                        return groq_key_manager.invoke_with_fallback(
                            [SystemMessage(content=prompt["multi_criteria_grader_instructions"])] +
                            [HumanMessage(content=grader_prompt_formatted)],
                            json_mode=True
                        )
                    
                    result = retry_with_backoff_advanced(
                        _grade,
                        circuit_breaker=llm_circuit_breaker
                    )
                    
                    try:
                        grade_data = json.loads(result.content)
                        
                        # Extraire les scores
                        scores = grade_data.get("scores", {})
                        relevance = float(scores.get("relevance", 0.0))
                        coverage = float(scores.get("coverage", 0.0))
                        freshness = float(scores.get("freshness", 0.7))  # Default si inconnu
                        authority = float(scores.get("authority", 0.7))  # Default si inconnu
                        clarity = float(scores.get("clarity", 0.7))
                        
                        # Calculer le score pondéré
                        weights = {
                            "relevance": getattr(Config, 'GRADING_RELEVANCE_WEIGHT', 0.35),
                            "coverage": getattr(Config, 'GRADING_COVERAGE_WEIGHT', 0.25),
                            "freshness": getattr(Config, 'GRADING_FRESHNESS_WEIGHT', 0.15),
                            "authority": getattr(Config, 'GRADING_AUTHORITY_WEIGHT', 0.15),
                            "clarity": getattr(Config, 'GRADING_CLARITY_WEIGHT', 0.10)
                        }
                        
                        overall_score = (
                            relevance * weights["relevance"] +
                            coverage * weights["coverage"] +
                            freshness * weights["freshness"] +
                            authority * weights["authority"] +
                            clarity * weights["clarity"]
                        )
                        
                        # Utiliser le score du LLM si fourni, sinon utiliser notre calcul
                        overall_score = float(grade_data.get("overall_score", overall_score))
                        all_scores.append(overall_score)
                        
                        # Déterminer le seuil
                        acceptance_threshold = getattr(Config, 'GRADING_ACCEPTANCE_THRESHOLD', 0.6)
                        adaptive_threshold = getattr(Config, 'GRADING_ADAPTIVE_THRESHOLD', True)
                        
                        if adaptive_threshold and len(all_scores) > 1:
                            # Seuil adaptatif : moyenne des scores * 0.8 (plus permissif)
                            threshold = (sum(all_scores) / len(all_scores)) * 0.8
                            threshold = max(threshold, acceptance_threshold * 0.7)  # Minimum 70% du seuil fixe
                        else:
                            threshold = acceptance_threshold
                        
                        accepted = grade_data.get("accepted", overall_score >= threshold)
                        reasoning = grade_data.get("reasoning", "")
                        
                        print(f"---GRADE: Score={overall_score:.2f} (R:{relevance:.2f}, C:{coverage:.2f}, F:{freshness:.2f}, A:{authority:.2f}, Cl:{clarity:.2f}) | Threshold={threshold:.2f}---")
                        if reasoning:
                            print(f"  Reasoning: {reasoning[:150]}...")
                        
                        if accepted and overall_score >= threshold:
                            print(f"✅ DOCUMENT ACCEPTED (score: {overall_score:.2f})")
                            filtered_docs.append(doc)
                        else:
                            print(f"❌ DOCUMENT REJECTED (score: {overall_score:.2f} < threshold: {threshold:.2f})")
                            web_search = "Yes"
                            
                    except (json.JSONDecodeError, ValueError, KeyError) as e:
                        print(f"⚠️ Erreur parsing JSON multi-criteria: {str(e)}. Fallback sur grading binaire pour ce document.")
                        multi_criteria_failed = True
                    
                if not multi_criteria_enabled or multi_criteria_failed:
                    # Grading binaire (fallback ou désactivé)
                    doc_grader_prompt_formatted = prompt["doc_grader_prompt"].format(
                        document=doc.page_content[:4000],
                        question=question
                    )
                    
                    def _grade():
                        # Utiliser le gestionnaire de clés avec fallback automatique (mode JSON)
                        return groq_key_manager.invoke_with_fallback(
                            [SystemMessage(content=prompt["doc_grader_instructions"])] +
                            [HumanMessage(content=doc_grader_prompt_formatted)],
                            json_mode=True
                        )
                    
                    result = retry_with_backoff_advanced(
                        _grade,
                        circuit_breaker=llm_circuit_breaker
                    )
                    
                    try:
                        grade_data = json.loads(result.content)
                        grade = grade_data.get("binary_score", "no")
                    except json.JSONDecodeError as e:
                        print(f"⚠️ Erreur parsing JSON: {str(e)}. Score par défaut: no")
                        grade = "no"
                    
                    if grade.lower() == "yes":
                        print("---GRADE: DOCUMENT RELEVANT---")
                        filtered_docs.append(doc)
                    else:
                        print("---GRADE: DOCUMENT NOT RELEVANT---")
                        web_search = "Yes"
                        
            except Exception as e:
                print(f"⚠️ Erreur lors du grading d'un document: {str(e)}. Document ignoré.")
                web_search = "Yes"
                continue
        
        elapsed_time = time.time() - start_time
        latencies["grading"] = elapsed_time
        
        logger.info(
            "Document grading completed",
            extra={
                "component": "grading",
                "conversation_id": conversation_id,
                "data": {
                    "latency": elapsed_time,
                    "num_filtered": len(filtered_docs),
                    "num_total": len(state.get("documents", [])),
                    "multi_criteria": multi_criteria_enabled,
                    "avg_score": sum(all_scores) / len(all_scores) if all_scores else 0.0
                }
            }
        )
        
        # Préserver tous les champs du state, notamment la question
        return {
            "documents": filtered_docs,
            "web_search": web_search,
            "latencies": latencies,
            "question": question,  # Préserver la question
            "conversation_id": conversation_id,
            "error_history": state.get("error_history", [])
        }
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        latencies["grading"] = elapsed_time
        print(f"❌ Erreur dans grade_documents: {str(e)}")
        logger.error(
            "Document grading failed",
            extra={"component": "grading", "conversation_id": conversation_id},
            exc_info=True
        )
        # En cas d'erreur, on continue avec tous les documents mais on préserve la question
        return {
            "documents": state.get("documents", []),
            "web_search": "Yes",
            "latencies": latencies,
            "question": state.get("question"),  # Préserver la question
            "conversation_id": conversation_id,
            "error_history": state.get("error_history", []) + [f"Erreur grading: {str(e)}"]
        }

def web_search(state: Dict) -> Dict:
    """Perform a web search based on the question."""
    start_time = time.time()
    conversation_id = state.get("conversation_id", "unknown")
    latencies = state.get("latencies", {})
    
    try:
        logger.info("Web search started", extra={"component": "web_search", "conversation_id": conversation_id})
        print("---WEB SEARCH---")
        
        if not state.get("question"):
            raise WebSearchException("Question manquante pour la recherche web")
        
        def _search():
            return web_search_tool.invoke({"query": state["question"]})
        
        docs = retry_with_backoff_advanced(
            _search,
            max_retries=2,
            circuit_breaker=web_search_circuit_breaker
        )
        
        if not docs:
            print("⚠️ Aucun résultat de recherche web")
            elapsed_time = time.time() - start_time
            latencies["web_search"] = elapsed_time
            return {
                "documents": state.get("documents", []),
                "latencies": latencies,
                "question": state.get("question"),  # Préserver la question
                "conversation_id": conversation_id
            }
        
        web_results = "\n".join([d.get("content", "") for d in docs if d.get("content")])
        
        if not web_results:
            print("⚠️ Résultats web vides")
            elapsed_time = time.time() - start_time
            latencies["web_search"] = elapsed_time
            return {
                "documents": state.get("documents", []),
                "latencies": latencies,
                "question": state.get("question"),  # Préserver la question
                "conversation_id": conversation_id
            }
        
        documents = state.get("documents", [])
        documents.append(Document(page_content=web_results))
        
        elapsed_time = time.time() - start_time
        latencies["web_search"] = elapsed_time
        
        logger.info(
            "Web search completed",
            extra={
                "component": "web_search",
                "conversation_id": conversation_id,
                "data": {"latency": elapsed_time}
            }
        )
        
        # Préserver tous les champs du state, notamment la question
        return {
            "documents": documents,
            "latencies": latencies,
            "question": state.get("question"),  # Préserver la question
            "conversation_id": conversation_id,
            "error_history": state.get("error_history", [])
        }
    except Exception as e:
        elapsed_time = time.time() - start_time
        latencies["web_search"] = elapsed_time
        error_msg = f"Erreur lors de la recherche web: {str(e)}"
        print(f"❌ {error_msg}")
        logger.error(
            "Web search failed",
            extra={"component": "web_search", "conversation_id": conversation_id},
            exc_info=True
        )
        # Ne pas bloquer, continuer avec les documents existants mais préserver la question
        return {
            "documents": state.get("documents", []),
            "latencies": latencies,
            "question": state.get("question"),  # Préserver la question
            "conversation_id": conversation_id,
            "error_history": state.get("error_history", []) + [f"Erreur web_search: {str(e)}"]
        }


# Edge functions
def route_question(state: Dict) -> str:
    """Route the question to either web search or RAG based on LLM decision."""
    try:
        print("---ROUTE QUESTION---")
        
        def _route():
            # Utiliser le gestionnaire de clés avec fallback automatique (mode JSON)
            return groq_key_manager.invoke_with_fallback(
                [SystemMessage(content=prompt["router_instructions"])] +
                [HumanMessage(content=state["question"])],
                json_mode=True
            )
        
        route_result = retry_with_backoff_advanced(
            _route,
            circuit_breaker=llm_circuit_breaker
        )
        
        try:
            route_data = json.loads(route_result.content)
            source = route_data.get("datasource", "vectorstore")
        except json.JSONDecodeError:
            print("⚠️ Erreur parsing JSON routing. Défaut: vectorstore")
            source = "vectorstore"
        
        return "websearch" if source == "websearch" else "vectorstore"
    except Exception as e:
        print(f"⚠️ Erreur lors du routing: {str(e)}. Défaut: vectorstore")
        return "vectorstore"  # Fallback sur vectorstore


def decide_to_generate(state: Dict) -> str:
    """Decide whether to generate an answer or add web search."""
    print("---ASSESS GRADED DOCUMENTS---")
    if state.get("web_search") == "Yes":
        print("---DECISION: INCLUDE WEB SEARCH---")
        return "websearch"
    else:
        print("---DECISION: GENERATE---")
        return "generate"


def grade_generation_v_documents_and_question(state: Dict) -> str:
    """Grade whether the generation is grounded in the document and answers the question."""
    try:
        print("---CHECK HALLUCINATIONS---")
        
        max_retries = state.get("max_retries", getattr(Config, 'MAX_RETRIES', 3))
        loop_step = state.get("loop_step", 0)
        
        if not state.get("generation"):
            raise ValidationException("Génération manquante pour la validation")
        
        generation_content = state["generation"].content if hasattr(state["generation"], "content") else str(state["generation"])
        
        # Vérification des hallucinations
        try:
            hallucination_grader_prompt_formatted = prompt["hallucination_grader_prompt"].format(
                documents=format_docs(state.get("documents", []), with_citations=False),
                generation=generation_content
            )
            
            def _check_hallucination():
                # Utiliser le gestionnaire de clés avec fallback automatique (mode JSON)
                return groq_key_manager.invoke_with_fallback(
                    [SystemMessage(content=prompt["hallucination_grader_instructions"])] +
                    [HumanMessage(content=hallucination_grader_prompt_formatted)],
                    json_mode=True
                )
            
            result = retry_with_backoff_advanced(
                _check_hallucination,
                circuit_breaker=llm_circuit_breaker
            )
            
            try:
                grade_data = json.loads(result.content)
                grade = grade_data.get("binary_score", "no")
            except json.JSONDecodeError:
                print("⚠️ Erreur parsing JSON hallucination. Par défaut: no")
                grade = "no"
            
            if grade != "yes":
                if loop_step < max_retries:
                    print(f"---DECISION: GENERATION NOT GROUNDED, RETRYING ({loop_step + 1}/{max_retries})---")
                    # Appliquer stratégie de recovery pour hallucinations
                    if getattr(Config, 'RECOVERY_STRATEGY_ENABLED', True):
                        try:
                            current_llm = get_llm_with_fallback()
                            state = RecoveryStrategy.handle_hallucination(state, current_llm)
                        except Exception as e:
                            print(f"⚠️ Erreur lors de l'application de la stratégie de recovery: {str(e)}")
                    
                   
                    return "not supported"
                else:
                    print("---DECISION: MAX RETRIES REACHED---")
                    raise MaxRetriesException(
                        f"Maximum de {max_retries} tentatives atteint",
                        {"loop_step": loop_step, "max_retries": max_retries}
                    )
        except MaxRetriesException:
            raise
        except Exception as e:
            print(f"⚠️ Erreur vérification hallucination: {str(e)}. On continue...")
            # En cas d'erreur, on considère comme OK pour éviter boucle infinie
        
        # Vérification de l'utilité
        print("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
        try:
            answer_grader_prompt_formatted = prompt["answer_grader_prompt"].format(
                question=state["question"],
                generation=generation_content
            )
            
            def _check_useful():
                # Utiliser le gestionnaire de clés avec fallback automatique (mode JSON)
                return groq_key_manager.invoke_with_fallback(
                    [SystemMessage(content=prompt["answer_grader_instructions"])] +
                    [HumanMessage(content=answer_grader_prompt_formatted)],
                    json_mode=True
                )
            
            result = retry_with_backoff_advanced(
                _check_useful,
                circuit_breaker=llm_circuit_breaker
            )
            
            try:
                grade_data = json.loads(result.content)
                grade = grade_data.get("binary_score", "no")
            except json.JSONDecodeError:
                print("⚠️ Erreur parsing JSON answer. Par défaut: no")
                grade = "no"
            
            if grade == "yes":
                return "useful"
            else:
                # Appliquer stratégie de recovery pour "not useful"
                if getattr(Config, 'RECOVERY_STRATEGY_ENABLED', True):
                    try:
                        state = RecoveryStrategy.handle_not_useful(state)
                    except Exception as e:
                        print(f"⚠️ Erreur lors de l'application de la stratégie de recovery: {str(e)}")
                
                return "not useful"
        except Exception as e:
            print(f"⚠️ Erreur vérification utilité: {str(e)}. Par défaut: not useful")
            return "not useful"
    except MaxRetriesException:
        return "max retries"
    except Exception as e:
        print(f"❌ Erreur dans grade_generation: {str(e)}")
        return "max retries"  # Sécurité: arrêt en cas d'erreur


def grade_answer_quality(state: Dict) -> Dict:
    """Évalue la qualité de la réponse générée sur 5 critères."""
    start_time = time.time()
    conversation_id = state.get("conversation_id", "unknown")
    latencies = state.get("latencies", {})
    
    try:
        logger.info("Answer quality scoring started", extra={"component": "answer_quality", "conversation_id": conversation_id})
        print("---ANSWER QUALITY SCORING---")
        
        # Vérifier si activé
        quality_scoring_enabled = getattr(Config, 'ANSWER_QUALITY_SCORING_ENABLED', True)
        if not quality_scoring_enabled:
            elapsed_time = time.time() - start_time
            latencies["answer_quality"] = elapsed_time
            return {"answer_quality_scores": None, "latencies": latencies}
        
        if not state.get("generation"):
            elapsed_time = time.time() - start_time
            latencies["answer_quality"] = elapsed_time
            return {"answer_quality_scores": None, "latencies": latencies}
        
        # Extraire le contenu de la réponse
        generation_content = state["generation"].content if hasattr(state["generation"], "content") else str(state["generation"])
        
        # Formater les documents pour le contexte
        context = format_docs(state.get("documents", []), with_citations=False)
        
        # Préparer le prompt
        quality_prompt_formatted = prompt["answer_quality_scorer_prompt"].format(
            question=state["question"],
            answer=generation_content[:4000],  # Limiter la longueur
            context=context[:3000]  # Limiter le contexte
        )
        
        def _score_quality():
            # Utiliser le gestionnaire de clés avec fallback automatique (mode JSON)
            return groq_key_manager.invoke_with_fallback(
                [SystemMessage(content=prompt["answer_quality_scorer_instructions"])] +
                [HumanMessage(content=quality_prompt_formatted)],
                json_mode=True
            )
        
        result = retry_with_backoff_advanced(
            _score_quality,
            circuit_breaker=llm_circuit_breaker
        )
        
        try:
            quality_data = json.loads(result.content)
            
            # Extraire les scores
            scores = quality_data.get("scores", {})
            relevance = float(scores.get("relevance", 0.0))
            completeness = float(scores.get("completeness", 0.0))
            conciseness = float(scores.get("conciseness", 0.0))
            accuracy = float(scores.get("accuracy", 0.0))
            coherence = float(scores.get("coherence", 0.0))
            
            # Calculer le score pondéré
            relevance_weight = getattr(Config, 'ANSWER_QUALITY_RELEVANCE_WEIGHT', 0.30)
            completeness_weight = getattr(Config, 'ANSWER_QUALITY_COMPLETENESS_WEIGHT', 0.25)
            conciseness_weight = getattr(Config, 'ANSWER_QUALITY_CONCISENESS_WEIGHT', 0.15)
            accuracy_weight = getattr(Config, 'ANSWER_QUALITY_ACCURACY_WEIGHT', 0.20)
            coherence_weight = getattr(Config, 'ANSWER_QUALITY_COHERENCE_WEIGHT', 0.10)
            
            overall_score = (
                relevance * relevance_weight +
                completeness * completeness_weight +
                conciseness * conciseness_weight +
                accuracy * accuracy_weight +
                coherence * coherence_weight
            )
            
            # Vérifier le seuil d'acceptation
            threshold = getattr(Config, 'ANSWER_QUALITY_ACCEPTANCE_THRESHOLD', 0.65)
            accepted = overall_score >= threshold
            
            quality_scores = {
                "relevance": relevance,
                "completeness": completeness,
                "conciseness": conciseness,
                "accuracy": accuracy,
                "coherence": coherence,
                "overall_score": overall_score,
                "accepted": accepted,
                "reasoning": quality_data.get("reasoning", "No reasoning provided")
            }
            
            print(f"📊 Answer Quality Scores:")
            print(f"   Relevance: {relevance:.2f}")
            print(f"   Completeness: {completeness:.2f}")
            print(f"   Conciseness: {conciseness:.2f}")
            print(f"   Accuracy: {accuracy:.2f}")
            print(f"   Coherence: {coherence:.2f}")
            print(f"   Overall Score: {overall_score:.2f} ({'✅ Accepted' if accepted else '❌ Below threshold'})")
            
            elapsed_time = time.time() - start_time
            latencies["answer_quality"] = elapsed_time
            
            logger.info(
                "Answer quality scoring completed",
                extra={
                    "component": "answer_quality",
                    "conversation_id": conversation_id,
                    "data": {
                        "latency": elapsed_time,
                        "overall_score": overall_score,
                        "accepted": accepted
                    }
                }
            )
            
            return {"answer_quality_scores": quality_scores, "latencies": latencies}
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Erreur parsing JSON answer quality: {str(e)}")
            elapsed_time = time.time() - start_time
            latencies["answer_quality"] = elapsed_time
            return {"answer_quality_scores": None, "latencies": latencies}
            
    except Exception as e:
        elapsed_time = time.time() - start_time
        latencies["answer_quality"] = elapsed_time
        print(f"❌ Erreur dans grade_answer_quality: {str(e)}")
        logger.error(
            "Answer quality scoring failed",
            extra={"component": "answer_quality", "conversation_id": conversation_id},
            exc_info=True
        )
        return {"answer_quality_scores": None, "latencies": latencies}


# Workflow definition and graph compilation
workflow = StateGraph(GraphState)
workflow.add_node("websearch", web_search)
workflow.add_node("retrieve", retrieve)
workflow.add_node("grade_documents", grade_documents)
workflow.add_node("generate", generate)
workflow.add_node("grade_answer_quality", grade_answer_quality)

workflow.set_conditional_entry_point(
    route_question,
    {"websearch": "websearch", "vectorstore": "retrieve"},
)
workflow.add_edge("websearch", "generate")
workflow.add_edge("retrieve", "grade_documents")
workflow.add_conditional_edges(
    "grade_documents",
    decide_to_generate,
    {"websearch": "websearch", "generate": "generate"},
)
workflow.add_edge("generate", "grade_answer_quality")
workflow.add_conditional_edges(
    "grade_answer_quality",
    grade_generation_v_documents_and_question,
    {"not supported": "generate", "useful": END, "not useful": "websearch", "max retries": END},
)

# Compile the graph
graph = workflow.compile()

# Final response function
def get_final_response(query: str) -> str:
    """Point d'entrée principal pour obtenir une réponse RAG."""
    conversation_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    
    # Début de la mesure end-to-end
    start_time = time.time()
    latencies = {}
    
    try:
        logger.info(
            "Request started",
            extra={
                "component": "rag",
                "conversation_id": conversation_id,
                "trace_id": trace_id,
                "data": {"query": query[:100]}
            }
        )
        
        if not query or not query.strip():
            return "⚠️ Veuillez fournir une question valide."
        
        # Réécriture de la requête (avec fallback sur query originale)
        try:
            rewritten_query = Rewrite_query(query, history=None)
        except Exception as e:
            print(f"⚠️ Erreur réécriture, utilisation query originale: {str(e)}")
            rewritten_query = query
        
        # Initialisation de l'état avec max_retries, conversation_id et latencies
        max_retries = getattr(Config, 'MAX_RETRIES', 3)
        initial_state = GraphState(
            question=rewritten_query,
            generation="",
            web_search="No",
            max_retries=max_retries,
            answers=0,
            loop_step=0,
            documents=[],
            error_history=[],
            conversation_id=conversation_id,
            latencies=latencies
        )
        
        # Exécution du workflow
        final_state = graph.invoke(initial_state)
        
        # Récupérer les latences mises à jour depuis le state
        latencies = final_state.get("latencies", latencies)
        
        # Extraction de la réponse
        generation = final_state.get("generation")
        if generation and hasattr(generation, "content"):
            response = generation.content
        elif generation:
            response = str(generation)
        else:
            response = "⚠️ Aucune réponse générée. Veuillez reformuler votre question."
        
        # Mesurer latence end-to-end
        latencies["end_to_end"] = time.time() - start_time
        
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
        
        logger.info(
            "Request completed",
            extra={
                "component": "rag",
                "conversation_id": conversation_id,
                "trace_id": trace_id,
                "data": {"latency": latencies["end_to_end"]}
            }
        )
        
        return response
        
    except MaxRetriesException as e:
        latencies["end_to_end"] = time.time() - start_time
        error_msg = "⚠️ Désolé, j'ai atteint le nombre maximum de tentatives. Veuillez reformuler votre question ou réessayer plus tard."
        
        if getattr(Config, 'METRICS_ENABLED', True):
            metrics.record_request(
                conversation_id=conversation_id,
                query=query,
                latencies=latencies,
                success=False,
                error="MaxRetriesException"
            )
        
        logger.warning(
            "Request max retries",
            extra={
                "component": "rag",
                "conversation_id": conversation_id,
                "trace_id": trace_id
            }
        )
        
        return error_msg
    
    except LLMQuotaException as e:
        latencies["end_to_end"] = time.time() - start_time
        error_msg = "⚠️ Le service est temporairement saturé. Veuillez réessayer dans quelques instants."
        
        if getattr(Config, 'METRICS_ENABLED', True):
            metrics.record_request(
                conversation_id=conversation_id,
                query=query,
                latencies=latencies,
                success=False,
                error="LLMQuotaException"
            )
        
        logger.error(
            "Request quota exceeded",
            extra={
                "component": "rag",
                "conversation_id": conversation_id,
                "trace_id": trace_id
            }
        )
        
        return error_msg
    
    except RetrievalException as e:
        latencies["end_to_end"] = time.time() - start_time
        error_msg = "⚠️ Impossible de trouver des documents pertinents. Veuillez reformuler votre question."
        
        if getattr(Config, 'METRICS_ENABLED', True):
            metrics.record_request(
                conversation_id=conversation_id,
                query=query,
                latencies=latencies,
                success=False,
                error="RetrievalException"
            )
        
        logger.error(
            "Request retrieval failed",
            extra={
                "component": "rag",
                "conversation_id": conversation_id,
                "trace_id": trace_id
            }
        )
        
        return error_msg
    
    except WebSearchException as e:
        latencies["end_to_end"] = time.time() - start_time
        error_msg = "⚠️ Erreur lors de la recherche web. Veuillez réessayer."
        
        if getattr(Config, 'METRICS_ENABLED', True):
            metrics.record_request(
                conversation_id=conversation_id,
                query=query,
                latencies=latencies,
                success=False,
                error="WebSearchException"
            )
        
        logger.error(
            "Request web search failed",
            extra={
                "component": "rag",
                "conversation_id": conversation_id,
                "trace_id": trace_id
            }
        )
        
        return error_msg
        
    except Exception as e:
        latencies["end_to_end"] = time.time() - start_time
        error_msg = str(e)
        
        # Enregistrer l'erreur
        if getattr(Config, 'METRICS_ENABLED', True):
            metrics.record_request(
                conversation_id=conversation_id,
                query=query,
                latencies=latencies,
                success=False,
                error=error_msg
            )
        
        logger.error(
            "Request failed",
            extra={
                "component": "rag",
                "conversation_id": conversation_id,
                "trace_id": trace_id,
                "data": {"error": error_msg}
            },
            exc_info=True
        )
        
        raise

def get_final_response_stream(query: str):
    """
    Point d'entrée principal pour obtenir une réponse RAG avec streaming.
    Retourne un générateur qui yield les chunks de la réponse.
    
    Args:
        query: Question de l'utilisateur
    
    Yields:
        str: Chunks de la réponse au fur et à mesure de la génération
    """
    conversation_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    
    # Début de la mesure end-to-end
    start_time = time.time()
    latencies = {}
    
    try:
        logger.info(
            "Streaming request started",
            extra={
                "component": "rag",
                "conversation_id": conversation_id,
                "trace_id": trace_id,
                "data": {"query": query[:100]}
            }
        )
        
        if not query or not query.strip():
            yield "⚠️ Veuillez fournir une question valide."
            return
        
        # Réécriture de la requête
        try:
            rewritten_query = Rewrite_query(query, history=None)
        except Exception as e:
            print(f"⚠️ Erreur réécriture, utilisation query originale: {str(e)}")
            rewritten_query = query
        
        # Initialisation de l'état
        max_retries = getattr(Config, 'MAX_RETRIES', 3)
        initial_state = GraphState(
            question=rewritten_query,
            generation="",
            web_search="No",
            max_retries=max_retries,
            answers=0,
            loop_step=0,
            documents=[],
            error_history=[],
            conversation_id=conversation_id,
            latencies=latencies
        )
        
        # Exécuter le workflow jusqu'à la génération
        # On doit exécuter manuellement les étapes jusqu'à generate
        current_state = initial_state
        
        # Route question
        route = route_question(current_state)
        if route == "websearch":
            current_state = web_search(current_state)
        else:
            current_state = retrieve(current_state)
            current_state = grade_documents(current_state)
            
            # Décider si on fait web search
            if current_state.get("web_search") == "Yes":
                current_state = web_search(current_state)
        
        # Maintenant on génère avec streaming
        # Utiliser generate_stream avec callback
        # Note: On doit adapter car generate_stream attend un callback, pas un générateur
        # Solution: créer un wrapper qui yield les chunks
        
        chunks_received = []
        
        def stream_callback_wrapper(chunk: str):
            """Wrapper pour collecter les chunks."""
            chunks_received.append(chunk)
        
        # Générer avec streaming
        generation_state = generate_stream(current_state, stream_callback=stream_callback_wrapper)
        
        # Yielder tous les chunks
        for chunk in chunks_received:
            yield chunk
        
        # Mettre à jour l'état final
        final_state = generation_state
        
        # Continuer avec le grading (sans streaming)
        # Note: Le grading et quality scoring ne stream pas
        try:
            grade_result = grade_generation_v_documents_and_question(final_state)
            if grade_result == "useful":
                # Succès
                pass
            elif grade_result == "not supported" and final_state.get("loop_step", 0) < max_retries:
                # Retry (ne devrait pas arriver souvent avec streaming)
                print("⚠️ Retry nécessaire après streaming")
        except Exception as e:
            print(f"⚠️ Erreur lors du grading: {str(e)}")
        
        # Exécuter le quality scoring aussi
        try:
            final_state = grade_answer_quality(final_state)
        except Exception as e:
            print(f"⚠️ Erreur lors du quality scoring: {str(e)}")
        
        # Récupérer les latences
        latencies = final_state.get("latencies", latencies)
        latencies["end_to_end"] = time.time() - start_time
        
        # Récupérer la réponse complète depuis l'état final
        generation = final_state.get("generation", "")
        full_response = generation if isinstance(generation, str) else (generation.content if hasattr(generation, 'content') else str(generation))
        
        # Enregistrer les métriques
        if getattr(Config, 'METRICS_ENABLED', True):
            answer_quality_scores = final_state.get("answer_quality_scores")
            metrics.record_request(
                conversation_id=conversation_id,
                query=query,
                latencies=latencies,
                success=True,
                num_documents=len(final_state.get("documents", [])),
                response_length=len(full_response) if full_response else 0,
                answer_quality_score=answer_quality_scores.get("overall_score") if answer_quality_scores else None,
                answer_quality_scores=answer_quality_scores
            )
        
        logger.info(
            "Streaming request completed",
            extra={
                "component": "rag",
                "conversation_id": conversation_id,
                "trace_id": trace_id,
                "data": {"latency": latencies["end_to_end"]}
            }
        )
        
    except Exception as e:
        latencies["end_to_end"] = time.time() - start_time
        error_msg = f"⚠️ Erreur lors de la génération: {str(e)}"
        yield error_msg
        
        if getattr(Config, 'METRICS_ENABLED', True):
            metrics.record_request(
                conversation_id=conversation_id,
                query=query,
                latencies=latencies,
                success=False,
                error=str(e)
            )
        
        logger.error(
            "Streaming request failed",
            extra={
                "component": "rag",
                "conversation_id": conversation_id,
                "trace_id": trace_id,
                "data": {"error": str(e)}
            },
            exc_info=True
        )