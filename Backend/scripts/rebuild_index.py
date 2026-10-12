import os
import sys
import warnings
import re
from pathlib import Path

# S'assurer qu'on est à la racine du projet backend
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.Config import Config

DISABLE_WARNINGS = True 
# Désactiver les warnings si configuré
if getattr(Config, 'DISABLE_WARNINGS', True):
    # Désactiver tous les warnings Python
    warnings.filterwarnings('ignore')
    
    # Intercepter sys.stderr pour filtrer les warnings embedInternal qui sont affichés via print()
    original_stderr = sys.stderr
    
    class FilteredStderr:
        """Filtre les messages embedInternal avant de les écrire dans stderr."""
        def __init__(self, original):
            self.original = original
        
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
    
    # Désactiver les warnings spécifiques de transformers
    os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from src.rag.Data_processing import (
    load_web_documents,
    load_pdf_documents_from_folder,
    split_documents,
    get_or_create_chroma_db,
    _save_bm25_documents,
    CHROMA_DB_DIR,
    BM25_DOCS_CACHE,
    urls,
)

# Importer tqdm pour les barres de progression
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = getattr(Config, 'SHOW_PROGRESS_BARS', True)
except ImportError:
    TQDM_AVAILABLE = False
    # Créer une fonction dummy pour tqdm si non disponible
    def tqdm(iterable, *args, **kwargs):
        return iterable

def rebuild_indexes(clear_db: bool = True, k: int = 3):
    print("=== REBUILD INDEXES (ChromaDB + BM25) ===")
    print(f"Project root: {project_root}")
    print(f"ChromaDB directory: {CHROMA_DB_DIR}")
    print()

    # 1) Charger les documents web
    print("[STEP 1] Chargement des documents web...")
    try:
        if TQDM_AVAILABLE and len(urls) > 1:
            web_docs = []
            for url in tqdm(urls, desc="Chargement URLs", unit="URL"):
                try:
                    from langchain_community.document_loaders import WebBaseLoader
                    docs = WebBaseLoader(url).load()
                    for doc in docs:
                        if not doc.metadata.get("source"):
                            doc.metadata["source"] = url
                        if not doc.metadata.get("title"):
                            from urllib.parse import urlparse
                            parsed = urlparse(url)
                            title = parsed.netloc + parsed.path.replace("/", "_")
                            doc.metadata["title"] = title
                    web_docs.extend(docs)
                except Exception as e:
                    if not getattr(Config, 'DISABLE_WARNINGS', True):
                        print(f"⚠️ Erreur lors du chargement de {url}: {str(e)}")
        else:
            web_docs = load_web_documents(urls)
        print(f"[OK] {len(web_docs)} documents web chargés.")
    except Exception as e:
        print(f"[WARN] Erreur chargement web_docs: {e}")
        web_docs = []

    # 2) Charger tous les PDFs dans data/raw
    print("\n[STEP 2] Chargement des PDFs...")
    raw_data_folder = os.path.join(project_root, "data", "raw")
    from src.rag.Data_processing import load_pdf_documents_from_folder

    pdf_docs = []
    if os.path.exists(raw_data_folder):
        try:
            pdf_docs = load_pdf_documents_from_folder(raw_data_folder)
            print(f"[OK] {len(pdf_docs)} documents PDF chargés.")
        except Exception as e:
            print(f"[WARN] Erreur chargement PDFs: {e}")
    else:
        print(f"[INFO] Dossier {raw_data_folder} inexistant, aucun PDF chargé.")

    all_docs = web_docs + pdf_docs
    if not all_docs:
        print("[ERROR] Aucun document trouvé à indexer. Vérifiez vos sources (URLs, PDFs).")
        return

    # 3) Chunking + enrichissement des métadonnées
    print("\n[STEP 3] Segmentation + enrichissement des documents...")
    doc_splits = split_documents(all_docs)
    print(f"[OK] {len(doc_splits)} chunks créés.")

    # 4) Recréation de la base ChromaDB
    print("\n[STEP 4] Création / Recréation de ChromaDB...")
    vectorstore = get_or_create_chroma_db(doc_splits, CHROMA_DB_DIR, clear_db=clear_db)
    print("[OK] Base ChromaDB prête.")

    # 5) Suppression et recréation du cache BM25
    print("\n[STEP 5] Suppression et recréation du cache BM25...")
    if os.path.exists(BM25_DOCS_CACHE):
        try:
            os.remove(BM25_DOCS_CACHE)
            print("[INFO] Ancien cache BM25 supprimé.")
        except Exception as e:
            print(f"[WARNING] Impossible de supprimer l'ancien cache BM25: {str(e)}")
    _save_bm25_documents(doc_splits)
    print("[OK] Nouveau cache BM25 sauvegardé.")

    print("\n=== REBUILD DONE ===")

if __name__ == "__main__":
    # clear_db=True => efface complètement la base existante avant de recréer
    rebuild_indexes(clear_db=True, k=3)