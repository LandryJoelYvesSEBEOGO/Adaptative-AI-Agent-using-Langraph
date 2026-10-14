"""Journalisation structurée (JSON), identifiant de requête et journal d'accès."""

import contextvars
import json
import logging
import sys
import time
import uuid
from datetime import UTC, datetime

from fastapi import Request, status
from fastapi.responses import JSONResponse

from config.settings import Settings, get_settings

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

# Attributs standard d'un LogRecord : tout le reste vient de `extra=` et est publié tel quel
_STANDARD = set(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {"message", "asctime"}


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """Une ligne JSON par événement : exploitable tel quel par Loki, Datadog, CloudWatch…"""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        for key, value in vars(record).items():
            if key not in _STANDARD and key != "request_id":
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def use_json_logs(settings: Settings) -> bool:
    return settings.LOG_FORMAT == "json" or (
        settings.LOG_FORMAT == "auto" and settings.ENVIRONMENT == "prod"
    )


def configure_logging(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        JsonFormatter()
        if use_json_logs(settings)
        else logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(request_id)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.LOG_LEVEL.upper())
    logging.getLogger("uvicorn.access").setLevel(
        logging.WARNING
    )  # remplacé par notre journal d'accès


access_logger = logging.getLogger("api.access")


async def log_requests(request: Request, call_next):
    """Identifiant de requête (en-tête X-Request-ID réutilisé s'il est sain) et journal d'accès."""
    incoming = request.headers.get("x-request-id", "")
    request_id = (
        incoming if 0 < len(incoming) <= 64 and incoming.isprintable() else uuid.uuid4().hex
    )
    token = request_id_var.set(request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        access_logger.exception(
            "unhandled exception",
            extra={"method": request.method, "path": request.url.path, "status": 500},
        )
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": "Erreur serveur interne", "path": request.url.path},
        )
    else:
        if request.method != "OPTIONS":
            level = logging.ERROR if response.status_code >= 500 else logging.INFO
            access_logger.log(
                level,
                "%s %s -> %s",
                request.method,
                request.url.path,
                response.status_code,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
    finally:
        request_id_var.reset(token)
    response.headers["X-Request-ID"] = request_id
    return response
