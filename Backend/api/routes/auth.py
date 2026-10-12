from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response

from api.dependencies import get_current_user
from api.models.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
)
from api.services.auth_service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    create_user,
    decode_token,
    get_user_by_id,
)
from config.settings import get_settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
REFRESH_PATH = "/api/v1/auth"  # le refresh token ne part que vers les routes d'authentification


def _public(user: dict) -> dict:
    return {"id": user["id"], "email": user["email"], "name": user["name"], "role": user["role"]}


def set_session_cookies(response: Response, user_id: str) -> str:
    """Pose les cookies httpOnly de session ; retourne le jeton d'accès."""
    settings = get_settings()
    common = {
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
    }
    access = create_access_token(user_id)
    response.set_cookie(
        ACCESS_COOKIE, access, max_age=settings.ACCESS_TOKEN_MINUTES * 60, path="/", **common
    )
    response.set_cookie(
        REFRESH_COOKIE,
        create_refresh_token(user_id),
        max_age=settings.REFRESH_TOKEN_DAYS * 86400,
        path=REFRESH_PATH,
        **common,
    )
    return access


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH)


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, response: Response):
    """Authentifie l'utilisateur : pose les cookies de session httpOnly.

    Le jeton d'accès est aussi renvoyé dans `token` pour les clients non navigateur
    (scripts, évaluation) qui l'envoient en en-tête `Authorization: Bearer`.
    """
    user = authenticate_user(request.email, request.password)
    if not user:
        return LoginResponse(success=False, error="Email ou mot de passe incorrect")
    return LoginResponse(
        success=True, token=set_session_cookies(response, user["id"]), user=_public(user)
    )


@router.post("/register", response_model=RegisterResponse)
def register(request: RegisterRequest, response: Response):
    """Crée un compte (rôle `user`) et ouvre la session."""
    user = create_user(
        email=request.email,
        password=request.password,
        name=request.name,
        role="user",  # le rôle n'est jamais choisi par le client
    )
    if not user:
        return RegisterResponse(success=False, error="Un utilisateur avec cet email existe déjà")
    return RegisterResponse(
        success=True, token=set_session_cookies(response, user["id"]), user=_public(user)
    )


@router.post("/refresh", response_model=LoginResponse)
def refresh(response: Response, refresh_token: str | None = Cookie(default=None)):
    """Renouvelle la session à partir du cookie de refresh (rotation du refresh token)."""
    payload = decode_token(refresh_token, "refresh") if refresh_token else None
    user = get_user_by_id(payload["sub"]) if payload else None
    if user is None:
        clear_session_cookies(response)
        raise HTTPException(status_code=401, detail="Session expirée")
    return LoginResponse(
        success=True, token=set_session_cookies(response, user["id"]), user=_public(user)
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)):
    """Utilisateur de la session courante (sert à restaurer la session au chargement)."""
    return _public(current_user)


@router.post("/logout")
def logout(request: Request, response: Response):
    """Termine la session : supprime les cookies."""
    clear_session_cookies(response)
    return {"success": True, "message": "Déconnecté avec succès"}
