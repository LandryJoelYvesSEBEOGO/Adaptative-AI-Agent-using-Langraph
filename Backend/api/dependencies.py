from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from api.services.auth_service import ALGORITHM, SECRET_KEY

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Dépendance pour récupérer l'utilisateur actuel depuis le token JWT.
    """
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        role: str | None = payload.get("role")

        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide")

        return {"email": email, "role": role}

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide ou expiré"
        ) from None


async def require_admin(current_user: dict = Depends(get_current_user)):
    """
    Dépendance pour vérifier que l'utilisateur est admin.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux administrateurs"
        )

    return current_user
