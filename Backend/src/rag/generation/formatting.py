import os
import re
from typing import Dict, List, Tuple
from urllib.parse import urlparse

from langchain_core.documents import Document

from config.Config import Config


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
        return "\n\n".join(doc.page_content for doc in docs if hasattr(doc, "page_content"))

    formatted_parts = []
    for idx, doc in enumerate(docs, start=1):
        if hasattr(doc, "page_content"):
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
        metadata = doc.metadata if hasattr(doc, "metadata") else {}

        # DEBUG: Afficher les métadonnées pour comprendre le problème
        # (à désactiver en production)
        if getattr(Config, "DEBUG_METADATA", False):
            print(f"[DEBUG] Document {idx} metadata: {metadata}")

        # Extraire le numéro de page (PyPDFLoader utilise 'page', parfois 'page_number')
        page_number = None
        if "page" in metadata:
            page_number = metadata.get("page")
            # Si c'est un index (0-based), convertir en numéro de page (1-based)
            if isinstance(page_number, int) and page_number >= 0:
                page_number = page_number + 1  # Convertir de 0-based à 1-based
        elif "page_number" in metadata:
            page_number = metadata.get("page_number")

        # Extraire la source brute depuis les métadonnées (essayer plusieurs clés)
        raw_source = (
            metadata.get("source", "")
            or metadata.get("source_path", "")
            or metadata.get("file_path", "")
            or ""
        )

        # DEBUG: Afficher les métadonnées pour comprendre le problème
        if getattr(Config, "DEBUG_METADATA", False):
            print(f"\n[DEBUG] Document {idx}:")
            print(f"  - raw_source: {raw_source}")
            print(f"  - title: {metadata.get('title', 'N/A')}")
            print(f"  - metadata keys: {list(metadata.keys())}")
            print(f"  - full metadata: {metadata}")

        # Déterminer le nom d'affichage (titre) avec logique intelligente
        display_name = metadata.get("title", "")

        # Nettoyer le titre s'il est invalide (détecter tous les "Document N")
        import re

        is_invalid_title = (
            not display_name
            or display_name == "Unknown source"
            or display_name.startswith("unknown_")
            or display_name.startswith("document_")
            or re.match(r"^Document \d+$", display_name)
            is not None  # Détecte "Document 1", "Document 2", etc.
        )
        if is_invalid_title:
            display_name = ""

        # Si pas de titre valide, extraire depuis la source
        if not display_name:
            if (
                raw_source
                and raw_source not in ["Unknown source", ""]
                and not raw_source.startswith("unknown_")
            ):
                # Vérifier si c'est une URL
                if raw_source.startswith("http://") or raw_source.startswith("https://"):
                    # C'est une URL web : formater le nom de la page
                    try:
                        parsed = urlparse(raw_source)
                        # Créer un nom lisible : domaine + chemin simplifié
                        domain = parsed.netloc.replace("www.", "")
                        path = parsed.path.strip("/").replace("/", " - ")
                        if path:
                            display_name = f"{domain} - {path}"
                        else:
                            display_name = domain
                    except:
                        display_name = raw_source
                # Vérifier si c'est un chemin de fichier (PDF)
                elif "/" in raw_source or "\\" in raw_source:
                    # C'est un fichier : extraire le nom sans extension
                    filename = os.path.basename(raw_source.replace("\\", "/"))
                    if filename.endswith(".pdf"):
                        display_name = filename[:-4]  # Enlever .pdf
                    else:
                        display_name = filename
                else:
                    # Source simple, l'utiliser directement
                    display_name = raw_source

        # Si toujours pas de nom valide après tous les essais
        if (
            not display_name
            or display_name in ["Unknown source", "Document 1", "Document 2", "Document 3"]
            or re.match(r"^Document \d+$", display_name)
        ):
            # Essayer d'autres métadonnées comme dernier recours
            # Chercher dans toutes les métadonnées pour trouver un chemin ou un nom
            for key, value in metadata.items():
                if value and isinstance(value, str):
                    # Si on trouve un chemin de fichier dans n'importe quelle métadonnée
                    if ("/" in value or "\\" in value) and (
                        value.endswith(".pdf") or ".pdf" in value
                    ):
                        filename = os.path.basename(value.replace("\\", "/"))
                        if filename.endswith(".pdf"):
                            display_name = filename[:-4]
                        else:
                            display_name = filename
                        break
                    # Si on trouve une URL
                    elif value.startswith("http://") or value.startswith("https://"):
                        try:
                            parsed = urlparse(value)
                            domain = parsed.netloc.replace("www.", "")
                            path = parsed.path.strip("/").replace("/", " - ")
                            if path:
                                display_name = f"{domain} - {path}"
                            else:
                                display_name = domain
                            break
                        except:
                            pass

            # Si toujours rien, utiliser le numéro de page si disponible
            if (
                not display_name
                or display_name in ["Unknown source", "Document 1", "Document 2", "Document 3"]
                or re.match(r"^Document \d+$", display_name)
            ):
                if page_number is not None:
                    display_name = f"Document (page {page_number})"
                else:
                    # Utiliser l'index mais seulement en dernier recours
                    display_name = f"Document {idx}"

        # Pour la source technique, garder la source brute ou utiliser le display_name
        source = (
            raw_source if raw_source and not raw_source.startswith("unknown_") else display_name
        )

        source_info = {
            "number": idx,
            "source": source,
            "parent_doc_id": metadata.get("parent_doc_id", ""),
            "chunk_id": metadata.get("chunk_id", ""),
            "title": display_name,  # Utiliser le nom d'affichage calculé
            "page": page_number,  # Ajouter le numéro de page
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
    citation_pattern = r"\[(\d+)\]"
    citations_used = set()

    def replace_citation(match):
        num = int(match.group(1))
        if 1 <= num <= len(sources):
            citations_used.add(num)
            return f"[{num}]"
        return match.group(0)

    # Remplacer les citations par des références formatées
    response_formatted = re.sub(citation_pattern, replace_citation, response)

    # Créer la section des références
    if citations_used:
        references_parts = ["\n\n**Références:**"]
        for num in sorted(citations_used):
            source_info = sources[num - 1]  # -1 car les indices commencent à 0

            # Déterminer le nom à afficher (toujours utiliser le titre calculé)
            source_display = source_info.get("title", "")

            # Si le titre n'est pas valide, extraire depuis la source
            if (
                not source_display
                or source_display == "Unknown source"
                or source_display.startswith("unknown_")
            ):
                source_path = source_info.get("source", "")
                if source_path:
                    # Vérifier si c'est une URL
                    if source_path.startswith("http://") or source_path.startswith("https://"):
                        try:
                            parsed = urlparse(source_path)
                            domain = parsed.netloc.replace("www.", "")
                            path = parsed.path.strip("/").replace("/", " - ")
                            if path:
                                source_display = f"{domain} - {path}"
                            else:
                                source_display = domain
                        except:
                            source_display = source_path
                    # Vérifier si c'est un chemin de fichier
                    elif "/" in source_path or "\\" in source_path:
                        filename = os.path.basename(source_path.replace("\\", "/"))
                        if filename.endswith(".pdf"):
                            source_display = filename[:-4]
                        else:
                            source_display = filename
                    else:
                        source_display = source_path
                else:
                    source_display = f"Document {num}"

            # S'assurer qu'on n'a jamais "Unknown source"
            if source_display == "Unknown source" or source_display.startswith("unknown_"):
                source_display = f"Document {num}"

            # Ajouter le numéro de page si disponible
            page_number = source_info.get("page")
            if page_number is not None:
                # Formater avec le numéro de page
                references_parts.append(f"[{num}] {source_display} (page {page_number})")
            else:
                references_parts.append(f"[{num}] {source_display}")

        references_section = "\n".join(references_parts)
    else:
        references_section = ""

    return response_formatted, references_section
