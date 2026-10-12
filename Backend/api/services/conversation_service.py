from datetime import UTC, datetime
from typing import Dict, List, Optional

from sqlalchemy import select

from api.database import session_scope
from api.db_models import Conversation, Feedback, Message


def _conv_dict(conv: Conversation) -> Dict:
    return {
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
    }


def _msg_dict(msg: Message) -> Dict:
    return {
        "id": msg.id,
        "conversation_id": msg.conversation_id,
        "role": msg.role,
        "content": msg.content,
        "citations": msg.citations or None,
        "stopped": bool(msg.stopped),
        "created_at": msg.created_at,
    }


def create_conversation(user_id: str, title: Optional[str] = None) -> Dict:
    with session_scope() as db:
        conv = Conversation(user_id=user_id, title=title)
        db.add(conv)
        db.flush()
        return _conv_dict(conv)


def list_conversations(user_id: str) -> List[Dict]:
    with session_scope() as db:
        rows = db.scalars(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        return [_conv_dict(c) for c in rows]


def get_conversation(conversation_id: str, user_id: str) -> Optional[Dict]:
    """Retourne la conversation si elle appartient à l'utilisateur, sinon None."""
    with session_scope() as db:
        conv = db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id, Conversation.user_id == user_id
            )
        )
        return _conv_dict(conv) if conv else None


def add_message(
    conversation_id: str,
    role: str,
    content: str,
    citations: Optional[List[Dict]] = None,
    stopped: bool = False,
) -> Dict:
    with session_scope() as db:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            citations=citations if citations is not None else None,
            stopped=stopped,
        )
        db.add(msg)
        conv = db.get(Conversation, conversation_id)
        if conv:
            conv.updated_at = datetime.now(UTC)
        db.flush()
        return _msg_dict(msg)


def list_messages(conversation_id: str, user_id: Optional[str] = None) -> List[Dict]:
    """Messages d'une conversation ; avec `user_id`, joint l'avis donné par cet utilisateur."""
    with session_scope() as db:
        stmt = select(Message, Feedback.feedback_type).outerjoin(
            Feedback,
            (Feedback.message_id == Message.id) & (Feedback.user_id == user_id),
        )
        rows = db.execute(
            stmt.where(Message.conversation_id == conversation_id).order_by(
                Message.created_at.asc()
            )
        )
        return [{**_msg_dict(m), "feedback": feedback} for m, feedback in rows]


def add_feedback(
    message_id: str,
    user_id: str,
    feedback_type: str,
    comment: Optional[str] = None,
) -> bool:
    """Enregistre (ou remplace) le feedback d'un utilisateur sur un message de SA conversation.

    Retourne False si le message n'existe pas ou n'appartient pas à l'utilisateur.
    """
    with session_scope() as db:
        owned = db.scalar(
            select(Message.id)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(Message.id == message_id, Conversation.user_id == user_id)
        )
        if not owned:
            return False

        feedback = db.scalar(
            select(Feedback).where(Feedback.message_id == message_id, Feedback.user_id == user_id)
        )
        if feedback:
            feedback.feedback_type = feedback_type
            feedback.comment = comment
            feedback.created_at = datetime.now(UTC)
        else:
            db.add(
                Feedback(
                    message_id=message_id,
                    user_id=user_id,
                    feedback_type=feedback_type,
                    comment=comment,
                )
            )
        return True


def prepare_regeneration(conversation_id: str) -> Optional[str]:
    """Retire la dernière réponse de l'assistant et retourne la question à reposer.

    Retourne None s'il n'y a pas de question utilisateur à régénérer."""
    with session_scope() as db:
        messages = list(
            db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.desc())
                .limit(2)
            )
        )
        if messages and messages[0].role == "assistant":
            db.delete(messages[0])  # le feedback associé part en cascade
            messages = messages[1:]
        if not messages or messages[0].role != "user":
            return None
        return messages[0].content
