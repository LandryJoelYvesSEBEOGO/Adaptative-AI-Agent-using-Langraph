"""
Module pour gérer les exemples few-shot et leur sélection dynamique.
"""
import os
import json
from typing import List, Dict, Optional
from config.Config import Config
from langchain_nomic.embeddings import NomicEmbeddings

# Instance singleton pour les embeddings
_embeddings = None

def get_embeddings():
    """Retourne une instance singleton des embeddings."""
    global _embeddings
    if _embeddings is None:
        # Configuration du device (GPU/CPU)
        device = "cpu"
        try:
            import torch
            if Config.DEVICE_PREFERENCE == "cuda":
                device = "cuda"
                if torch.cuda.is_available():
                    print(f"[INFO] CUDA détecté pour few-shot embeddings: {torch.cuda.get_device_name(0)}")
                else:
                    print("[WARNING] CUDA non disponible, mais utilisation forcée du GPU pour few-shot embeddings")
            elif Config.DEVICE_PREFERENCE == "auto":
                if torch.cuda.is_available():
                    device = "cuda"
        except Exception:
            if Config.DEVICE_PREFERENCE == "cuda":
                device = "cuda"
        
        _embeddings = NomicEmbeddings(
            model=Config.NomicEmbeddings_model,  # Utiliser le modèle de la config
            inference_mode="local",  # Mode local, pas besoin de token API
            device=device
        )
    return _embeddings

def load_few_shot_examples() -> List[Dict[str, str]]:
    """
    Charge les exemples few-shot depuis le fichier JSON.
    
    Returns:
        Liste de dictionnaires avec 'question' et 'answer'
    """
    examples_file = getattr(Config, 'FEW_SHOT_EXAMPLES_FILE', None)
    if not examples_file or not os.path.exists(examples_file):
        # Créer le fichier avec des exemples par défaut
        default_examples = [
            {
                "question": "What is prompt engineering?",
                "answer": "Prompt engineering is the practice of designing and optimizing prompts to effectively communicate with large language models. It involves crafting input text that guides the model to produce desired outputs, using techniques like few-shot learning, chain-of-thought reasoning, and structured formatting [1]."
            },
            {
                "question": "How do LLM agents work?",
                "answer": "LLM agents are autonomous systems that use large language models to reason, plan, and execute tasks. They typically combine LLMs with tools, memory systems, and decision-making frameworks to perform complex multi-step operations [2]."
            },
            {
                "question": "What are adversarial attacks on LLMs?",
                "answer": "Adversarial attacks on LLMs are techniques designed to manipulate model outputs through carefully crafted inputs. These include prompt injection, jailbreaking, and data poisoning methods that exploit model vulnerabilities [3]."
            }
        ]
        
        # Si examples_file est None, utiliser un chemin par défaut
        if not examples_file:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            examples_file = os.path.join(project_root, "data", "few_shot_examples.json")
        
        # Créer le répertoire si nécessaire
        examples_dir = os.path.dirname(examples_file)
        if examples_dir:
            os.makedirs(examples_dir, exist_ok=True)
        
        # Sauvegarder les exemples par défaut
        with open(examples_file, 'w', encoding='utf-8') as f:
            json.dump(default_examples, f, indent=2, ensure_ascii=False)
        
        return default_examples
    
    try:
        with open(examples_file, 'r', encoding='utf-8') as f:
            examples = json.load(f)
        return examples
    except Exception as e:
        print(f"⚠️ Erreur lors du chargement des exemples few-shot: {str(e)}")
        return []

def select_similar_examples(query: str, num_examples: int = 2) -> List[Dict[str, str]]:
    """
    Sélectionne les exemples les plus similaires à la requête.
    
    Args:
        query: La question de l'utilisateur
        num_examples: Nombre d'exemples à retourner
    
    Returns:
        Liste des exemples les plus similaires
    """
    if not getattr(Config, 'FEW_SHOT_ENABLED', True):
        return []
    
    examples = load_few_shot_examples()
    if not examples:
        return []
    
    if len(examples) <= num_examples:
        return examples[:num_examples]
    
    try:
        embeddings = get_embeddings()
        query_embedding = embeddings.embed_query(query)
        
        # Calculer la similarité pour chaque exemple
        similarities = []
        for example in examples:
            example_embedding = embeddings.embed_query(example['question'])
            # Similarité cosinus
            similarity = sum(a * b for a, b in zip(query_embedding, example_embedding))
            similarities.append((similarity, example))
        
        # Trier par similarité décroissante
        similarities.sort(reverse=True, key=lambda x: x[0])
        
        # Filtrer par seuil et retourner les meilleurs
        threshold = getattr(Config, 'FEW_SHOT_SIMILARITY_THRESHOLD', 0.7)
        selected = [
            example for similarity, example in similarities[:num_examples]
            if similarity >= threshold
        ]
        
        # Retourner les meilleurs même si sous le seuil
        if selected:
            return selected
        else:
            # Extraire les exemples des tuples (similarity, example)
            return [example for _, example in similarities[:num_examples]]
    
    except Exception as e:
        print(f"⚠️ Erreur lors de la sélection des exemples: {str(e)}")
        # Fallback: retourner les premiers exemples
        return examples[:num_examples]

def format_few_shot_examples(examples: List[Dict[str, str]]) -> str:
    """
    Formate les exemples few-shot pour inclusion dans le prompt.
    
    Args:
        examples: Liste d'exemples avec 'question' et 'answer'
    
    Returns:
        Chaîne formatée pour le prompt
    """
    if not examples:
        return ""
    
    formatted = "\n\n## Exemples de Questions-Réponses:\n\n"
    for i, example in enumerate(examples, 1):
        formatted += f"**Exemple {i}:**\n"
        formatted += f"Question: {example['question']}\n"
        formatted += f"Réponse: {example['answer']}\n\n"
    
    formatted += "---\n\n"
    return formatted