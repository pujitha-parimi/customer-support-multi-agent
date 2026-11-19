import sqlite3
import json
from typing import Optional
from langgraph.checkpoint.memory import MemorySaver
from memory.state import WorkingMemory

DB_PATH = "support_memory.db"


def init_memory_db(db_path: str = DB_PATH) -> None:
    """Create the SQLite table for structured working memory if it does not exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS working_memory (
            session_id TEXT PRIMARY KEY,
            memory_json TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def default_working_memory() -> WorkingMemory:
    """Return a clean initial working memory structure for a new session."""
    return {
        "customer_id": None,
        "active_order_id": None,
        "active_policy_id": None,
        "last_intent": None,
        "pending_approval": None,
        "is_human_approved": False,
    }


def load_working_memory(session_id: str, db_path: str = DB_PATH) -> WorkingMemory:
    """Fetch persisted structured working memory for a session from SQLite."""
    init_memory_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT memory_json FROM working_memory WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return json.loads(row[0])
    return default_working_memory()


def save_working_memory(session_id: str, memory: WorkingMemory, db_path: str = DB_PATH) -> None:
    """Persist updated structured working memory to SQLite."""
    init_memory_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO working_memory (session_id, memory_json, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(session_id) DO UPDATE SET
            memory_json = excluded.memory_json,
            updated_at = CURRENT_TIMESTAMP
        """,
        (session_id, json.dumps(memory)),
    )
    conn.commit()
    conn.close()


def get_session_checkpointer() -> MemorySaver:
    """Returns LangGraph's session message checkpointer for multi-turn conversation threads."""
    return MemorySaver()