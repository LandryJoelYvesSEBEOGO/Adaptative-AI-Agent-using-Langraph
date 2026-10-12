import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
import uuid
import time
import re

# Ajouter le chemin du projet
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.rag.Rag_model import (
    get_final_response, 
    get_final_response_stream, 
    extract_sources_from_documents, 
    graph, 
    GraphState,
    Rewrite_query
)
from config.Config import Config
from api.services.conversation_service import list_messages

def _normalize_text(text: Optional[str]) -> str:
    return (text or "").strip()

def _build_conversation_history(conversation_id: Optional[str], current_question: str) -> str:
    if not conversation_id:
        return ""
    
    try:
        messages = list_messages(conversation_id)
    except Exception:
        return ""
    
    if not messages:
        return ""
    
    current_question_norm = _normalize_text(current_question)
    if messages and messages[-1].get("role") == "user":
        last_content = _normalize_text(messages[-1].get("content"))
        if last_content == current_question_norm:
            messages = messages[:-1]
    
    max_turns = getattr(Config, "CONVERSATION_CONTEXT_TURNS", 6)
    max_chars = getattr(Config, "CONVERSATION_CONTEXT_MAX_CHARS", 2000)
    max_messages = max_turns * 2
    recent_messages = messages[-max_messages:]
    
    parts = []
    for msg in recent_messages:
        content = _normalize_text(msg.get("content"))
        if not content:
            continue
        role = msg.get("role") or "user"
        label = "User" if role == "user" else "Assistant" if role == "assistant" else str(role)
        parts.append(f"{label}: {content}")
    
    history_text = "\n".join(parts)
    if max_chars and len(history_text) > max_chars:
        history_text = history_text[-max_chars:]
    
    return history_text

def extract_citations(response_text: str, documents: Optional[List] = None) -> List[Dict]:
    """
    Extrait les citations de la réponse RAG et les mappe aux vraies sources.
    Format attendu: [1], [2], etc. dans le texte.
    
    Args:
        response_text: Texte de la réponse avec citations [1], [2], etc.
        documents: Liste des documents LangChain utilisés pour la génération (optionnel)
    
    Returns:
        Liste de dictionnaires avec les citations et leurs sources réelles
    """
    citations = []
    pattern = r'\[(\d+)\]'
    matches = re.findall(pattern, response_text)
    
    # Extraire les citations uniques
    unique_ids = sorted(set(int(match) for match in matches))
    
    # Si on a les documents, extraire les vraies sources
    sources = []
    if documents:
        sources = extract_sources_from_documents(documents)
    
    for citation_id in unique_ids:
        # Extraire un extrait du texte autour de la citation si possible
        excerpt = ""
        citation_pattern = rf'\[{citation_id}\]'
        citation_positions = [m.start() for m in re.finditer(citation_pattern, response_text)]
        
        if citation_positions:
            # Prendre le premier contexte où la citation apparaît
            pos = citation_positions[0]
            start = max(0, pos - 50)
            end = min(len(response_text), pos + 50)
            excerpt = response_text[start:end].strip()
            if len(excerpt) > 100:
                excerpt = excerpt[:97] + "..."
        
        # Mapper à la vraie source si disponible
        source_name = f"Document {citation_id}"
        source_path = ""
        page_number = None
        if sources and 1 <= citation_id <= len(sources):
            source_info = sources[citation_id - 1]  # -1 car les indices commencent à 0
            source_name = source_info.get('title') or source_info.get('source', f'Document {citation_id}')
            source_path = source_info.get('source', '')
            page_number = source_info.get('page')
            # Nettoyer le nom de la source (enlever le chemin complet si c'est un fichier)
            if source_path and '/' in source_path:
                source_name = source_path.split('/')[-1] if not source_info.get('title') else source_info.get('title')
        
        if page_number is not None:
            source_display = f"{source_name} (page {page_number})"
        else:
            source_display = source_name
        
        citations.append({
            "id": citation_id,
            "source": source_display if source_display != "Unknown source" else f"Document {citation_id}",
            "excerpt": excerpt or f"Référence au document {citation_id}",
            "metadata": {
                "source_path": source_path,
                "parent_doc_id": sources[citation_id - 1].get('parent_doc_id', '') if sources and 1 <= citation_id <= len(sources) else '',
                "page": page_number
            }
        })
    
    return citations

def process_rag_query(question: str, conversation_id: Optional[str] = None) -> Dict:
    """
    Traite une question RAG et retourne la réponse avec les vraies sources.
    """
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
    
    start_time = time.time()
    
    try:
        # Exécuter le workflow pour obtenir la réponse ET les documents
        # Réécriture de la requête
        try:
            conversation_history = _build_conversation_history(conversation_id, question)
            rewritten_query = Rewrite_query(question, history=conversation_history)
        except Exception as e:
            rewritten_query = question
        
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
            latencies={}
        )
        
        # Exécution du workflow
        final_state = graph.invoke(initial_state)
        
        # Extraction de la réponse
        generation = final_state.get("generation")
        if generation and hasattr(generation, "content"):
            response_text = generation.content
        elif generation:
            response_text = str(generation)
        else:
            response_text = "⚠️ Aucune réponse générée. Veuillez reformuler votre question."
        
        # Récupérer les documents utilisés
        documents = final_state.get("documents", [])
        
        # Extraire les citations avec les vraies sources
        citations = extract_citations(response_text, documents)
        
        latency = time.time() - start_time
        latencies = final_state.get("latencies", {}) or {}
        if "end_to_end" not in latencies:
            latencies["end_to_end"] = latency

        answer_quality_scores = final_state.get("answer_quality_scores")
        answer_quality_score = None
        if isinstance(answer_quality_scores, dict):
            answer_quality_score = answer_quality_scores.get("overall_score")
        
        return {
            "response": response_text,
            "citations": citations,
            "conversation_id": conversation_id,
            "latency": latency,
            "latencies": latencies,
            "num_documents": len(documents),
            "answer_quality_score": answer_quality_score,
            "answer_quality_scores": answer_quality_scores,
            "success": True,
            "error": None
        }
    
    except Exception as e:
        latency = time.time() - start_time
        latencies = {"end_to_end": latency}
        return {
            "response": "",
            "citations": [],
            "conversation_id": conversation_id or str(uuid.uuid4()),
            "latency": latency,
            "latencies": latencies,
            "num_documents": 0,
            "answer_quality_score": None,
            "answer_quality_scores": None,
            "success": False,
            "error": str(e)
        }

def process_rag_query_stream(
    question: str,
    conversation_id: Optional[str] = None,
    on_complete: Optional[Callable[[Dict], None]] = None
):
    """
    Traite une question RAG en mode streaming.
    Retourne un générateur qui yield les chunks, puis les citations à la fin.
    """
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        # Exécuter le workflow manuellement pour obtenir les documents
        # Réécriture de la requête
        try:
            conversation_history = _build_conversation_history(conversation_id, question)
            rewritten_query = Rewrite_query(question, history=conversation_history)
        except Exception as e:
            rewritten_query = question
        
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
            latencies={}
        )
        
        # Exécuter les étapes jusqu'à la génération
        from src.rag.Rag_model import route_question, retrieve, grade_documents, web_search, generate_stream
        
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
        
        # Collecter les documents avant le streaming
        documents = current_state.get("documents", [])
        
        # Générer avec streaming
        chunks_received = []
        full_response = ""
        
        def stream_callback_wrapper(chunk: str):
            """Wrapper pour collecter les chunks."""
            chunks_received.append(chunk)
            nonlocal full_response
            full_response += chunk
        
        # Générer avec streaming
        generation_state = generate_stream(current_state, stream_callback=stream_callback_wrapper)
        
        # Yielder tous les chunks
        for chunk in chunks_received:
            yield chunk
        
        # Mettre à jour l'état final
        final_state = generation_state

        # Extraire les citations avec les vraies sources
        citations = extract_citations(full_response, documents)

        latencies = final_state.get("latencies", current_state.get("latencies", {})) or {}
        latencies["end_to_end"] = time.time() - start_time

        answer_quality_scores = final_state.get("answer_quality_scores")
        answer_quality_score = None
        if isinstance(answer_quality_scores, dict):
            answer_quality_score = answer_quality_scores.get("overall_score")

        if on_complete:
            on_complete({
                "latencies": latencies,
                "num_documents": len(documents),
                "response_length": len(full_response),
                "answer_quality_score": answer_quality_score,
                "answer_quality_scores": answer_quality_scores,
                "citations": citations,
                "success": True,
                "error": None,
            })
        
        # Les citations sont maintenant gérées séparément via l'API, pas dans le texte de réponse
        # Suppression de l'affichage __CITATIONS__ dans le texte pour éviter l'affichage brut sur le frontend
    
    except Exception as e:
        if on_complete:
            on_complete({
                "latencies": {"end_to_end": time.time() - start_time},
                "num_documents": 0,
                "response_length": 0,
                "answer_quality_score": None,
                "answer_quality_scores": None,
                "citations": [],
                "success": False,
                "error": str(e),
            })
        yield f"⚠️ Erreur lors de la génération: {str(e)}"