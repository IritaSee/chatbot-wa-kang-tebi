"""Conversation log + handover state, disimpan di SQLite (data/conversation_log.db).
wa_number di-hash (sha256) sebelum disimpan, sesuai skema privasi di dokumen arsitektur.
"""
import hashlib
import os
import sqlite3
from datetime import datetime, timedelta

from app import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS conversation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wa_number_hash TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    incoming_text TEXT NOT NULL,
    matched_faq_id TEXT,
    match_method TEXT NOT NULL,
    response_sent TEXT NOT NULL,
    fallback INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS handover_state (
    wa_number_hash TEXT PRIMARY KEY,
    handover INTEGER NOT NULL DEFAULT 0,
    handover_since TEXT,
    handover_reason TEXT,
    fallback_streak INTEGER NOT NULL DEFAULT 0
);
"""


def hash_number(wa_number: str) -> str:
    return hashlib.sha256(wa_number.encode("utf-8")).hexdigest()


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(config.DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.executescript(_SCHEMA)
    return conn


def log_interaction(
    wa_number_hash: str,
    incoming_text: str,
    matched_faq_id: str | None,
    match_method: str,
    response_sent: str,
    fallback: bool,
) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO conversation_log "
            "(wa_number_hash, timestamp, incoming_text, matched_faq_id, match_method, response_sent, fallback) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                wa_number_hash,
                datetime.utcnow().isoformat(),
                incoming_text,
                matched_faq_id,
                match_method,
                response_sent,
                int(fallback),
            ),
        )


def is_handover_active(wa_number_hash: str) -> bool:
    """True kalau nomor masih dalam status handover. Auto-reset kalau trigger-nya
    'explicit' (admin/cs/manusia) dan sudah lewat HANDOVER_RESET_HOURS.
    Trigger 'fallback_streak' cuma direset lewat register_match()."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT handover, handover_since, handover_reason FROM handover_state WHERE wa_number_hash = ?",
            (wa_number_hash,),
        ).fetchone()
        if not row or not row[0]:
            return False
        handover, handover_since, reason = row
        if reason == "explicit" and handover_since:
            since = datetime.fromisoformat(handover_since)
            if datetime.utcnow() - since >= timedelta(hours=config.HANDOVER_RESET_HOURS):
                _set_handover(conn, wa_number_hash, active=False, reason=None)
                return False
        return True


def trigger_handover(wa_number_hash: str, reason: str) -> None:
    """reason: 'explicit' (kata admin/cs/manusia) atau 'fallback_streak'."""
    with _connect() as conn:
        _set_handover(conn, wa_number_hash, active=True, reason=reason)


def reset_handover(wa_number_hash: str) -> None:
    with _connect() as conn:
        _set_handover(conn, wa_number_hash, active=False, reason=None)


def register_fallback(wa_number_hash: str) -> bool:
    """Increment fallback streak, return True kalau streak baru cukup buat trigger handover."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT fallback_streak FROM handover_state WHERE wa_number_hash = ?",
            (wa_number_hash,),
        ).fetchone()
        streak = (row[0] if row else 0) + 1
        conn.execute(
            "INSERT INTO handover_state (wa_number_hash, handover, handover_since, fallback_streak) "
            "VALUES (?, 0, NULL, ?) "
            "ON CONFLICT(wa_number_hash) DO UPDATE SET fallback_streak = ?",
            (wa_number_hash, streak, streak),
        )
        return streak >= config.FALLBACK_STREAK_FOR_HANDOVER


def register_match(wa_number_hash: str) -> None:
    """Match berhasil ke FAQ: reset fallback streak. Kalau handover aktif karena
    fallback_streak (bukan trigger eksplisit "admin"), reset juga handover-nya."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT handover, handover_reason FROM handover_state WHERE wa_number_hash = ?",
            (wa_number_hash,),
        ).fetchone()
        if row and row[0] and row[1] == "fallback_streak":
            _set_handover(conn, wa_number_hash, active=False, reason=None)
        conn.execute(
            "INSERT INTO handover_state (wa_number_hash, handover, handover_since, fallback_streak) "
            "VALUES (?, 0, NULL, 0) "
            "ON CONFLICT(wa_number_hash) DO UPDATE SET fallback_streak = 0",
            (wa_number_hash,),
        )


def _set_handover(conn: sqlite3.Connection, wa_number_hash: str, active: bool, reason: str | None) -> None:
    since = datetime.utcnow().isoformat() if active else None
    conn.execute(
        "INSERT INTO handover_state (wa_number_hash, handover, handover_since, handover_reason, fallback_streak) "
        "VALUES (?, ?, ?, ?, 0) "
        "ON CONFLICT(wa_number_hash) DO UPDATE SET handover = ?, handover_since = ?, handover_reason = ?",
        (wa_number_hash, int(active), since, reason, int(active), since, reason),
    )
