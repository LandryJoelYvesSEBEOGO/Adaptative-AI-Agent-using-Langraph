import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict

from api.db import get_connection

ISO = "%Y-%m-%dT%H:%M:%S.%fZ"


def _now() -> str:
    return datetime.utcnow().strftime(ISO)


def create_conversation(user_email: str, title: Optional[str] = None) -> Dict:
    conv_id = str(uuid.uuid4())
    now = _now()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO conversations (id, user_email, title, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (conv_id, user_email, title, now, now),
    )
    conn.commit()
    conn.close()

    return {
        "id": conv_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
    }


def list_conversations(user_email: str) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, title, created_at, updated_at
        FROM conversations
        WHERE user_email = ?
        ORDER BY updated_at DESC
        """,
        (user_email,),
    )
    rows = cur.fetchall()
    conn.close()

    return [dict(r) for r in rows]


def get_conversation(conversation_id: str, user_email: str) -> Optional[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, title, created_at, updated_at
        FROM conversations
        WHERE id = ? AND user_email = ?
        """,
        (conversation_id, user_email),
    )
    row = cur.fetchone()
    conn.close()

    return dict(row) if row else None


def add_message(
    conversation_id: str,
    role: str,
    content: str,
    citations: Optional[List[Dict]] = None,
) -> Dict:
    msg_id = str(uuid.uuid4())
    now = _now()

    citations_json = json.dumps(citations) if citations is not None else None

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO messages (id, conversation_id, role, content, citations, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (msg_id, conversation_id, role, content, citations_json, now),
    )

    cur.execute(
        """
        UPDATE conversations
        SET updated_at = ?
        WHERE id = ?
        """,
        (now, conversation_id),
    )

    conn.commit()
    conn.close()

    return {
        "id": msg_id,
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "citations": citations or None,
        "created_at": now,
    }


def list_messages(conversation_id: str) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, conversation_id, role, content, citations, created_at
        FROM messages
        WHERE conversation_id = ?
        ORDER BY created_at ASC
        """,
        (conversation_id,),
    )
    rows = cur.fetchall()
    conn.close()

    messages = []
    for r in rows:
        citations = json.loads(r["citations"]) if r["citations"] else None
        messages.append(
            {
                "id": r["id"],
                "conversation_id": r["conversation_id"],
                "role": r["role"],
                "content": r["content"],
                "citations": citations,
                "created_at": r["created_at"],
            }
        )
    return messages
