#!/usr/bin/env python
"""
Script pour démarrer l'API FastAPI.
Usage: python run_api.py
"""

import sys
from pathlib import Path

# Ajouter le chemin du projet au PYTHONPATH
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Vérification rapide des dépendances
try:
    import email_validator  # noqa: F401
    import uvicorn
except ImportError as e:
    print("❌ ERREUR: Dépendances manquantes!")
    print(f"   Module manquant: {e.name}")
    print(f"   Python actuel: {sys.executable}")
    print("\n   Solution: uv sync")
    print("   (ou activez l environnement virtuel : .venv)")
    sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Démarrage du serveur RAG System API...")
    print("=" * 60)
    print(f"📁 Répertoire: {project_root}")
    print()
    print("🌐 URLs disponibles:")
    print("   • API:         http://localhost:8000  ou  http://127.0.0.1:8000")
    print("   • Health:      http://localhost:8000/health")
    print("   • Documentation: http://localhost:8000/docs")
    print("   • ReDoc:       http://localhost:8000/redoc")
    print()
    print("💡 Appuyez sur CTRL+C pour arrêter")
    print("=" * 60)
    print()

    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[str(project_root / "api")],
        log_level="info",
    )
