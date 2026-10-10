from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
import time
import logging
import traceback

logger = logging.getLogger(__name__)

def setup_cors(app):
    """Configure CORS pour permettre les requêtes depuis le frontend."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:3000",
            "http://localhost:8081",      # Frontend Vite
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8081",      # Frontend Vite en 127.0.0.1
            "http://localhost:5174",
            "http://127.0.0.1:5174",
        ],
        allow_credentials=True,
        allow_methods=["*"],  # Autorise toutes les méthodes (GET, POST, OPTIONS, etc.)
        allow_headers=["*"],  # Autorise tous les headers
        expose_headers=["*"],
        max_age=3600,  # Cache les prérequêtes CORS pendant 1 heure
    )

async def log_requests(request: Request, call_next):
    """Middleware pour logger les requêtes avec détails améliorés."""
    start_time = time.time()
    origin = request.headers.get("origin", "N/A")
    user_agent = request.headers.get("user-agent", "N/A")[:100]  # Limiter la longueur
    
    # Logger les requêtes OPTIONS (preflight CORS) avec moins de détails
    if request.method == "OPTIONS":
        logger.debug(f"OPTIONS preflight: {request.url.path} from {origin}")
    else:
        logger.info(
            f"Request: {request.method} {request.url.path} | "
            f"Origin: {origin} | "
            f"IP: {request.client.host if request.client else 'N/A'}"
        )
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Logger les réponses avec codes de statut colorés
        if request.method != "OPTIONS":
            status_emoji = "✅" if 200 <= response.status_code < 300 else \
                          "⚠️" if 300 <= response.status_code < 400 else \
                          "❌" if 400 <= response.status_code < 500 else \
                          "🔥" if response.status_code >= 500 else "❓"
            
            logger.info(
                f"{status_emoji} Response: {response.status_code} | "
                f"Path: {request.url.path} | "
                f"Time: {process_time:.3f}s"
            )
        
        return response
    
    except Exception as e:
        process_time = time.time() - start_time
        error_type = type(e).__name__
        error_message = str(e)
        
        logger.error(
            f"🔥 Exception: {error_type} | "
            f"Path: {request.url.path} | "
            f"Method: {request.method} | "
            f"Time: {process_time:.3f}s | "
            f"Error: {error_message}"
        )
        logger.debug(f"Traceback: {traceback.format_exc()}")
        
        # Retourner une réponse d'erreur structurée
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "Erreur serveur interne",
                "type": error_type,
                "path": request.url.path,
            }
        )