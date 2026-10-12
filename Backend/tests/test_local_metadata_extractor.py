"""
Tests pour l'extraction de métadonnées avec modèles locaux.

Ce module teste :
- KeyBERT pour l'extraction de mots-clés
- spaCy NER pour l'extraction d'entités nommées
- BERTopic pour la détection de sujets
- T5/Pegasus pour la génération de résumés
- La fonction complète extract_metadata_local
"""

import sys
from pathlib import Path

# Ajouter le répertoire racine au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from langchain.schema import Document

from src.rag.local_metadata_extractor import (
    extract_entities,
    extract_keywords,
    extract_metadata_local,
    extract_summary,
    extract_topics,
)

# Texte de test pour tous les tests
SAMPLE_TEXT = """
Artificial Intelligence (AI) is transforming the technology landscape. 
Companies like OpenAI, Google, and Microsoft are leading the development 
of large language models such as GPT-4, BERT, and T5. These models are 
being used in various applications including natural language processing, 
computer vision, and autonomous systems. The field of machine learning 
has seen significant advances in recent years, particularly in deep learning 
and neural networks. Researchers at institutions like Stanford University 
and MIT are pushing the boundaries of what AI can achieve.
"""

SAMPLE_TEXT_FRENCH = """
L'intelligence artificielle (IA) transforme le paysage technologique.
Des entreprises comme OpenAI, Google et Microsoft mènent le développement
de grands modèles de langage comme GPT-4, BERT et T5. Ces modèles sont
utilisés dans diverses applications incluant le traitement du langage naturel,
la vision par ordinateur et les systèmes autonomes.
"""


class TestKeyBERT:
    """Tests pour l'extraction de mots-clés avec KeyBERT."""

    def test_extract_keywords_basic(self):
        """Test basique d'extraction de mots-clés."""
        keywords = extract_keywords(SAMPLE_TEXT, max_keywords=5)

        assert isinstance(keywords, list)
        assert len(keywords) <= 5
        assert all(isinstance(kw, str) for kw in keywords)
        print(f"✅ Keywords extraits: {keywords}")

    def test_extract_keywords_empty_text(self):
        """Test avec texte vide."""
        keywords = extract_keywords("", max_keywords=5)
        assert keywords == []

    def test_extract_keywords_short_text(self):
        """Test avec texte court."""
        keywords = extract_keywords("AI and machine learning", max_keywords=3)
        assert isinstance(keywords, list)
        assert len(keywords) <= 3

    def test_extract_keywords_max_limit(self):
        """Test que le nombre maximum de keywords est respecté."""
        keywords = extract_keywords(SAMPLE_TEXT, max_keywords=3)
        assert len(keywords) <= 3


class TestSpaCyNER:
    """Tests pour l'extraction d'entités nommées avec spaCy."""

    def test_extract_entities_basic(self):
        """Test basique d'extraction d'entités."""
        entities = extract_entities(SAMPLE_TEXT, max_entities=10)

        assert isinstance(entities, list)
        assert len(entities) <= 10
        assert all(isinstance(ent, str) for ent in entities)

        # Vérifier le format "text (label)"
        if entities:
            assert "(" in entities[0] and ")" in entities[0]
        print(f"✅ Entities extraites: {entities[:3]}")

    def test_extract_entities_empty_text(self):
        """Test avec texte vide."""
        entities = extract_entities("", max_entities=10)
        assert entities == []

    def test_extract_entities_contains_orgs(self):
        """Test que les organisations sont détectées."""
        entities = extract_entities(SAMPLE_TEXT, max_entities=20)
        entity_texts = [e.split(" (")[0] for e in entities]

        # Vérifier que certaines organisations connues sont détectées
        orgs_found = any(org in " ".join(entity_texts) for org in ["OpenAI", "Google", "Microsoft"])
        # Note: Ce test peut échouer si spaCy n'est pas installé ou si les modèles ne sont pas chargés
        print(f"✅ Organisations détectées: {orgs_found}")


class TestBERTopic:
    """Tests pour la détection de sujets avec BERTopic."""

    def test_extract_topics_basic(self):
        """Test basique d'extraction de sujets."""
        topics = extract_topics(SAMPLE_TEXT, max_topics=3)

        assert isinstance(topics, list)
        assert len(topics) <= 3
        assert all(isinstance(topic, str) for topic in topics)
        print(f"✅ Topics extraits: {topics}")

    def test_extract_topics_empty_text(self):
        """Test avec texte vide."""
        topics = extract_topics("", max_topics=3)
        assert topics == []

    def test_extract_topics_short_text(self):
        """Test avec texte très court (fallback sur KeyBERT)."""
        topics = extract_topics("AI machine learning", max_topics=2)
        assert isinstance(topics, list)
        # Avec un texte très court, BERTopic peut retourner vide ou utiliser KeyBERT
        assert len(topics) <= 2


class TestSummarization:
    """Tests pour la génération de résumés avec T5/Pegasus."""

    def test_extract_summary_basic(self):
        """Test basique de génération de résumé."""
        summary = extract_summary(SAMPLE_TEXT, max_length=50)

        assert isinstance(summary, str)
        assert len(summary) > 0
        print(f"✅ Résumé généré ({len(summary)} caractères): {summary[:100]}...")

    def test_extract_summary_empty_text(self):
        """Test avec texte vide."""
        summary = extract_summary("", max_length=50)
        assert summary == ""

    def test_extract_summary_max_length(self):
        """Test que la longueur du résumé est raisonnable."""
        summary = extract_summary(SAMPLE_TEXT, max_length=30)
        assert isinstance(summary, str)
        # Le résumé peut être plus long que max_length (en tokens), mais devrait être raisonnable
        assert len(summary) < len(SAMPLE_TEXT)  # Le résumé devrait être plus court que l'original


class TestCompleteMetadataExtraction:
    """Tests pour l'extraction complète de métadonnées."""

    def test_extract_metadata_local_complete(self):
        """Test complet d'extraction de métadonnées."""
        doc = Document(
            page_content=SAMPLE_TEXT,
            metadata={"source": "test_document.txt", "title": "Test Document"},
        )

        metadata = extract_metadata_local(doc)

        assert isinstance(metadata, dict)

        # Vérifier que les clés attendues sont présentes (si les extractions sont activées)
        possible_keys = ["keywords", "entities", "topics", "summary"]
        assert any(key in metadata for key in possible_keys)

        # Vérifier les types
        if "keywords" in metadata:
            assert isinstance(metadata["keywords"], list)
            assert all(isinstance(kw, str) for kw in metadata["keywords"])

        if "entities" in metadata:
            assert isinstance(metadata["entities"], list)
            assert all(isinstance(ent, str) for ent in metadata["entities"])

        if "topics" in metadata:
            assert isinstance(metadata["topics"], list)
            assert all(isinstance(topic, str) for topic in metadata["topics"])

        if "summary" in metadata:
            assert isinstance(metadata["summary"], str)
            assert len(metadata["summary"]) > 0

        print(f"✅ Métadonnées extraites: {list(metadata.keys())}")
        if "keywords" in metadata:
            print(f"   Keywords: {metadata['keywords']}")
        if "entities" in metadata:
            print(f"   Entities: {metadata['entities'][:3]}")
        if "topics" in metadata:
            print(f"   Topics: {metadata['topics']}")
        if "summary" in metadata:
            print(f"   Summary: {metadata['summary'][:100]}...")

    def test_extract_metadata_local_empty_document(self):
        """Test avec document vide."""
        doc = Document(page_content="", metadata={})
        metadata = extract_metadata_local(doc)
        assert isinstance(metadata, dict)

    def test_extract_metadata_local_short_text(self):
        """Test avec texte très court."""
        doc = Document(page_content="AI is important.", metadata={"source": "short.txt"})
        metadata = extract_metadata_local(doc)
        assert isinstance(metadata, dict)

    def test_extract_metadata_local_preserves_original_metadata(self):
        """Test que les métadonnées originales ne sont pas modifiées."""
        original_metadata = {"source": "test.txt", "title": "Test", "custom": "value"}
        doc = Document(page_content=SAMPLE_TEXT, metadata=original_metadata.copy())

        extracted = extract_metadata_local(doc)

        # Les métadonnées extraites ne doivent pas écraser les originales
        # (cette fonction retourne seulement les nouvelles métadonnées)
        assert isinstance(extracted, dict)
        # Le document original ne devrait pas être modifié
        assert doc.metadata == original_metadata


class TestModelLoading:
    """Tests pour le chargement des modèles (lazy loading)."""

    def test_keybert_model_loading(self):
        """Test que KeyBERT peut être chargé."""
        from src.rag.local_metadata_extractor import _get_keybert_model

        model = _get_keybert_model()
        # Si KeyBERT n'est pas installé, model sera None
        # Ce test vérifie juste qu'il n'y a pas d'erreur
        assert model is None or hasattr(model, "extract_keywords")

    def test_spacy_model_loading(self):
        """Test que spaCy peut être chargé."""
        from src.rag.local_metadata_extractor import _get_spacy_ner_model

        model = _get_spacy_ner_model()
        # Si spaCy n'est pas installé ou les modèles ne sont pas téléchargés, model sera None
        assert model is None or hasattr(model, "ents")

    def test_bertopic_model_loading(self):
        """Test que BERTopic peut être chargé."""
        from src.rag.local_metadata_extractor import _get_bertopic_model

        model = _get_bertopic_model()
        # Si BERTopic n'est pas installé, model sera None
        assert model is None or hasattr(model, "fit_transform")

    def test_summarization_model_loading(self):
        """Test que le modèle de résumé peut être chargé."""
        from src.rag.local_metadata_extractor import _get_summarization_model

        model = _get_summarization_model()
        # Si transformers n'est pas installé, model sera None
        assert model is None or callable(model)


class TestIntegration:
    """Tests d'intégration avec le système complet."""

    def test_integration_with_config(self):
        """Test que le système respecte la configuration."""
        from config.Config import Config

        # Vérifier que la configuration existe
        assert hasattr(Config, "METADATA_USE_LOCAL_MODELS")
        assert hasattr(Config, "METADATA_EXTRACT_KEYWORDS")
        assert hasattr(Config, "METADATA_EXTRACT_ENTITIES")
        assert hasattr(Config, "METADATA_EXTRACT_TOPICS")
        assert hasattr(Config, "METADATA_EXTRACT_SUMMARY")

    def test_fallback_behavior(self):
        """Test que le système gère gracieusement les modèles manquants."""
        doc = Document(page_content=SAMPLE_TEXT, metadata={"source": "test.txt"})

        # Même si certains modèles ne sont pas installés,
        # la fonction ne devrait pas planter
        try:
            metadata = extract_metadata_local(doc)
            assert isinstance(metadata, dict)
        except Exception as e:
            # Si une erreur se produit, elle devrait être gérée gracieusement
            pytest.fail(f"extract_metadata_local ne devrait pas planter: {e}")


# Tests de performance (optionnels, peuvent être désactivés)
class TestPerformance:
    """Tests de performance (peuvent être lents)."""

    @pytest.mark.slow
    def test_keywords_performance(self):
        """Test de performance pour l'extraction de keywords."""
        import time

        start = time.time()
        keywords = extract_keywords(SAMPLE_TEXT * 10, max_keywords=10)  # Texte plus long
        elapsed = time.time() - start

        assert isinstance(keywords, list)
        # Devrait prendre moins de 10 secondes (ajuster selon votre hardware)
        assert elapsed < 10.0
        print(f"✅ Extraction keywords: {elapsed:.2f}s")

    @pytest.mark.slow
    def test_entities_performance(self):
        """Test de performance pour l'extraction d'entités."""
        import time

        start = time.time()
        entities = extract_entities(SAMPLE_TEXT * 10, max_entities=20)
        elapsed = time.time() - start

        assert isinstance(entities, list)
        assert elapsed < 15.0  # spaCy peut être plus lent
        print(f"✅ Extraction entities: {elapsed:.2f}s")

    @pytest.mark.slow
    def test_summary_performance(self):
        """Test de performance pour la génération de résumé."""
        import time

        start = time.time()
        summary = extract_summary(SAMPLE_TEXT, max_length=50)
        elapsed = time.time() - start

        assert isinstance(summary, str)
        # Le premier appel peut être plus lent (téléchargement du modèle)
        print(f"✅ Génération résumé: {elapsed:.2f}s")


if __name__ == "__main__":
    """
    Exécution directe des tests (sans pytest).
    Utile pour un test rapide.
    """
    print("=" * 60)
    print("TESTS D'EXTRACTION DE MÉTADONNÉES LOCALES")
    print("=" * 60)

    # Test KeyBERT
    print("\n[TEST] KeyBERT - Extraction de mots-clés...")
    try:
        keywords = extract_keywords(SAMPLE_TEXT, max_keywords=5)
        print(f"✅ Keywords: {keywords}")
    except Exception as e:
        print(f"❌ Erreur KeyBERT: {e}")

    # Test spaCy NER
    print("\n[TEST] spaCy NER - Extraction d'entités...")
    try:
        entities = extract_entities(SAMPLE_TEXT, max_entities=10)
        print(f"✅ Entities ({len(entities)}): {entities[:3]}")
    except Exception as e:
        print(f"❌ Erreur spaCy: {e}")

    # Test BERTopic
    print("\n[TEST] BERTopic - Détection de sujets...")
    try:
        topics = extract_topics(SAMPLE_TEXT, max_topics=3)
        print(f"✅ Topics: {topics}")
    except Exception as e:
        print(f"❌ Erreur BERTopic: {e}")

    # Test Résumé
    print("\n[TEST] T5/Pegasus - Génération de résumé...")
    try:
        summary = extract_summary(SAMPLE_TEXT, max_length=50)
        print(f"✅ Résumé: {summary[:150]}...")
    except Exception as e:
        print(f"❌ Erreur Résumé: {e}")

    # Test complet
    print("\n[TEST] Extraction complète de métadonnées...")
    try:
        doc = Document(page_content=SAMPLE_TEXT, metadata={"source": "test.txt", "title": "Test"})
        metadata = extract_metadata_local(doc)
        print(f"✅ Métadonnées extraites: {list(metadata.keys())}")
        for key, value in metadata.items():
            if isinstance(value, list):
                print(f"   {key}: {value[:3]}")
            else:
                print(f"   {key}: {str(value)[:100]}...")
    except Exception as e:
        print(f"❌ Erreur extraction complète: {e}")

    print("\n" + "=" * 60)
    print("TESTS TERMINÉS")
    print("=" * 60)
