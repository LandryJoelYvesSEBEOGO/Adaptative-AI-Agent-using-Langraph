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
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 heures

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


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crée un token JWT."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Authentifie un utilisateur."""
    user = get_user_by_email(email)
    if not user or not verify_password(password, user["hashed_password"]):
        return None
    return {k: v for k, v in user.items() if k != "hashed_password"}


def verify_token(token: str) -> Optional[dict]:
    """Vérifie et décode un token JWT."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


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
