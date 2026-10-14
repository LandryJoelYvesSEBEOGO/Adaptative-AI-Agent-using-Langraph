# isort: off
# Le patch bcrypt DOIT être importé avant passlib.
from api.services.bcrypt_patch import *  # noqa: F401, F403

# isort: on
import os
from datetime import UTC, datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select

from api.database import session_scope
from api.db_models import User
from config.settings import get_settings

# Configuration
SECRET_KEY: str = get_settings().JWT_SECRET_KEY
if len(SECRET_KEY) < 32:
    raise RuntimeError(
        "JWT_SECRET_KEY doit être défini (32 caractères minimum). "
        'Générez-en une avec : python -c "import secrets; print(secrets.token_urlsafe(48))"'
    )
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _to_dict(user: User) -> dict:
    """Représentation publique d'un utilisateur (sans le hash du mot de passe)."""
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe."""
    return pwd_context.verify(plain_password, hashed_password)


def get_user_by_email(email: str) -> Optional[dict]:
    """Récupère un utilisateur par email (hash inclus, usage interne)."""
    with session_scope() as db:
        user = db.scalar(select(User).where(User.email == email.lower()))
        if user is None:
            return None
        return {**_to_dict(user), "hashed_password": user.hashed_password}


def get_user_by_id(user_id: str) -> Optional[dict]:
    """Récupère un utilisateur par identifiant (sans le hash)."""
    with session_scope() as db:
        user = db.get(User, user_id)
        return _to_dict(user) if user else None


def _encode(user_id: str, token_type: str, lifetime: timedelta) -> str:
    claims = {"sub": user_id, "type": token_type, "exp": datetime.now(UTC) + lifetime}
    return jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(user_id: str) -> str:
    """Jeton d'accès à courte durée (cookie `access_token` ou en-tête Bearer)."""
    return _encode(user_id, "access", timedelta(minutes=get_settings().ACCESS_TOKEN_MINUTES))


def create_refresh_token(user_id: str) -> str:
    """Jeton de renouvellement (cookie httpOnly limité à /api/v1/auth)."""
    return _encode(user_id, "refresh", timedelta(days=get_settings().REFRESH_TOKEN_DAYS))


def decode_token(token: str, expected_type: str) -> Optional[dict]:
    """Décode et vérifie un jeton ; None s'il est invalide, expiré ou d'un autre type.

    Accepte aussi les jetons signés avec une ancienne clé (JWT_SECRET_KEY_PREVIOUS) : pendant une
    rotation du secret, les sessions ouvertes restent valables jusqu'à leur expiration."""
    for key in (SECRET_KEY, *get_settings().jwt_previous_keys):
        try:
            payload = jwt.decode(token, key, algorithms=[ALGORITHM])
        except JWTError:
            continue
        return payload if payload.get("type") == expected_type else None
    return None


def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Authentifie un utilisateur."""
    user = get_user_by_email(email)
    if not user or not verify_password(password, user["hashed_password"]):
        return None
    return {k: v for k, v in user.items() if k != "hashed_password"}


def create_user(email: str, password: str, name: str, role: str = "user") -> Optional[dict]:
    """Crée un utilisateur ; retourne None si l'email est déjà pris."""
    email = email.lower()
    with session_scope() as db:
        if db.scalar(select(User).where(User.email == email)):
            return None
        user = User(
            email=email,
            hashed_password=pwd_context.hash(password),
            name=name,
            role=role if role in ("admin", "user") else "user",
        )
        db.add(user)
        db.flush()
        return _to_dict(user)


def seed_initial_users() -> None:
    """Crée les comptes initiaux décrits par l'environnement (ADMIN_*, DEFAULT_USER_*)."""
    for prefix, name, role in (
        ("ADMIN", "Admin User", "admin"),
        ("DEFAULT_USER", "Standard User", "user"),
    ):
        email = os.getenv(f"{prefix}_EMAIL")
        password = os.getenv(f"{prefix}_PASSWORD")
        if email and password and not get_user_by_email(email):
            create_user(email, password, name, role)
