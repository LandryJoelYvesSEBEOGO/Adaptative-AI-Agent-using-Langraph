"""
Stratégies de recovery adaptatives selon le type d'échec.
"""
from typing import Dict, Optional, List
from langchain_core.documents import Document
from langchain_groq import ChatGroq

from config.Config import Config


class RecoveryStrategy:
    """Stratégies de recovery pour différents types d'échecs."""
    
    @staticmethod
    def handle_hallucination(state: Dict, llm: ChatGroq) -> Dict:
        """
        Stratégie pour gérer les hallucinations.
        Augmente la température et change le prompt.
        """
        if not getattr(Config, 'RECOVERY_INCREASE_TEMPERATURE', True):
            return state
        
        print("[RECOVERY] Stratégie: Augmentation température pour réduire hallucinations")
        
        # Augmenter la température
        temperature_increase = getattr(Config, 'RECOVERY_TEMPERATURE_INCREASE', 0.2)
        current_temp = getattr(llm, 'temperature', 0)
        new_temp = min(current_temp + temperature_increase, 1.0)
        
        # Note: On ne peut pas modifier la température d'un LLM existant
        # Il faudrait créer un nouveau LLM avec la température augmentée
        # Pour l'instant, on log juste l'intention
        
        print(f"[RECOVERY] Température suggérée: {new_temp:.2f} (actuelle: {current_temp:.2f})")
        
        return state
    
    @staticmethod
    def handle_not_useful(state: Dict) -> Dict:
        """
        Stratégie pour gérer les réponses "not useful".
        Élargit la recherche et essaie la recherche web.
        """
        if not getattr(Config, 'RECOVERY_EXPAND_SEARCH', True):
            return state
        
        print("[RECOVERY] Stratégie: Élargissement de la recherche")
        
        # Élargir la recherche
        expansion_factor = getattr(Config, 'RECOVERY_SEARCH_EXPANSION_FACTOR', 1.5)
        
        # Récupérer plus de documents
        try:
            from src.rag.Data_processing import get_retriever

            retriever = get_retriever()
            current_k = len(state.get("documents", []))
            new_k = int(current_k * expansion_factor)
            
            print(f"[RECOVERY] Recherche élargie: {current_k} -> {new_k} documents")
            
            # Note: Pour vraiment élargir, il faudrait refaire la recherche
            # Pour l'instant, on suggère d'utiliser web_search
            
            if state.get("web_search") != "Yes":
                print("[RECOVERY] Activation de la recherche web")
                state["web_search"] = "Yes"
        
        except Exception as e:
            print(f"[RECOVERY] Erreur lors de l'élargissement: {str(e)}")
        
        return state
    
    @staticmethod
    def handle_timeout(state: Dict) -> Dict:
        """
        Stratégie pour gérer les timeouts.
        Réduit max_tokens et suggère un modèle plus rapide.
        """
        print("[RECOVERY] Stratégie: Gestion du timeout")
        print("[RECOVERY] Suggestions: Réduire max_tokens, utiliser modèle plus rapide")
        
        # Note: L'implémentation complète nécessiterait de modifier les paramètres du LLM
        # Pour l'instant, on log juste les suggestions
        
        return state