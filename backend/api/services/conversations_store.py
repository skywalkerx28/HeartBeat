"""
Conversation persistence for HeartBeat Engine (Postgres)

Stores user conversations and messages in Cloud SQL Postgres so users can
access history across devices (ChatGPT-style). Falls back to None if
DATABASE_URL is not configured; in that case in-memory storage is used by
the orchestrator service.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def _build_engine() -> Optional[Engine]:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        return None
    # Create a small, robust pool for Cloud Run
    return create_engine(
        dsn,
        pool_pre_ping=True,
        pool_size=int(os.getenv("PG_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("PG_MAX_OVERFLOW", "5")),
    )


@dataclass
class ConversationsStore:
    engine: Engine

    def ensure_schema(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(text(
                """
                CREATE TABLE IF NOT EXISTS hb_conversations (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    conversation_id TEXT NOT NULL,
                    title TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    UNIQUE (user_id, conversation_id)
                );
                CREATE INDEX IF NOT EXISTS idx_hb_conversations_user_updated
                    ON hb_conversations(user_id, updated_at DESC);
                CREATE TABLE IF NOT EXISTS hb_messages (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    text TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_hb_messages_user_conv
                    ON hb_messages(user_id, conversation_id, created_at);
                """
            ))

    # --- CRUD helpers ---
    def start_conversation(self, user_id: str, conversation_id: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO hb_conversations(user_id, conversation_id)
                    VALUES (:u, :c)
                    ON CONFLICT (user_id, conversation_id) DO NOTHING
                    """
                ),
                {"u": user_id, "c": conversation_id},
            )

    def append_message(self, user_id: str, conversation_id: str, role: str, text_value: str) -> None:
        if not text_value:
            return
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO hb_conversations(user_id, conversation_id)
                    VALUES (:u, :c)
                    ON CONFLICT (user_id, conversation_id) DO UPDATE SET updated_at = NOW();
                    """
                ),
                {"u": user_id, "c": conversation_id},
            )
            conn.execute(
                text(
                    """
                    INSERT INTO hb_messages(user_id, conversation_id, role, text)
                    VALUES (:u, :c, :r, :t)
                    """
                ),
                {"u": user_id, "c": conversation_id, "r": role, "t": text_value},
            )

    def get_messages(self, user_id: str, conversation_id: str) -> List[Dict[str, Any]]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT role, text, created_at
                    FROM hb_messages
                    WHERE user_id = :u AND conversation_id = :c
                    ORDER BY created_at ASC, id ASC
                    """
                ),
                {"u": user_id, "c": conversation_id},
            ).mappings().all()
        return [{"role": r["role"], "text": r["text"]} for r in rows]

    def list_conversations(self, user_id: str) -> List[Dict[str, Any]]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT c.conversation_id,
                           COALESCE(c.title, '') AS title,
                           c.updated_at,
                           COALESCE(m.cnt, 0) AS message_count
                    FROM hb_conversations c
                    LEFT JOIN (
                        SELECT user_id, conversation_id, COUNT(*) AS cnt
                        FROM hb_messages
                        GROUP BY user_id, conversation_id
                    ) m
                    ON m.user_id = c.user_id AND m.conversation_id = c.conversation_id
                    WHERE c.user_id = :u
                    ORDER BY c.updated_at DESC, c.id DESC
                    """
                ),
                {"u": user_id},
            ).mappings().all()
        return [
            {
                "conversation_id": r["conversation_id"],
                "title": r["title"],
                "updated_at": (r["updated_at"].isoformat() if r["updated_at"] else None),
                "message_count": int(r["message_count"] or 0),
            }
            for r in rows
        ]

    def get_conversation(self, user_id: str, conversation_id: str) -> Dict[str, Any]:
        msgs = self.get_messages(user_id, conversation_id)
        with self.engine.begin() as conn:
            meta = conn.execute(
                text(
                    """
                    SELECT title, updated_at
                    FROM hb_conversations
                    WHERE user_id = :u AND conversation_id = :c
                    """
                ),
                {"u": user_id, "c": conversation_id},
            ).mappings().first()
        return {
            "conversation_id": conversation_id,
            "updated_at": meta["updated_at"].isoformat() if meta and meta["updated_at"] else None,
            "messages": msgs,
        }

    def rename_conversation(self, user_id: str, conversation_id: str, new_title: str) -> bool:
        with self.engine.begin() as conn:
            res = conn.execute(
                text(
                    """
                    UPDATE hb_conversations
                    SET title = :t, updated_at = NOW()
                    WHERE user_id = :u AND conversation_id = :c
                    """
                ),
                {"u": user_id, "c": conversation_id, "t": new_title},
            )
        return res.rowcount > 0

    def delete_conversation(self, user_id: str, conversation_id: str) -> bool:
        with self.engine.begin() as conn:
            conn.execute(
                text("DELETE FROM hb_messages WHERE user_id = :u AND conversation_id = :c"),
                {"u": user_id, "c": conversation_id},
            )
            res = conn.execute(
                text("DELETE FROM hb_conversations WHERE user_id = :u AND conversation_id = :c"),
                {"u": user_id, "c": conversation_id},
            )
        return res.rowcount > 0


_store_singleton: Optional[ConversationsStore] = None


def get_conversation_store() -> Optional[ConversationsStore]:
    global _store_singleton
    if _store_singleton is not None:
        return _store_singleton
    engine = _build_engine()
    if engine is None:
        _store_singleton = None
        return None
    _store_singleton = ConversationsStore(engine=engine)
    try:
        _store_singleton.ensure_schema()
    except Exception:
        # Do not block service startup if schema creation fails; logs in calling code
        pass
    return _store_singleton


