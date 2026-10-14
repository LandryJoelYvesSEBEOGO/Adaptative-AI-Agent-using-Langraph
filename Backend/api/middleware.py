from fastapi.middleware.cors import CORSMiddleware

from config.settings import get_settings


def setup_cors(app):
    """Configure CORS pour permettre les requêtes depuis le frontend."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_credentials=True,
        allow_methods=["*"],  # Autorise toutes les méthodes (GET, POST, OPTIONS, etc.)
        allow_headers=["*"],  # Autorise tous les headers
        expose_headers=["*"],
        max_age=3600,  # Cache les prérequêtes CORS pendant 1 heure
    )
