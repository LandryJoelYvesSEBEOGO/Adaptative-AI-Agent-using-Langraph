# Patch bcrypt pour passlib - DOIT être importé en premier
from api.services.bcrypt_patch import *  # noqa: F401, F403
from api.db import init_db
from api.routes import conversation
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging

# Import des routers
from api.routes import auth, chat, admin
from api.middleware import setup_cors, log_requests

# Configuration du logging avec format amélioré
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# Créer l'application FastAPI
app = FastAPI(
    title="RAG System API",
    description="API pour le système RAG avec frontend React",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurer CORS EN PREMIER - doit être avant tout autre middleware
setup_cors(app)

# Initialiser la base
init_db()

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
            }
        )
    
    # Pour les autres exceptions, retourner une erreur 500
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Erreur serveur interne",
            "path": path,
        }
    )

# Ajouter le middleware de logging après CORS
app.middleware("http")(log_requests)

# Handler explicite pour les requêtes OPTIONS (preflight CORS)
@app.options("/{full_path:path}")
async def options_handler(request: Request, full_path: str):
    """
    Handler pour les requêtes OPTIONS (preflight CORS).
    Le middleware CORS devrait normalement gérer cela, mais ce handler
    garantit que les requêtes OPTIONS sont toujours acceptées avec les bons headers.
    """
    from fastapi.responses import Response
    
    # Récupérer l'origin de la requête pour le retourner (si autorisé)
    origin = request.headers.get("origin", "*")
    allowed_origins = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]
    
    # Si l'origin est autorisé, le retourner, sinon utiliser *
    allow_origin = origin if origin in allowed_origins else "*"
    
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": allow_origin,
            "Access-Control-Allow-Methods": "*",  # Autorise toutes les méthodes
            "Access-Control-Allow-Headers": "*",  # Autorise tous les headers
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "3600",
        }
    )

# Inclure les routers
app.include_router(auth.router)
app.include_router(chat.router)  # Inclut aussi /feedback
app.include_router(admin.router)
app.include_router(conversation.router)
@app.get("/")
async def root():
    """Endpoint racine."""
    return {
        "message": "RAG System API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

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
        reload=True
    )