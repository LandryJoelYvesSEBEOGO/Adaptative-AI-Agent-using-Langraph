# isort: off
# Patch bcrypt pour passlib - DOIT être importé en premier
from api.services.bcrypt_patch import *  # noqa: F401, F403

# isort: on
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.database import run_migrations
from api.middleware import log_requests, setup_cors
from api.routes import admin, auth, chat, conversation
from api.services.auth_service import seed_initial_users
from config.settings import get_settings

# Configuration du logging avec format amélioré
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if get_settings().AUTO_MIGRATE:
        run_migrations()
    seed_initial_users()
    yield


# Créer l'application FastAPI
app = FastAPI(
    lifespan=lifespan,
    title="RAG System API",
    description="API pour le système RAG avec frontend React",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configurer CORS EN PREMIER - doit être avant tout autre middleware
setup_cors(app)


# Handler global pour les erreurs
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Gestionnaire global d'exceptions pour améliorer l'affichage des erreurs."""
    import traceback

    error_type = type(exc).__name__
    error_message = str(exc)
    path = request.url.path
    method = request.method

    logger.error(
        f"🔥 Exception globale: {error_type} | "
        f"Path: {path} | "
        f"Method: {method} | "
        f"Error: {error_message}"
    )
    logger.debug(f"Traceback complet:\n{traceback.format_exc()}")

    # Si c'est une HTTPException de FastAPI, la laisser passer
    from fastapi import HTTPException

    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.detail,
                "path": path,
            },
        )

    # Pour les autres exceptions, retourner une erreur 500
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Erreur serveur interne",
            "path": path,
        },
    )


# Ajouter le middleware de logging après CORS
app.middleware("http")(log_requests)

# Inclure les routers
app.include_router(auth.router)
app.include_router(chat.router)  # Inclut aussi /feedback
app.include_router(admin.router)
app.include_router(conversation.router)


@app.get("/")
async def root():
    """Endpoint racine."""
    return {"message": "RAG System API", "version": "1.0.0", "docs": "/docs", "redoc": "/redoc"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",  # Écouter uniquement sur localhost
        port=8000,
        reload=True,
    )
