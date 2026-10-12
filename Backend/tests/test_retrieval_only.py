"""
Test isolé du retrieval pour diagnostiquer le blocage GPU.
"""

import os
import sys
import time
import traceback

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("TEST ISOLÉ DU RETRIEVAL - Diagnostic GPU")
print("=" * 70)
print()

try:
    from src.rag.Data_processing import get_retriever

    print("[1] Creation du retriever...")
    start = time.time()
    retriever = get_retriever()
    elapsed = time.time() - start
    print(f"[OK] Retriever cree en {elapsed:.2f}s")
    print()

    print("[2] Test de recherche avec une question...")
    query = "What is a Large Language Model?"
    print(f"Question: {query}")
    print()

    # Test direct sans threading pour voir où ça bloque exactement
    print("[2a] Appel DIRECT retriever.invoke() (sans timeout)...")
    print("     Cela va nous dire EXACTEMENT ou ca bloque.")
    print("     Appuyez sur Ctrl+C si ca prend plus de 2 minutes.")
    print()

    try:
        start_invoke = time.time()
        print(f"[TIMESTAMP] Debut: {time.strftime('%H:%M:%S')}")

        # Appel direct pour voir où ça bloque
        documents = retriever.invoke(query)

        elapsed_invoke = time.time() - start_invoke
        print(f"[TIMESTAMP] Fin: {time.strftime('%H:%M:%S')}")
        print(f"[OK] retriever.invoke() termine en {elapsed_invoke:.2f}s")

        if documents:
            print(f"[OK] {len(documents)} documents trouves")
            for i, doc in enumerate(documents[:2], 1):
                print(f"  Doc {i}: {len(doc.page_content)} caracteres")
        else:
            print("[WARN] Aucun document trouve")

    except KeyboardInterrupt:
        elapsed_invoke = time.time() - start_invoke
        print()
        print(f"[INTERROMPU] Apres {elapsed_invoke:.2f} secondes")
        print("[INFO] L'utilisateur a interrompu - le code etait bloque")
    except Exception as e:
        elapsed_invoke = time.time() - start_invoke
        print(f"[ERREUR] Apres {elapsed_invoke:.2f}s: {str(e)}")
        traceback.print_exc()

    print()
    print("[3] Test avec timeout (comme dans le code)...")

    import threading

    result_container = [None]
    exception_container = [None]

    def retrieval_test():
        try:
            result_container[0] = retriever.invoke(query)
        except Exception as e:
            exception_container[0] = e

    thread = threading.Thread(target=retrieval_test, daemon=True)
    thread.start()
    thread.join(timeout=30)

    if thread.is_alive():
        print("[TIMEOUT] Le retriever.invoke() bloque dans un thread!")
        print("         Cela confirme le probleme de blocage.")
    elif exception_container[0]:
        print(f"[ERREUR] {str(exception_container[0])}")
    elif result_container[0]:
        print(f"[OK] Fonctionne dans thread: {len(result_container[0])} documents")
    else:
        print("[ERREUR] Aucun resultat")

except Exception as e:
    print(f"[ERREUR FATALE] {str(e)}")
    traceback.print_exc()

print()
print("=" * 70)
print("FIN DU TEST")
print("=" * 70)
