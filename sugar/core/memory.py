"""Conversation memory — SQLite-backed message storage and retrieval."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """A single message in a conversation."""

    id: str
    conversation_id: str
    role: str  # "user", "assistant", "system", "tool"
    content: str
    timestamp: datetime

    def to_dict(self) -> dict[str, str]:
        """Convert to the format expected by the LLM."""
        return {"role": self.role, "content": self.content}


class Memory:
    """SQLite-backed conversation memory.

    Stores messages with timestamps for context retrieval.
    Each conversation gets a unique ID, and messages are ordered chronologically.
    """

    def __init__(self, db_path: Path | str = "brain_memory.db") -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                );

                CREATE INDEX IF NOT EXISTS idx_messages_conv
                    ON messages(conversation_id, timestamp);
            """)

    def _connect(self) -> sqlite3.Connection:
        """Create a database connection."""
        return sqlite3.connect(str(self.db_path))

    def new_conversation(self, title: str = "") -> str:
        """Create a new conversation and return its ID."""
        conv_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (conv_id, title, now, now),
            )
        logger.debug("Created conversation: %s", conv_id)
        return conv_id

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> Message:
        """Add a message to a conversation."""
        msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            timestamp=datetime.now(timezone.utc),
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO messages (id, conversation_id, role, content, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (msg.id, msg.conversation_id, msg.role, msg.content, msg.timestamp.isoformat()),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (msg.timestamp.isoformat(), conversation_id),
            )
        return msg

    def get_messages(
        self,
        conversation_id: str,
        limit: int = 50,
    ) -> list[Message]:
        """Get recent messages from a conversation."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT id, conversation_id, role, content, timestamp "
                "FROM messages WHERE conversation_id = ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (conversation_id, limit),
            )
            rows = cursor.fetchall()

        messages = [
            Message(
                id=row[0],
                conversation_id=row[1],
                role=row[2],
                content=row[3],
                timestamp=datetime.fromisoformat(row[4]),
            )
            for row in reversed(rows)  # Chronological order
        ]
        return messages

    def get_context_messages(
        self,
        conversation_id: str,
        limit: int = 20,
    ) -> list[dict[str, str]]:
        """Get recent messages formatted for the LLM context window."""
        messages = self.get_messages(conversation_id, limit=limit)
        return [msg.to_dict() for msg in messages]

    def list_conversations(self, limit: int = 20) -> list[dict]:
        """List recent conversations."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT id, title, created_at, updated_at "
                "FROM conversations ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "title": row[1],
                "created_at": row[2],
                "updated_at": row[3],
            }
            for row in rows
        ]

    def search_messages(self, query: str, limit: int = 10) -> list[Message]:
        """Search all messages for a query string."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT id, conversation_id, role, content, timestamp "
                "FROM messages WHERE content LIKE ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (f"%{query}%", limit),
            )
            rows = cursor.fetchall()

        return [
            Message(
                id=row[0],
                conversation_id=row[1],
                role=row[2],
                content=row[3],
                timestamp=datetime.fromisoformat(row[4]),
            )
            for row in rows
        ]
