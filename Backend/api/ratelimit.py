"""Limitation de débit (fenêtre glissante, en mémoire) et quotas quotidiens.

La fenêtre glissante est locale au processus : avec plusieurs instances de l'API, chacune applique
sa propre limite (la limite effective est donc multipliée par le nombre d'instances). Pour un
plafond global strict, remplacer `SlidingWindowLimiter` par un compteur partagé (Redis). Le quota
quotidien, lui, est compté en base et s'applique globalement.
"""

import math
import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import HTTPException, Request, status

from config.settings import get_settings

MAX_TRACKED_KEYS = 50_000


class SlidingWindowLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window: float) -> int | None:
        """Enregistre une requête. Retourne None si elle passe, sinon les secondes à attendre."""
        now = self._clock()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - window:
                hits.popleft()
            if len(hits) >= limit:
                return max(1, math.ceil(hits[0] + window - now))
            hits.append(now)
            if len(self._hits) > MAX_TRACKED_KEYS:
                self._purge(now, window)
            return None

    def _purge(self, now: float, window: float) -> None:
        for key in [k for k, v in self._hits.items() if not v or v[-1] <= now - window]:
            del self._hits[key]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = SlidingWindowLimiter()


def client_ip(request: Request) -> str:
    """Adresse du client ; derrière un proxy de confiance, la dernière entrée de X-Forwarded-For
    (celle ajoutée par ce proxy : les entrées précédentes sont contrôlables par le client)."""
    if get_settings().TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def enforce(key: str, limit: int, window: float = 60.0) -> None:
    """Lève 429 (avec Retry-After) si `key` dépasse `limit` requêtes sur `window` secondes."""
    settings = get_settings()
    if not settings.RATE_LIMIT_ENABLED or limit <= 0:
        return
    retry_after = limiter.hit(key, limit, window)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de requêtes. Réessayez dans un instant.",
            headers={"Retry-After": str(retry_after)},
        )


def enforce_daily_quota(user: dict, used_today: Callable[[str], int]) -> None:
    """Lève 429 si l'utilisateur a épuisé son quota quotidien (les administrateurs en sont exemptés)."""
    quota = get_settings().DAILY_QUESTION_QUOTA
    if not get_settings().RATE_LIMIT_ENABLED or quota <= 0 or user.get("role") == "admin":
        return
    if used_today(user["id"]) >= quota:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Quota quotidien atteint ({quota} questions). Il se renouvelle à minuit (UTC).",
            headers={"Retry-After": str(seconds_until_midnight_utc())},
        )


def seconds_until_midnight_utc() -> int:
    now = time.time()
    return int(86400 - now % 86400)
