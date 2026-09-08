"""Conversation log + handover state + kontak (siapa aja yang pernah chat).

Backend Sheets (produksi, lihat sheets_store.py) kalau Google Sheets dikonfigurasi;
kalau tidak, fallback ke SQLite lokal (dev/test, offline, gak butuh jaringan).
wa_number disimpan mentah di contacts (keputusan sadar: admin perlu follow-up
manual & fase 2 butuh riwayat per kontak) + wa_number_hash tetap dipertahankan
sebagai kunci stabil buat join ke conversation_log (yang tetap hash-only).
"""
import hashlib
import os
import sqlite3
from datetime import datetime, timedelta

from app import config, sheets_client, sheets_store

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

CREATE TABLE IF NOT EXISTS contacts (
    wa_number_hash TEXT PRIMARY KEY,
    wa_number TEXT,
    name TEXT,
    first_seen TEXT,
    last_seen TEXT,
    message_count INTEGER NOT NULL DEFAULT 0,
    handover INTEGER NOT NULL DEFAULT 0,
    handover_since TEXT,
    handover_reason TEXT,
    fallback_streak INTEGER NOT NULL DEFAULT 0
);
"""


def hash_number(wa_number: str) -> str:
    return hashlib.sha256(wa_number.encode("utf-8")).hexdigest()


def _use_sheets() -> bool:
    return sheets_client.is_configured()


def _sqlite_touch_contact(conn: sqlite3.Connection, wa_number_hash: str, wa_number: str, name: str) -> None:
    now = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO contacts (wa_number_hash, wa_number, name, first_seen, last_seen, message_count) "
        "VALUES (?, ?, ?, ?, ?, 1) "
        "ON CONFLICT(wa_number_hash) DO UPDATE SET "
        "wa_number = excluded.wa_number, "
        "name = CASE WHEN excluded.name != '' THEN excluded.name ELSE contacts.name END, "
        "last_seen = excluded.last_seen, "
        "message_count = message_count + 1",
        (wa_number_hash, wa_number, name, now, now),
    )


def _sqlite_set_handover(conn: sqlite3.Connection, wa_number_hash: str, active: bool, reason: str | None) -> None:
    since = datetime.utcnow().isoformat() if active else None
    conn.execute(
        "INSERT INTO contacts (wa_number_hash, handover, handover_since, handover_reason) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(wa_number_hash) DO UPDATE SET handover = ?, handover_since = ?, handover_reason = ?",
        (wa_number_hash, int(active), since, reason, int(active), since, reason),
    )


def _open(path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(_SCHEMA)
    return conn


def _connect() -> sqlite3.Connection:
    """Filesystem serverless (mis. Vercel) sering read-only kecuali /tmp. Coba
    DB_PATH biasa dulu; kalau gagal (OSError, termasuk sqlite "unable to open
    database file"), fallback ke /tmp. /tmp ephemeral, tapi lebih baik daripada
    bot gak bisa jawab sama sekali."""
    try:
        return _open(config.DB_PATH)
    except (sqlite3.OperationalError, OSError):
        fallback_path = os.path.join("/tmp", os.path.basename(config.DB_PATH))
        return _open(fallback_path)


def log_interaction(
    wa_number_hash: str,
    incoming_text: str,
    matched_faq_id: str | None,
    match_method: str,
    response_sent: str,
    fallback: bool,
) -> None:
    timestamp = datetime.utcnow().isoformat()
    if _use_sheets():
        sheets_store.append_log(
            wa_number_hash, timestamp, incoming_text, matched_faq_id, match_method, response_sent, fallback
        )
        return
    with _connect() as conn:
        conn.execute(
            "INSERT INTO conversation_log "
            "(wa_number_hash, timestamp, incoming_text, matched_faq_id, match_method, response_sent, fallback) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (wa_number_hash, timestamp, incoming_text, matched_faq_id, match_method, response_sent, int(fallback)),
        )


def is_handover_active(wa_number_hash: str) -> bool:
    """True kalau nomor masih dalam status handover. Auto-reset kalau trigger-nya
    'explicit' (admin/cs/manusia) dan sudah lewat HANDOVER_RESET_HOURS.
    Trigger 'fallback_streak' cuma direset lewat register_match()."""
    if _use_sheets():
        contact = sheets_store.get_contact(wa_number_hash)
        if not contact or not int(contact.get("handover") or 0):
            return False
        reason = contact.get("handover_reason")
        since_raw = contact.get("handover_since")
        if reason == "explicit" and since_raw:
            since = datetime.fromisoformat(since_raw)
            if datetime.utcnow() - since >= timedelta(hours=config.HANDOVER_RESET_HOURS):
                sheets_store.set_contact_fields(wa_number_hash, handover=0, handover_since="", handover_reason="")
                return False
        return True

    with _connect() as conn:
        row = conn.execute(
            "SELECT handover, handover_since, handover_reason FROM contacts WHERE wa_number_hash = ?",
            (wa_number_hash,),
        ).fetchone()
        if not row or not row[0]:
            return False
        handover, handover_since, reason = row
        if reason == "explicit" and handover_since:
            since = datetime.fromisoformat(handover_since)
            if datetime.utcnow() - since >= timedelta(hours=config.HANDOVER_RESET_HOURS):
                _sqlite_set_handover(conn, wa_number_hash, active=False, reason=None)
                return False
        return True


def trigger_handover(wa_number_hash: str, reason: str, wa_number: str = "", name: str = "") -> None:
    """reason: 'explicit' (kata admin/cs/manusia) atau 'fallback_streak'."""
    if _use_sheets():
        timestamp = datetime.utcnow().isoformat()
        sheets_store.upsert_contact(
            wa_number, wa_number_hash, name, timestamp,
            handover=1, handover_since=timestamp, handover_reason=reason,
        )
        return
    with _connect() as conn:
        _sqlite_touch_contact(conn, wa_number_hash, wa_number, name)
        _sqlite_set_handover(conn, wa_number_hash, active=True, reason=reason)


def reset_handover(wa_number_hash: str) -> None:
    if _use_sheets():
        sheets_store.set_contact_fields(wa_number_hash, handover=0, handover_since="", handover_reason="")
        return
    with _connect() as conn:
        _sqlite_set_handover(conn, wa_number_hash, active=False, reason=None)


def register_fallback(wa_number_hash: str, wa_number: str = "", name: str = "") -> bool:
    """Increment fallback streak, return True kalau streak baru cukup buat trigger handover."""
    if _use_sheets():
        timestamp = datetime.utcnow().isoformat()
        contact = sheets_store.get_contact(wa_number_hash) or {}
        streak = int(contact.get("fallback_streak") or 0) + 1
        sheets_store.upsert_contact(wa_number, wa_number_hash, name, timestamp, fallback_streak=streak)
        return streak >= config.FALLBACK_STREAK_FOR_HANDOVER

    with _connect() as conn:
        row = conn.execute(
            "SELECT fallback_streak FROM contacts WHERE wa_number_hash = ?", (wa_number_hash,)
        ).fetchone()
        streak = (row[0] if row else 0) + 1
        _sqlite_touch_contact(conn, wa_number_hash, wa_number, name)
        conn.execute("UPDATE contacts SET fallback_streak = ? WHERE wa_number_hash = ?", (streak, wa_number_hash))
        return streak >= config.FALLBACK_STREAK_FOR_HANDOVER


def register_match(wa_number_hash: str, wa_number: str = "", name: str = "") -> None:
    """Match berhasil ke FAQ: reset fallback streak. Kalau handover aktif karena
    fallback_streak (bukan trigger eksplisit "admin"), reset juga handover-nya."""
    if _use_sheets():
        timestamp = datetime.utcnow().isoformat()
        contact = sheets_store.get_contact(wa_number_hash) or {}
        overrides = {"fallback_streak": 0}
        if int(contact.get("handover") or 0) and contact.get("handover_reason") == "fallback_streak":
            overrides.update(handover=0, handover_since="", handover_reason="")
        sheets_store.upsert_contact(wa_number, wa_number_hash, name, timestamp, **overrides)
        return

    with _connect() as conn:
        row = conn.execute(
            "SELECT handover, handover_reason FROM contacts WHERE wa_number_hash = ?", (wa_number_hash,)
        ).fetchone()
        if row and row[0] and row[1] == "fallback_streak":
            _sqlite_set_handover(conn, wa_number_hash, active=False, reason=None)
        _sqlite_touch_contact(conn, wa_number_hash, wa_number, name)
        conn.execute("UPDATE contacts SET fallback_streak = 0 WHERE wa_number_hash = ?", (wa_number_hash,))
