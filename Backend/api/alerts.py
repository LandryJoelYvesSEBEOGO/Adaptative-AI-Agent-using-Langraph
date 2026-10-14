"""Alertes de latence et d'erreurs : journal ERROR (pour votre plateforme de logs) et webhook optionnel.

Les seuils sont évalués après chaque requête RAG ; une même alerte n'est pas renvoyée avant
`ALERT_COOLDOWN_MINUTES`. L'état du délai est local au processus (comme la limitation de débit)."""

import logging
import threading
import time

import httpx

from api.services.metrics_service import evaluate_alerts
from config.settings import get_settings

logger = logging.getLogger("api.alerts")

_last_fired: dict[str, float] = {}
_lock = threading.Lock()


def _post_webhook(url: str, text: str) -> None:
    try:
        httpx.post(url, json={"text": text}, timeout=5).raise_for_status()
    except Exception:
        logger.exception("échec de l'envoi du webhook d'alerte")


def notify_if_needed(now: float | None = None) -> list[dict]:
    """Journalise (et envoie par webhook) les alertes actives hors délai de rappel.
    Retourne les alertes effectivement émises."""
    settings = get_settings()
    now = time.monotonic() if now is None else now
    cooldown = settings.ALERT_COOLDOWN_MINUTES * 60
    fired = []
    for alert in evaluate_alerts():
        with _lock:
            last = _last_fired.get(alert["kind"])
            if last is not None and now - last < cooldown:
                continue
            _last_fired[alert["kind"]] = now
        logger.error(
            "ALERT %s: %s", alert["kind"], alert["message"], extra={"alert": alert["kind"]}
        )
        if settings.ALERT_WEBHOOK_URL:
            # hors du chemin de la requête : un webhook lent ne ralentit pas l'utilisateur
            threading.Thread(
                target=_post_webhook,
                args=(settings.ALERT_WEBHOOK_URL, f"[RAG System] {alert['message']}"),
                daemon=True,
            ).start()
        fired.append(alert)
    return fired


def reset() -> None:
    with _lock:
        _last_fired.clear()
