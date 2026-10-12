from datetime import timedelta

from fastapi import APIRouter

from api.models.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
)
from api.services.auth_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_user,
    create_access_token,
    create_user,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    """
    Authentifie un utilisateur et retourne un token JWT.
    """
    user = authenticate_user(request.email, request.password)

    if not user:
        return LoginResponse(success=False, error="Email ou mot de passe incorrect")

    # Créer le token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user["id"]}, expires_delta=access_token_expires)

    return LoginResponse(
        success=True,
        token=access_token,
        user={"id": user["id"], "email": user["email"], "name": user["name"], "role": user["role"]},
    )


@router.post("/register", response_model=RegisterResponse)
def register(request: RegisterRequest):
    """
    Crée un nouvel utilisateur et retourne un token JWT.
    """
    # Créer l'utilisateur
    user = create_user(
        email=request.email,
        password=request.password,
        name=request.name,
        role="user",  # le rôle n'est jamais choisi par le client
    )

    if not user:
        return RegisterResponse(success=False, error="Un utilisateur avec cet email existe déjà")

    # Créer le token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user["id"]}, expires_delta=access_token_expires)

    return RegisterResponse(
        success=True,
        token=access_token,
        user={"id": user["id"], "email": user["email"], "name": user["name"], "role": user["role"]},
    )


@router.post("/logout")
async def logout():
    """
    Déconnecte un utilisateur (pour l'instant, juste une confirmation).
    En production, vous pourriez ajouter le token à une blacklist.
    """
    return {"success": True, "message": "Déconnecté avec succès"}
