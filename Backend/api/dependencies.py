from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.services.auth_service import decode_token, get_user_by_id
from config.settings import get_settings

# auto_error=False : l'absence d'en-tête n'est pas une erreur tant qu'un cookie de session existe
security = HTTPBearer(auto_error=False)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _check_csrf(request: Request) -> None:
    """Requêtes à effet de bord authentifiées par cookie : l'origine doit être autorisée.

    SameSite protège déjà contre l'essentiel ; ce contrôle ferme le reste (sous-domaines,
    navigateurs anciens). Les clients qui utilisent l'en-tête Bearer ne sont pas concernés."""
    origin = request.headers.get("origin")
    if origin is None:
        referer = request.headers.get("referer", "")
        origin = "/".join(referer.split("/")[:3]) if referer else None
    if origin not in get_settings().cors_origins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origine non autorisée")


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """
    Dépendance pour récupérer l'utilisateur actuel (en-tête Bearer ou cookie de session).

    Le rôle est relu en base à chaque requête : un compte supprimé ou rétrogradé
    perd immédiatement ses droits, quel que soit le contenu du token.
    """
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide ou expiré"
    )
    if credentials is not None:
        token, from_cookie = credentials.credentials, False
    else:
        token, from_cookie = request.cookies.get("access_token"), True
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Non authentifié")

    payload = decode_token(token, "access")
    user = get_user_by_id(payload["sub"]) if payload and payload.get("sub") else None
    if user is None:
        raise invalid
    if from_cookie and request.method not in SAFE_METHODS:
        _check_csrf(request)
    return user


def require_admin(current_user: dict = Depends(get_current_user)):
    """
    Dépendance pour vérifier que l'utilisateur est admin.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux administrateurs"
        )

    return current_user
