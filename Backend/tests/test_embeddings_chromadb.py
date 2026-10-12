"""
Script de diagnostic pour identifier le blocage:
- Test 1: NomicEmbeddings seul (sans ChromaDB)
- Test 2: ChromaDB seul (lecture)
- Test 3: ChromaDB + NomicEmbeddings (retriever complet)
"""

import os
import sys
import threading
import time
import traceback

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv

load_dotenv()

print("=" * 80)
print("DIAGNOSTIC COMPLET: NomicEmbeddings + ChromaDB")
print("=" * 80)
print()

# Configuration
from config.Config import Config

CHROMA_DB_DIR = os.path.join(project_root, "chroma_db")

# ============================================================================
# TEST 1: NomicEmbeddings seul (sans ChromaDB)
# ============================================================================
print("TEST 1: NomicEmbeddings SEUL (sans ChromaDB)")
print("-" * 80)

try:
    import torch
    from langchain_nomic.embeddings import NomicEmbeddings

    # Détection du device
    device = "cpu"
    if torch.cuda.is_available():
        device = "cuda"
        print(f"[INFO] CUDA détecté: {torch.cuda.get_device_name(0)}")
        print(
            f"[INFO] Mémoire GPU disponible: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB"
        )
    else:
        print("[INFO] CUDA non disponible, utilisation du CPU")

    print(f"\n[1.1] Création du modèle NomicEmbeddings (device: {device})...")
    start = time.time()
    try:
        embedding_model = NomicEmbeddings(
            model=Config.NomicEmbeddings_model, inference_mode="local", device=device
        )
        creation_time = time.time() - start
        print(f"[OK] Modele cree en {creation_time:.2f}s")
    except Exception as e:
        print(f"[ERREUR] Erreur lors de la creation: {str(e)}")
        traceback.print_exc()
        raise

    # Test d'embedding avec timeout
    print("\n[1.2] Test génération d'embedding (peut prendre 10-60s)...")
    print("     Si ça bloque plus de 2 minutes, appuyez sur Ctrl+C")

    result_container = [None]
    exception_container = [None]
    start_embed = time.time()

    def embed_test():
        try:
            test_text = "What is a large language model?"
            print(f"     Texte test: '{test_text}'")
            result_container[0] = embedding_model.embed_query(test_text)
        except Exception as e:
            exception_container[0] = e

    # Thread avec timeout
    thread = threading.Thread(target=embed_test, daemon=True)
    thread.start()
    thread.join(timeout=120)  # 2 minutes max

    elapsed = time.time() - start_embed

    if thread.is_alive():
        print(f"[ERREUR] TIMEOUT après {elapsed:.2f}s")
        print("    Le modèle NomicEmbeddings bloque lors de l'embedding!")
        print("    → PROBLÈME IDENTIFIÉ: NomicEmbeddings")
        nomic_ok = False
    elif exception_container[0]:
        print(f"[ERREUR] ERREUR après {elapsed:.2f}s: {str(exception_container[0])}")
        traceback.print_exc()
        nomic_ok = False
    else:
        embedding = result_container[0]
        print(f"[OK] Embedding généré en {elapsed:.2f}s")
        print(f"   Dimensions: {len(embedding)}")
        print(f"   Extrait: {embedding[:5]}...")
        nomic_ok = True

    del embedding_model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

except Exception as e:
    print(f"[ERREUR] ERREUR CRITIQUE dans TEST 1: {str(e)}")
    traceback.print_exc()
    nomic_ok = False

print()
print()

# ============================================================================
# TEST 2: ChromaDB seul (lecture sans embedding)
# ============================================================================
print("TEST 2: ChromaDB SEUL (vérification de la base)")
print("-" * 80)

chromadb_ok = False
if os.path.exists(CHROMA_DB_DIR) and os.listdir(CHROMA_DB_DIR):
    print("[INFO] ChromaDB existe.")

    try:
        from chromadb import PersistentClient

        print("[2.1] Connexion à ChromaDB...")
        start = time.time()
        client = PersistentClient(path=CHROMA_DB_DIR)
        elapsed = time.time() - start
        print(f"[OK] Connexion réussie en {elapsed:.2f}s")

        print("[2.2] Vérification des collections...")
        collections = client.list_collections()
        print(f"[OK] {len(collections)} collection(s) trouvée(s):")
        for col in collections:
            count = col.count()
            print(f"   - {col.name}: {count} documents")

        chromadb_ok = True

    except Exception as e:
        print(f"[ERREUR] Erreur avec ChromaDB: {str(e)}")
        traceback.print_exc()
        chromadb_ok = False
else:
    print("[ATTENTION] ChromaDB n'existe pas encore.")
    print("   Il faudra la créer lors du premier chargement de documents.")

print()
print()

# ============================================================================
# TEST 3: ChromaDB + NomicEmbeddings (Retriever complet)
# ============================================================================
print("TEST 3: ChromaDB + NomicEmbeddings (RETRIEVER COMPLET)")
print("-" * 80)

if not nomic_ok:
    print("[ATTENTION] Skippé car NomicEmbeddings a échoué dans TEST 1")
elif not chromadb_ok and not os.path.exists(CHROMA_DB_DIR):
    print("[ATTENTION] Skippé car ChromaDB n'existe pas")
else:
    try:
        import torch
        from langchain_chroma import Chroma
        from langchain_nomic.embeddings import NomicEmbeddings

        device = "cpu"
        if torch.cuda.is_available():
            device = "cuda"

        print(f"[3.1] Création du modèle d'embedding (device: {device})...")
        start = time.time()
        embedding_model = NomicEmbeddings(
            model=Config.NomicEmbeddings_model, inference_mode="local", device=device
        )
        print(f"[OK] Modèle créé en {time.time() - start:.2f}s")

        print("[3.2] Chargement de ChromaDB avec embedding...")
        start = time.time()
        vectorstore = Chroma(persist_directory=CHROMA_DB_DIR, embedding_function=embedding_model)
        print(f"[OK] ChromaDB chargée en {time.time() - start:.2f}s")

        print("[3.3] Création du retriever...")
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        print("[OK] Retriever créé")

        # Test du retriever avec timeout
        print("\n[3.4] Test retriever.invoke() (peut prendre 30s-2min)...")
        print("     Si ça bloque plus de 3 minutes, appuyez sur Ctrl+C")

        result_container = [None]
        exception_container = [None]
        start_invoke = time.time()

        def retrieve_test():
            try:
                query = "What is a Large Language Model?"
                print(f"     Requête test: '{query}'")
                result_container[0] = retriever.invoke(query)
            except Exception as e:
                exception_container[0] = e

        thread = threading.Thread(target=retrieve_test, daemon=True)
        thread.start()
        thread.join(timeout=180)  # 3 minutes max

        elapsed = time.time() - start_invoke

        if thread.is_alive():
            print(f"[ERREUR] TIMEOUT après {elapsed:.2f}s")
            print("    Le retriever bloque lors de l'invocation!")
            print("    → PROBLÈME IDENTIFIÉ: retriever.invoke()")
            print("\n    Hypothèses:")
            print("    1. Le modèle d'embedding bloque (problème GPU)")
            print("    2. ChromaDB bloque lors de la recherche vectorielle")
            print("    3. Interaction entre les deux")
        elif exception_container[0]:
            print(f"[ERREUR] ERREUR après {elapsed:.2f}s: {str(exception_container[0])}")
            traceback.print_exc()
        else:
            docs = result_container[0]
            print(f"[OK] retriever.invoke() réussi en {elapsed:.2f}s")
            print(f"   Documents trouvés: {len(docs)}")
            if docs:
                print(f"   Premier document: {len(docs[0].page_content)} caractères")

        del embedding_model, vectorstore, retriever
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    except Exception as e:
        print(f"[ERREUR] ERREUR CRITIQUE dans TEST 3: {str(e)}")
        traceback.print_exc()

print()
print()
print("=" * 80)
print("RÉSUMÉ DU DIAGNOSTIC")
print("=" * 80)
print()
print("TEST 1 - NomicEmbeddings seul:", "[OK] OK" if nomic_ok else "[ERREUR] ÉCHEC")
print("TEST 2 - ChromaDB seul:", "[OK] OK" if chromadb_ok else "[ATTENTION] N/A ou ÉCHEC")
print()
print("Si NomicEmbeddings bloque seul -> Probleme avec le modele/GPU")
print("Si seul retriever.invoke() bloque -> Probleme d'interaction ChromaDB/Embedding")
print("=" * 80)
