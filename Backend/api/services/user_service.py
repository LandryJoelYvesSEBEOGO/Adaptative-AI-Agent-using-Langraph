from typing import Dict, List, Optional

from sqlalchemy import func, select

from api.database import session_scope
from api.db_models import Conversation, RagRequest, User


def list_users() -> List[Dict]:
    """Utilisateurs avec leur activité (conversations, requêtes RAG, dernière requête)."""
    conversations = (
        select(Conversation.user_id, func.count(Conversation.id).label("n"))
        .group_by(Conversation.user_id)
        .subquery()
    )
    requests = (
        select(
            RagRequest.user_id,
            func.count(RagRequest.id).label("n"),
            func.max(RagRequest.created_at).label("last"),
        )
        .group_by(RagRequest.user_id)
        .subquery()
    )
    with session_scope() as db:
        rows = db.execute(
            select(User, conversations.c.n, requests.c.n, requests.c.last)
            .outerjoin(conversations, conversations.c.user_id == User.id)
            .outerjoin(requests, requests.c.user_id == User.id)
            .order_by(User.created_at.desc())
        ).all()
    return [
        {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "created_at": user.created_at,
            "conversations": conv_count or 0,
            "requests": req_count or 0,
            "last_activity": last,
        }
        for user, conv_count, req_count, last in rows
    ]


def _admin_count(db) -> int:
    return db.scalar(select(func.count(User.id)).where(User.role == "admin")) or 0


def set_role(user_id: str, role: str) -> Optional[str]:
    """Change le rôle. Retourne None si réussi, sinon un code d'erreur
    ('not_found' | 'last_admin')."""
    with session_scope() as db:
        user = db.get(User, user_id)
        if user is None:
            return "not_found"
        if user.role == "admin" and role != "admin" and _admin_count(db) <= 1:
            return "last_admin"
        user.role = role
        return None


def delete_user(user_id: str) -> Optional[str]:
    """Supprime le compte et ses conversations. None si réussi, sinon 'not_found' | 'last_admin'."""
    with session_scope() as db:
        user = db.get(User, user_id)
        if user is None:
            return "not_found"
        if user.role == "admin" and _admin_count(db) <= 1:
            return "last_admin"
        db.delete(user)
        return None
