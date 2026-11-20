"""SQLite persistence. One file, WAL mode, small typed helpers.

Only *redacted* text is ever stored: raw uploads are parsed in memory, PII is
replaced with typed placeholders, and the original bytes are discarded.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from typing import Any, Iterator

from .config import settings
from .context import pid

_LOCK = threading.RLock()
_CONN: sqlite3.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS persons (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    display_name TEXT,
    role TEXT,
    reports_to TEXT,
    email TEXT UNIQUE,
    pw_hash TEXT,
    meta JSON NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    person_id TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL DEFAULT 'ceo',
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    added_at REAL NOT NULL,
    consent INTEGER NOT NULL DEFAULT 1,
    n_items INTEGER NOT NULL DEFAULT 0,
    pii JSON NOT NULL DEFAULT '{}',
    meta JSON NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    channel TEXT NOT NULL,
    author TEXT,
    is_owner INTEGER NOT NULL DEFAULT 0,
    audience TEXT,
    counterpart TEXT,
    subject TEXT,
    ts TEXT,
    text TEXT NOT NULL,
    reply_to TEXT,
    meta JSON NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_items_source ON items(source_id);
CREATE INDEX IF NOT EXISTS idx_sources_person ON sources(person_id);
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    source_id TEXT NOT NULL,
    text TEXT NOT NULL,
    embedding BLOB
);
CREATE INDEX IF NOT EXISTS idx_chunks_item ON chunks(item_id);
CREATE TABLE IF NOT EXISTS profile_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id TEXT NOT NULL DEFAULT 'ceo',
    created_at REAL NOT NULL,
    method TEXT NOT NULL,
    note TEXT,
    profile JSON NOT NULL
);
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id TEXT NOT NULL DEFAULT 'ceo',
    created_at REAL NOT NULL,
    kind TEXT NOT NULL,
    request JSON NOT NULL,
    response JSON NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    final_text TEXT,
    decided_at REAL
);
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id TEXT NOT NULL DEFAULT 'ceo',
    ts REAL NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    detail JSON NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value JSON NOT NULL
);
CREATE TABLE IF NOT EXISTS eval_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id TEXT NOT NULL DEFAULT 'ceo',
    ts REAL NOT NULL,
    provider TEXT NOT NULL,
    results JSON NOT NULL
);
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    target TEXT NOT NULL,
    title TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id, target);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    text TEXT NOT NULL,
    payload JSON NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id);
CREATE TABLE IF NOT EXISTS voice_turns (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    target TEXT NOT NULL,
    conversation_id INTEGER,
    message_id INTEGER,
    transcript TEXT NOT NULL DEFAULT '',
    answer TEXT NOT NULL DEFAULT '',
    state TEXT NOT NULL,
    audio BLOB,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_voice_user ON voice_turns(user_id);
CREATE TABLE IF NOT EXISTS self_test_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    question TEXT NOT NULL,
    question_source TEXT NOT NULL,
    user_answer TEXT NOT NULL DEFAULT '',
    twin_answer TEXT NOT NULL DEFAULT '',
    feedback TEXT,
    correction TEXT,
    trait_id TEXT,
    created_at REAL NOT NULL,
    undone_at REAL
);
CREATE TABLE IF NOT EXISTS persona_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    user_id TEXT NOT NULL,
    target TEXT NOT NULL,
    message_id INTEGER,
    rating TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS simli_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    day TEXT NOT NULL,
    user_id TEXT NOT NULL,
    person TEXT NOT NULL,
    seconds INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS blind_votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id TEXT NOT NULL DEFAULT 'ceo',
    ts REAL NOT NULL,
    case_id TEXT NOT NULL,
    correct INTEGER NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    global _CONN
    with _LOCK:
        if _CONN is None:
            settings.data_dir.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(settings.db_path, check_same_thread=False, isolation_level=None)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.executescript(SCHEMA)
            _CONN = conn
        return _CONN


@contextmanager
def tx() -> Iterator[sqlite3.Connection]:
    conn = connect()
    with _LOCK:
        conn.execute("BEGIN")
        try:
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


def query(sql: str, params: tuple | list = ()) -> list[dict[str, Any]]:
    conn = connect()
    with _LOCK:
        rows = conn.execute(sql, params).fetchall()
    return [_row(r) for r in rows]


def one(sql: str, params: tuple | list = ()) -> dict[str, Any] | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple | list = ()) -> int:
    conn = connect()
    with _LOCK:
        cur = conn.execute(sql, params)
        return cur.lastrowid or 0


_JSON_COLS = {"pii", "meta", "profile", "request", "response", "detail", "value", "results", "payload"}


def _row(r: sqlite3.Row) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in r.keys():
        v = r[k]
        if k in _JSON_COLS and isinstance(v, str):
            try:
                v = json.loads(v)
            except json.JSONDecodeError:
                pass
        out[k] = v
    return out


def get_setting(key: str, default: Any = None) -> Any:
    row = one("SELECT value FROM settings WHERE key=?", (key,))
    return row["value"] if row else default


def set_setting(key: str, value: Any) -> None:
    execute(
        "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, json.dumps(value, ensure_ascii=False)),
    )


def audit(actor: str, action: str, **detail: Any) -> None:
    execute(
        "INSERT INTO audit(ts, person_id, actor, action, detail) VALUES(?, ?, ?, ?, ?)",
        (time.time(), pid(), actor, action, json.dumps(detail, ensure_ascii=False, default=str)),
    )


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def reset_all() -> None:
    conn = connect()
    with _LOCK:
        for table in ("chunks", "items", "sources", "profile_versions", "drafts", "eval_runs", "blind_votes", "audit",
                      "messages", "conversations", "persona_feedback", "voice_turns", "self_test_events"):
            conn.execute(f"DELETE FROM {table}")
