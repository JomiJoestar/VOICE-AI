"""Persistencia del historial visible (SQLite, vía stdlib en executor)."""
from __future__ import annotations

import asyncio
import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger("voice_ai.db")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = ROOT_DIR / "data" / "voice_ai.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id          TEXT PRIMARY KEY,
    speaker     TEXT NOT NULL,
    kind        TEXT NOT NULL,
    text        TEXT NOT NULL,
    timestamp   REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages(timestamp);
"""


class Storage:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_sync(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    async def init(self) -> None:
        await asyncio.get_running_loop().run_in_executor(None, self.init_sync)

    # --- escritura -----------------------------------------------------------
    def _save_sync(self, msg: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO messages (id, speaker, kind, text, timestamp)"
                " VALUES (?, ?, ?, ?, ?)",
                (msg["id"], msg["speaker"], msg["kind"], msg["text"], msg["timestamp"]),
            )

    async def persist_event(self, event: dict[str, Any]) -> None:
        """Callback del EventBus: guarda solo los mensajes del historial."""
        if event.get("type") != "agent_message":
            return
        await asyncio.get_running_loop().run_in_executor(
            None, self._save_sync, event
        )

    # --- lectura -------------------------------------------------------------
    def _recent_sync(self, limit: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, speaker, kind, text, timestamp FROM messages"
                " ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    async def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._recent_sync, limit
        )
