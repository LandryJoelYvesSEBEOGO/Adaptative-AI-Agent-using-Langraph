from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from api.services.auth_service import ALGORITHM, SECRET_KEY, get_user_by_id

security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Dépendance pour récupérer l'utilisateur actuel depuis le token JWT.

    Le rôle est relu en base à chaque requête : un compte supprimé ou rétrogradé
    perd immédiatement ses droits, quel que soit le contenu du token.
    """
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide ou expiré"
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise invalid from None

    user_id = payload.get("sub")
    user = get_user_by_id(user_id) if user_id else None
    if user is None:
        raise invalid
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
