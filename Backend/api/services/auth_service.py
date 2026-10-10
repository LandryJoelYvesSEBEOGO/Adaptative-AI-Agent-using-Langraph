# Patch pour bcrypt avant l'import de passlib
from api.services.bcrypt_patch import *  # noqa: F401, F403

from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional
import os

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise RuntimeError(
        "JWT_SECRET_KEY doit être défini (32 caractères minimum). "
        "Générez-en une avec : python -c \"import secrets; print(secrets.token_urlsafe(48))\""
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 heures

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Base de données utilisateurs (à remplacer par une vraie DB)
MOCK_USERS = [
    {
        "id": "1",
        "email": "admin@rag-system.io",
        "hashed_password": pwd_context.hash("admin"),
        "name": "Admin User",
        "role": "admin"
    },
    {
        "id": "2",
        "email": "user@rag-system.io",
        "hashed_password": pwd_context.hash("user"),
        "name": "Standard User",
        "role": "user"
    }
]

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe."""
    return pwd_context.verify(plain_password, hashed_password)

def get_user_by_email(email: str) -> Optional[dict]:
    """Récupère un utilisateur par email."""
    for user in MOCK_USERS:
        if user["email"].lower() == email.lower():
            return user
    return None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crée un token JWT."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Authentifie un utilisateur."""
    user = get_user_by_email(email)
    if not user:
        return None
    
    if not verify_password(password, user["hashed_password"]):
        return None
    
    # Retourner l'utilisateur sans le hash
    user_without_password = {k: v for k, v in user.items() if k != "hashed_password"}
    return user_without_password

def verify_token(token: str) -> Optional[dict]:
    """Vérifie et décode un token JWT."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def create_user(email: str, password: str, name: str, role: str = "user") -> Optional[dict]:
    """Crée un nouvel utilisateur."""
    # Vérifier si l'utilisateur existe déjà
    if get_user_by_email(email):
        return None
    
    # Générer un nouvel ID
    new_id = str(len(MOCK_USERS) + 1)
    
    # Hasher le mot de passe
    hashed_password = pwd_context.hash(password)
    
    # Créer le nouvel utilisateur
    new_user = {
        "id": new_id,
        "email": email.lower(),
        "hashed_password": hashed_password,
        "name": name,
        "role": role if role in ["admin", "user"] else "user"
    }
    
    # Ajouter à la liste (dans une vraie app, on sauvegarderait en DB)
    MOCK_USERS.append(new_user)
    
    # Retourner l'utilisateur sans le hash
    user_without_password = {k: v for k, v in new_user.items() if k != "hashed_password"}
    return user_without_password