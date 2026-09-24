"""Conversation log + handover state + kontak (siapa aja yang pernah chat).

Full Google Sheets (lihat sheets_store.py) sebagai satu-satunya backend --
production wajib GOOGLE_SHEET_ID + kredensial service account dikonfigurasi
(lihat sheets_client.is_configured()). Gak ada fallback SQLite lokal lagi:
kalau Sheets belum dikonfigurasi, panggil fungsi di sini raise RuntimeError
lebih awal & jelas, daripada diam-diam nyimpen ke .db yang gak sinkron sama
data produksi.

wa_number disimpan mentah di contacts (keputusan sadar: admin perlu follow-up
manual & fase 2 butuh riwayat per kontak) + wa_number_hash tetap dipertahankan
sebagai kunci stabil buat join ke log (yang tetap hash-only).
"""
import hashlib
import re
from datetime import datetime, timedelta

from app import config, sheets_client, sheets_store


def hash_number(wa_number: str) -> str:
    """Normalize dulu (ambil digit doang) sebelum di-hash. Fonnte kadang ngirim

    nomor sender dengan format sedikit beda antar-webhook call (spasi, "+",
    dst) buat kontak yang sama -> tanpa normalisasi, hash-nya beda -> sistem
    anggap "orang baru" -> handover aktif ketembus/gak kebaca (bug: bot balas
    lagi padahal user baru ketik "admin", session kerasa "reset" kecepetan).
    """
    digits = re.sub(r"\D", "", wa_number)
    return hashlib.sha256((digits or wa_number).encode("utf-8")).hexdigest()


def _require_sheets() -> None:
    if not sheets_client.is_configured():
        raise RuntimeError(
            "Google Sheets belum dikonfigurasi (GOOGLE_SHEET_ID + "
            "GOOGLE_SERVICE_ACCOUNT_FILE/GOOGLE_SERVICE_ACCOUNT_JSON). "
            "Contacts/log/handover wajib Sheets, gak ada fallback lokal."
        )


def log_interaction(
    wa_number_hash: str,
    incoming_text: str,
    matched_faq_id: str | None,
    match_method: str,
    response_sent: str,
    fallback: bool,
) -> None:
    _require_sheets()
    timestamp = datetime.utcnow().isoformat()
    sheets_store.append_log(
        wa_number_hash, timestamp, incoming_text, matched_faq_id, match_method, response_sent, fallback
    )


def is_handover_active(wa_number_hash: str) -> bool:
    """True kalau nomor masih dalam status handover. Auto-reset kalau trigger-nya
    'explicit' (admin/cs/manusia) dan sudah lewat HANDOVER_RESET_HOURS.
    Trigger 'fallback_streak' cuma direset lewat register_match()."""
    _require_sheets()
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


def trigger_handover(wa_number_hash: str, reason: str, wa_number: str = "", name: str = "") -> None:
    """reason: 'explicit' (kata admin/cs/manusia) atau 'fallback_streak'."""
    _require_sheets()
    timestamp = datetime.utcnow().isoformat()
    sheets_store.upsert_contact(
        wa_number, wa_number_hash, name, timestamp,
        handover=1, handover_since=timestamp, handover_reason=reason,
    )


def reset_handover(wa_number_hash: str) -> None:
    _require_sheets()
    sheets_store.set_contact_fields(wa_number_hash, handover=0, handover_since="", handover_reason="")


def register_fallback(wa_number_hash: str, wa_number: str = "", name: str = "") -> bool:
    """Increment fallback streak, return True kalau streak baru cukup buat trigger handover."""
    _require_sheets()
    timestamp = datetime.utcnow().isoformat()
    contact = sheets_store.get_contact(wa_number_hash) or {}
    streak = int(contact.get("fallback_streak") or 0) + 1
    sheets_store.upsert_contact(wa_number, wa_number_hash, name, timestamp, fallback_streak=streak)
    return streak >= config.FALLBACK_STREAK_FOR_HANDOVER


def is_bot_enabled(wa_number_hash: str) -> bool:
    """`bot_enabled=0` di worksheet contacts -> admin matiin bot total buat nomor
    itu (manual penuh, fuzzy dan LLM sama-sama gak jalan). Default (kolom kosong)
    = enabled."""
    _require_sheets()
    contact = sheets_store.get_contact(wa_number_hash)
    if not contact:
        return True
    return str(contact.get("bot_enabled") or "1") != "0"


def is_llm_enabled(wa_number_hash: str) -> bool:
    """`llm_enabled=0` -> tier 2 (LLM) dimatiin admin buat nomor itu, fuzzy tetap
    jalan. Default (kolom kosong) = enabled."""
    _require_sheets()
    contact = sheets_store.get_contact(wa_number_hash)
    if not contact:
        return True
    return str(contact.get("llm_enabled") or "1") != "0"


def get_mode(wa_number_hash: str) -> str:
    """Return "llm" kalau nomor lagi dalam sesi tier 2 (dipilih via menu "8"),
    else "". Auto-expire ke "" kalau idle > LLM_MODE_IDLE_MINUTES (pola sama
    persis is_handover_active: reset lazy pas dibaca, bukan job terpisah)."""
    _require_sheets()
    contact = sheets_store.get_contact(wa_number_hash)
    if not contact or contact.get("mode") != "llm":
        return ""
    since_raw = contact.get("mode_since")
    if since_raw:
        since = datetime.fromisoformat(since_raw)
        if datetime.utcnow() - since >= timedelta(minutes=config.LLM_MODE_IDLE_MINUTES):
            sheets_store.set_contact_fields(wa_number_hash, mode="", mode_since="")
            return ""
    return "llm"


def set_mode(wa_number_hash: str, mode: str, wa_number: str = "", name: str = "") -> None:
    """mode: "llm" (masuk tier 2) atau "" (balik ke fuzzy: user ketik menu/0,
    atau dieskalasi ke admin). upsert (bukan set_contact_fields) karena bisa
    dipanggil buat kontak yang belum ada baris (baru pertama kali pilih menu 8)."""
    _require_sheets()
    timestamp = datetime.utcnow().isoformat()
    sheets_store.upsert_contact(
        wa_number, wa_number_hash, name, timestamp, mode=mode, mode_since=timestamp if mode else ""
    )


def consume_llm_quota(wa_number_hash: str, wa_number: str = "", name: str = "") -> bool:
    """Increment counter harian LLM buat nomor ini. Return True kalau masih di
    bawah LLM_DAILY_CAP (boleh lanjut manggil LLM), False kalau sudah habis
    (caller harus eskalasi, bukan manggil LLM lagi)."""
    _require_sheets()
    timestamp = datetime.utcnow().isoformat()
    today = timestamp[:10]
    contact = sheets_store.get_contact(wa_number_hash) or {}
    count = int(contact.get("llm_count") or 0) if contact.get("llm_date") == today else 0
    count += 1
    sheets_store.upsert_contact(wa_number, wa_number_hash, name, timestamp, llm_count=count, llm_date=today)
    return count <= config.LLM_DAILY_CAP


def register_match(wa_number_hash: str, wa_number: str = "", name: str = "") -> None:
    """Match berhasil ke FAQ: reset fallback streak. Kalau handover aktif karena
    fallback_streak (bukan trigger eksplisit "admin"), reset juga handover-nya."""
    _require_sheets()
    timestamp = datetime.utcnow().isoformat()
    contact = sheets_store.get_contact(wa_number_hash) or {}
    overrides = {"fallback_streak": 0}
    if int(contact.get("handover") or 0) and contact.get("handover_reason") == "fallback_streak":
        overrides.update(handover=0, handover_since="", handover_reason="")
    sheets_store.upsert_contact(wa_number, wa_number_hash, name, timestamp, **overrides)
