"""
Script de test pour les citations automatiques
"""

import os
import sys

# Ajouter le répertoire racine au sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from langchain.schema import Document

from src.rag.Rag_model import extract_sources_from_documents, format_citations, format_docs


def test_format_docs_without_citations():
    """Test format_docs sans citations."""
    print("\n" + "=" * 60)
    print("TEST 1: format_docs sans citations")
    print("=" * 60)

    docs = [
        Document(page_content="Premier document sur Python.", metadata={"source": "doc1.pdf"}),
        Document(page_content="Deuxième document sur LangChain.", metadata={"source": "doc2.pdf"}),
    ]

    result = format_docs(docs, with_citations=False)
    print(f"Résultat:\n{result}")

    # Vérifier qu'il n'y a pas de numéros [Document X]
    assert "[Document 1]" not in result, "Ne devrait pas contenir [Document 1]"
    assert "[Document 2]" not in result, "Ne devrait pas contenir [Document 2]"
    assert "Premier document" in result, "Devrait contenir le contenu du premier document"
    assert "Deuxième document" in result, "Devrait contenir le contenu du deuxième document"

    print("✅ Test format_docs sans citations réussi!")


def test_format_docs_with_citations():
    """Test format_docs avec citations."""
    print("\n" + "=" * 60)
    print("TEST 2: format_docs avec citations")
    print("=" * 60)

    docs = [
        Document(page_content="Premier document sur Python.", metadata={"source": "doc1.pdf"}),
        Document(page_content="Deuxième document sur LangChain.", metadata={"source": "doc2.pdf"}),
    ]

    result = format_docs(docs, with_citations=True)
    print(f"Résultat:\n{result}")

    # Vérifier qu'il y a des numéros [Document X]
    assert "[Document 1]" in result, "Devrait contenir [Document 1]"
    assert "[Document 2]" in result, "Devrait contenir [Document 2]"
    assert "Premier document" in result, "Devrait contenir le contenu du premier document"
    assert "Deuxième document" in result, "Devrait contenir le contenu du deuxième document"

    print("✅ Test format_docs avec citations réussi!")


def test_extract_sources_from_documents():
    """Test extract_sources_from_documents."""
    print("\n" + "=" * 60)
    print("TEST 3: extract_sources_from_documents")
    print("=" * 60)

    docs = [
        Document(
            page_content="Contenu du premier document.",
            metadata={
                "source": "data/documents/python_guide.pdf",
                "parent_doc_id": "doc_001",
                "chunk_id": "chunk_001",
                "title": "Guide Python",
            },
        ),
        Document(
            page_content="Contenu du deuxième document.",
            metadata={
                "source": "data/documents/langchain_tutorial.pdf",
                "parent_doc_id": "doc_002",
                "chunk_id": "chunk_002",
            },
        ),
    ]

    sources = extract_sources_from_documents(docs)

    print(f"Nombre de sources extraites: {len(sources)}")
    for i, source in enumerate(sources, 1):
        print(f"  Source {i}: {source}")

    # Vérifications
    assert len(sources) == 2, "Devrait extraire 2 sources"
    assert sources[0]["number"] == 1, "Premier document devrait avoir le numéro 1"
    assert sources[1]["number"] == 2, "Deuxième document devrait avoir le numéro 2"
    assert sources[0]["source"] == "data/documents/python_guide.pdf", "Source incorrecte"
    assert sources[0]["title"] == "Guide Python", "Titre devrait être 'Guide Python'"
    assert sources[1]["title"] == "langchain_tutorial.pdf", "Titre devrait être le nom du fichier"

    print("✅ Test extract_sources_from_documents réussi!")


def test_format_citations_with_citations():
    """Test format_citations avec des citations dans la réponse."""
    print("\n" + "=" * 60)
    print("TEST 4: format_citations avec citations")
    print("=" * 60)

    response = "Python est un langage de programmation [1] qui supporte plusieurs paradigmes [2]. LangChain est une bibliothèque [2] pour Python [1]."

    sources = [
        {"number": 1, "source": "python_guide.pdf", "title": "Guide Python"},
        {"number": 2, "source": "langchain_tutorial.pdf", "title": "Tutoriel LangChain"},
    ]

    formatted_response, references = format_citations(response, sources)

    print(f"Réponse originale:\n{response}\n")
    print(f"Réponse formatée:\n{formatted_response}\n")
    print(f"Références:\n{references}\n")

    # Vérifications
    assert "[1]" in formatted_response, "Devrait contenir [1]"
    assert "[2]" in formatted_response, "Devrait contenir [2]"
    assert "**Références:**" in references, "Devrait contenir la section Références"
    assert "[1]" in references, "Devrait contenir [1] dans les références"
    assert "[2]" in references, "Devrait contenir [2] dans les références"
    assert "Guide Python" in references, "Devrait contenir 'Guide Python'"
    assert "Tutoriel LangChain" in references, "Devrait contenir 'Tutoriel LangChain'"

    print("✅ Test format_citations avec citations réussi!")


def test_format_citations_without_citations():
    """Test format_citations sans citations dans la réponse."""
    print("\n" + "=" * 60)
    print("TEST 5: format_citations sans citations")
    print("=" * 60)

    response = "Python est un langage de programmation qui supporte plusieurs paradigmes."

    sources = [
        {"number": 1, "source": "python_guide.pdf", "title": "Guide Python"},
        {"number": 2, "source": "langchain_tutorial.pdf", "title": "Tutoriel LangChain"},
    ]

    formatted_response, references = format_citations(response, sources)

    print(f"Réponse originale:\n{response}\n")
    print(f"Réponse formatée:\n{formatted_response}\n")
    print(f"Références:\n{references}\n")

    # Vérifications
    assert formatted_response == response, "La réponse ne devrait pas changer"
    assert references == "", "Les références devraient être vides"

    print("✅ Test format_citations sans citations réussi!")


def test_format_citations_invalid_numbers():
    """Test format_citations avec des numéros invalides."""
    print("\n" + "=" * 60)
    print("TEST 6: format_citations avec numéros invalides")
    print("=" * 60)

    response = "Python est un langage [1] mais aussi [5] et [10] qui n'existent pas."

    sources = [
        {"number": 1, "source": "python_guide.pdf", "title": "Guide Python"},
        {"number": 2, "source": "langchain_tutorial.pdf", "title": "Tutoriel LangChain"},
    ]

    formatted_response, references = format_citations(response, sources)

    print(f"Réponse originale:\n{response}\n")
    print(f"Réponse formatée:\n{formatted_response}\n")
    print(f"Références:\n{references}\n")

    # Vérifications
    assert "[1]" in formatted_response, "Devrait contenir [1]"
    assert "[5]" in formatted_response, "[5] devrait rester car invalide"
    assert "[10]" in formatted_response, "[10] devrait rester car invalide"
    assert "Guide Python" in references, "Devrait contenir 'Guide Python' pour [1]"

    print("✅ Test format_citations avec numéros invalides réussi!")


def test_format_citations_empty_sources():
    """Test format_citations avec sources vides."""
    print("\n" + "=" * 60)
    print("TEST 7: format_citations avec sources vides")
    print("=" * 60)

    response = "Python est un langage de programmation [1]."

    sources = []

    formatted_response, references = format_citations(response, sources)

    print(f"Réponse originale:\n{response}\n")
    print(f"Réponse formatée:\n{formatted_response}\n")
    print(f"Références:\n{references}\n")

    # Vérifications
    assert formatted_response == response, "La réponse ne devrait pas changer"
    assert references == "", "Les références devraient être vides"

    print("✅ Test format_citations avec sources vides réussi!")


def test_format_docs_empty_list():
    """Test format_docs avec une liste vide."""
    print("\n" + "=" * 60)
    print("TEST 8: format_docs avec liste vide")
    print("=" * 60)

    docs = []

    result_with_citations = format_docs(docs, with_citations=True)
    result_without_citations = format_docs(docs, with_citations=False)

    print(f"Avec citations: '{result_with_citations}'")
    print(f"Sans citations: '{result_without_citations}'")

    # Vérifications
    assert result_with_citations == "", "Devrait retourner une chaîne vide"
    assert result_without_citations == "", "Devrait retourner une chaîne vide"

    print("✅ Test format_docs avec liste vide réussi!")


def main():
    """Exécute tous les tests."""
    print("\n" + "=" * 60)
    print("TESTS DES CITATIONS AUTOMATIQUES")
    print("=" * 60)

    try:
        test_format_docs_without_citations()
        test_format_docs_with_citations()
        test_extract_sources_from_documents()
        test_format_citations_with_citations()
        test_format_citations_without_citations()
        test_format_citations_invalid_numbers()
        test_format_citations_empty_sources()
        test_format_docs_empty_list()

        print("\n" + "=" * 60)
        print("✅ TOUS LES TESTS SONT PASSES AVEC SUCCES!")
        print("=" * 60)
        print("\nLes citations automatiques fonctionnent correctement.")
        print("Vous pouvez maintenant tester avec get_final_response() pour voir")
        print("les citations dans une réponse complète du RAG.")

    except AssertionError as e:
        print(f"\n❌ ERREUR DE TEST: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERREUR INATTENDUE: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
