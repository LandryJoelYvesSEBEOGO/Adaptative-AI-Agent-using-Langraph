import os
import sqlite3
from pathlib import Path
from typing import Optional

# Chemin par défaut: Backend/data/rag.db
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = os.getenv("RAG_DB_PATH", str(DATA_DIR / "rag.db"))


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_email TEXT NOT NULL,
            title TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL,
            citations TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_requests (
            id TEXT PRIMARY KEY,
            conversation_id TEXT,
            user_email TEXT,
            question TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('success', 'error')),
            error TEXT,
            latency_end_to_end REAL,
            latency_retrieval REAL,
            latency_generation REAL,
            latency_grading REAL,
            latency_web_search REAL,
            latency_reranking REAL,
            latency_answer_quality REAL,
            docs_count INTEGER,
            response_length INTEGER,
            answer_quality_score REAL,
            answer_quality_scores TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_email)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rag_requests_created_at ON rag_requests(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rag_requests_status ON rag_requests(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rag_requests_user ON rag_requests(user_email)")

    conn.commit()
    conn.close()
