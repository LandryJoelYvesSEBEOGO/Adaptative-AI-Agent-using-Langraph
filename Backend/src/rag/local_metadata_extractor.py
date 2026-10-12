"""
Module d'extraction de métadonnées utilisant des modèles locaux (transformers).
Remplace les appels LLM pour l'enrichissement des métadonnées lors de l'ingestion.

Modèles utilisés:
- KeyBERT: Extraction de mots-clés
- spaCy + Transformer NER: Extraction d'entités nommées
- BERTopic: Détection de sujets
- T5/Pegasus: Génération de résumés
"""
import os
import sys
import warnings
from typing import List, Dict
from langchain_core.documents import Document

# Ajouter le répertoire racine au path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.Config import Config

# Désactiver les warnings si configuré
if getattr(Config, 'DISABLE_WARNINGS', True):
    warnings.filterwarnings('ignore')
    os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'

# Fonction helper pour afficher les warnings conditionnellement
def _print_warning(message: str):
    """Affiche un warning seulement si DISABLE_WARNINGS est False."""
    if not getattr(Config, 'DISABLE_WARNINGS', True):
        print(message)

# Variables globales pour les modèles (lazy loading)
_keybert_model = None
_spacy_model = None
_bertopic_model = None
_summarization_model = None
_summarization_tokenizer = None


def _get_keybert_model():
    """Récupère ou crée le modèle KeyBERT (lazy loading)."""
    global _keybert_model
    if _keybert_model is None:
        try:
            from keybert import KeyBERT
            # Utiliser un modèle BERT léger pour KeyBERT
            _keybert_model = KeyBERT(model='all-MiniLM-L6-v2')
            print("[INFO] Modèle KeyBERT chargé")
        except ImportError:
            _print_warning("[WARNING] KeyBERT non installé. Installer avec: pip install keybert")
            return None
        except Exception as e:
            _print_warning(f"[WARNING] Erreur chargement KeyBERT: {e}")
            return None
    return _keybert_model


def _get_spacy_ner_model():
    """Récupère ou crée le modèle spaCy NER (lazy loading)."""
    global _spacy_model
    if _spacy_model is None:
        try:
            import spacy
            # Essayer de charger un modèle avec NER
            try:
                # Essayer d'abord un modèle transformer si disponible
                _spacy_model = spacy.load("en_core_web_trf")
                print("[INFO] Modèle spaCy Transformer (en_core_web_trf) chargé")
            except OSError:
                # Fallback sur le modèle standard
                try:
                    _spacy_model = spacy.load("en_core_web_sm")
                    print("[INFO] Modèle spaCy standard (en_core_web_sm) chargé")
                except OSError:
                    _print_warning("[WARNING] Modèle spaCy non trouvé. Installer avec: python -m spacy download en_core_web_sm")
                    return None
        except ImportError:
            _print_warning("[WARNING] spaCy non installé. Installer avec: pip install spacy")
            return None
        except Exception as e:
            _print_warning(f"[WARNING] Erreur chargement spaCy: {e}")
            return None
    return _spacy_model


def _get_bertopic_model():
    """Récupère ou crée le modèle BERTopic (lazy loading)."""
    global _bertopic_model
    if _bertopic_model is None:
        try:
            from bertopic import BERTopic
            from sentence_transformers import SentenceTransformer
            
            # Utiliser un modèle d'embedding pour BERTopic
            embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            _bertopic_model = BERTopic(
                embedding_model=embedding_model,
                calculate_probabilities=True,
                verbose=False
            )
            print("[INFO] Modèle BERTopic chargé")
        except ImportError:
            _print_warning("[WARNING] BERTopic non installé. Installer avec: pip install bertopic")
            return None
        except Exception as e:
            _print_warning(f"[WARNING] Erreur chargement BERTopic: {e}")
            return None
    return _bertopic_model


def _get_summarization_model():
    """Récupère ou crée le modèle de résumé T5/Pegasus (lazy loading)."""
    global _summarization_model, _summarization_tokenizer
    if _summarization_model is None:
        try:
            from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
            import torch
            
            # Configuration du device (GPU/CPU)
            # Forcer l'utilisation du GPU si configuré
            if Config.DEVICE_PREFERENCE == "cuda":
                device = 0  # GPU
                if torch.cuda.is_available():
                    print(f"[INFO] Utilisation du GPU pour le modèle de résumé: {torch.cuda.get_device_name(0)}")
                else:
                    _print_warning("[WARNING] CUDA non disponible, mais utilisation forcée du GPU (peut causer des erreurs)")
            elif hasattr(Config, 'DEVICE_PREFERENCE') and Config.DEVICE_PREFERENCE == "auto":
                device = 0 if torch.cuda.is_available() else -1
            else:
                device = -1  # CPU
                print("[INFO] Utilisation du CPU pour le modèle de résumé")
            
            # Essayer T5-small d'abord (plus léger)
            model_name = "t5-small"
            try:
                tokenizer = AutoTokenizer.from_pretrained(model_name)
                model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
                _summarization_tokenizer = tokenizer
                _summarization_model = pipeline(
                    "summarization",
                    model=model,
                    tokenizer=tokenizer,
                    device=device
                )
                print(f"[INFO] Modèle de résumé T5-small chargé (device: {'cuda' if device >= 0 else 'cpu'})")
            except Exception as e:
                _print_warning(f"[WARNING] Erreur chargement T5: {e}")
                # Fallback sur un modèle encore plus simple
                try:
                    model_name = "facebook/bart-large-cnn"
                    _summarization_model = pipeline(
                        "summarization",
                        model=model_name,
                        device=device
                    )
                    print(f"[INFO] Modèle de résumé BART chargé (device: {'cuda' if device >= 0 else 'cpu'})")
                except Exception as e2:
                    _print_warning(f"[WARNING] Erreur chargement BART: {e2}")
                    return None
        except ImportError:
            _print_warning("[WARNING] Transformers non installé. Installer avec: pip install transformers")
            return None
        except Exception as e:
            _print_warning(f"[WARNING] Erreur chargement modèle résumé: {e}")
            return None
    return _summarization_model


def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """
    Extrait les mots-clés d'un texte en utilisant KeyBERT.
    
    Args:
        text: Texte à analyser
        max_keywords: Nombre maximum de mots-clés à extraire
    
    Returns:
        Liste de mots-clés
    """
    if not text or not text.strip():
        return []
    
    model = _get_keybert_model()
    if model is None:
        return []
    
    try:
        # KeyBERT extrait les mots-clés avec scores
        keywords_with_scores = model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 2),  # Unigrammes et bigrammes
            stop_words='english',
            top_n=max_keywords,
            use_mmr=True,  # Maximum Marginal Relevance pour diversité
            diversity=0.5
        )
        
        # Extraire juste les mots-clés (sans les scores)
        keywords = [kw[0] for kw in keywords_with_scores if isinstance(kw, tuple)]
        return keywords[:max_keywords]
    
    except Exception as e:
        _print_warning(f"[WARNING] Erreur extraction keywords KeyBERT: {e}")
        return []


def extract_entities(text: str, max_entities: int = 10) -> List[str]:
    """
    Extrait les entités nommées d'un texte en utilisant spaCy NER.
    
    Args:
        text: Texte à analyser
        max_entities: Nombre maximum d'entités à extraire
    
    Returns:
        Liste d'entités nommées (format: "text (label)")
    """
    if not text or not text.strip():
        return []
    
    nlp = _get_spacy_ner_model()
    if nlp is None:
        return []
    
    try:
        # Traiter le texte avec spaCy
        doc = nlp(text)
        
        # Extraire les entités nommées
        entities = []
        seen = set()  # Pour éviter les doublons
        
        for ent in doc.ents:
            # Format: "text (label)" ex: "OpenAI (ORG)"
            entity_str = f"{ent.text} ({ent.label_})"
            if entity_str not in seen:
                entities.append(entity_str)
                seen.add(entity_str)
                if len(entities) >= max_entities:
                    break
        
        return entities[:max_entities]
    
    except Exception as e:
        _print_warning(f"[WARNING] Erreur extraction entities spaCy: {e}")
        return []


def extract_topics(text: str, max_topics: int = 3) -> List[str]:
    """
    Extrait les sujets principaux d'un texte en utilisant BERTopic.
    
    Args:
        text: Texte à analyser
        max_topics: Nombre maximum de sujets à extraire
    
    Returns:
        Liste de sujets
    """
    if not text or not text.strip():
        return []
    
    model = _get_bertopic_model()
    if model is None:
        return []
    
    try:
        # BERTopic fonctionne mieux avec plusieurs documents
        # Pour un seul document, on peut le diviser en phrases
        try:
            from nltk.tokenize import sent_tokenize
            sentences = sent_tokenize(text)
        except ImportError:
            # Fallback si nltk n'est pas disponible
            sentences = [s.strip() for s in text.split('.') if s.strip()]
        except Exception:
            # Autre erreur avec nltk
            sentences = [s.strip() for s in text.split('.') if s.strip()]
        
        if len(sentences) < 2:
            # Si trop peu de phrases, retourner vide
            return []
        
        # Ajuster le modèle pour un petit nombre de documents
        # BERTopic peut avoir des problèmes avec très peu de documents
        if len(sentences) < 5:
            # Utiliser une approche simplifiée : extraire les mots-clés comme sujets
            keywords = extract_keywords(text, max_keywords=max_topics)
            return keywords
        
        # Utiliser BERTopic pour détecter les sujets
        topics, probs = model.fit_transform(sentences)
        
        # Extraire les noms des sujets principaux
        topic_info = model.get_topic_info()
        if topic_info is not None and len(topic_info) > 0:
            # Prendre les top sujets (exclure le topic -1 qui est le bruit)
            valid_topics = topic_info[topic_info['Topic'] != -1]
            if len(valid_topics) > 0:
                top_topics = valid_topics.head(max_topics)
                # Extraire les mots-clés des sujets
                topic_names = []
                for topic_id in top_topics['Topic']:
                    topic_words = model.get_topic(topic_id)
                    if topic_words:
                        # Prendre les 2-3 premiers mots du topic
                        topic_name = " ".join([word[0] for word in topic_words[:2]])
                        topic_names.append(topic_name)
                return topic_names[:max_topics]
        
        return []
    
    except Exception as e:
        _print_warning(f"[WARNING] Erreur extraction topics BERTopic: {e}")
        # Fallback sur KeyBERT si BERTopic échoue
        return extract_keywords(text, max_keywords=max_topics)


def extract_summary(text: str, max_length: int = 100) -> str:
    """
    Génère un résumé d'un texte en utilisant T5 ou Pegasus.
    
    Args:
        text: Texte à résumer
        max_length: Longueur maximale du résumé (en mots)
    
    Returns:
        Résumé du texte
    """
    if not text or not text.strip():
        return ""
    
    model = _get_summarization_model()
    if model is None:
        return ""
    
    try:
        # Limiter la longueur du texte d'entrée (T5 a des limites)
        max_input_length = 512  # Tokens
        # Approximativement 4 caractères par token
        max_chars = max_input_length * 4
        
        if len(text) > max_chars:
            text = text[:max_chars]
        
        # Générer le résumé
        summary = model(
            text,
            max_length=max_length,
            min_length=max_length // 2,
            do_sample=False
        )
        
        if isinstance(summary, list) and len(summary) > 0:
            summary_text = summary[0].get('summary_text', '')
            return summary_text
        elif isinstance(summary, str):
            return summary
        else:
            return ""
    
    except Exception as e:
        _print_warning(f"[WARNING] Erreur génération résumé: {e}")
        return ""


def extract_metadata_local(doc: Document) -> Dict:
    """
    Extrait toutes les métadonnées avancées d'un document en utilisant des modèles locaux.
    
    Args:
        doc: Document LangChain à analyser
    
    Returns:
        Dictionnaire avec keywords, entities, topics, summary
    """
    advanced_metadata = {}
    
    # Vérifier quelles extractions sont activées
    extract_entities_flag = getattr(Config, 'METADATA_EXTRACT_ENTITIES', True)
    extract_keywords_flag = getattr(Config, 'METADATA_EXTRACT_KEYWORDS', True)
    extract_topics_flag = getattr(Config, 'METADATA_EXTRACT_TOPICS', True)
    extract_summary_flag = getattr(Config, 'METADATA_EXTRACT_SUMMARY', True)
    
    # Si aucune extraction n'est activée, retourner vide
    if not any([extract_entities_flag, extract_keywords_flag, extract_topics_flag, extract_summary_flag]):
        return advanced_metadata
    
    try:
        # Pour les documents complets (tous les chunks concaténés), on peut utiliser plus de texte
        # Limiter à 50000 caractères pour les documents complets (au lieu de 5000 pour un chunk)
        # Cela permet d'avoir un meilleur contexte pour l'extraction de métadonnées
        max_content_length = 50000 if len(doc.page_content) > 10000 else 5000
        content = doc.page_content[:max_content_length]
        
        if not content.strip():
            return advanced_metadata
        
        # Récupérer les limites depuis la config
        max_keywords = getattr(Config, 'METADATA_MAX_KEYWORDS', 5)
        max_entities = getattr(Config, 'METADATA_MAX_ENTITIES', 10)
        max_topics = getattr(Config, 'METADATA_MAX_TOPICS', 3)
        summary_length = getattr(Config, 'METADATA_SUMMARY_MAX_LENGTH', 100)
        
        # Extraire les métadonnées selon les flags
        if extract_keywords_flag:
            keywords = extract_keywords(content, max_keywords=max_keywords)
            if keywords:
                advanced_metadata['keywords'] = keywords
        
        if extract_entities_flag:
            entities = extract_entities(content, max_entities=max_entities)
            if entities:
                advanced_metadata['entities'] = entities
        
        if extract_topics_flag:
            topics = extract_topics(content, max_topics=max_topics)
            if topics:
                advanced_metadata['topics'] = topics
        
        if extract_summary_flag:
            summary = extract_summary(content, max_length=summary_length)
            if summary:
                advanced_metadata['summary'] = summary
    
    except Exception as e:
        _print_warning(f"[WARNING] Erreur lors de l'extraction de métadonnées locales: {str(e)}")
        # En cas d'erreur, continuer sans ces métadonnées
    
    return advanced_metadata

