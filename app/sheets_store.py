"""Backend Sheets buat logger.py: worksheet `contacts` (1 baris per nomor, gabung
kontak + handover state) dan `log` (append-only, hash-only sesuai skema privasi
dokumen arsitektur bagian 3).

Header worksheet (baris 1), harus persis, urutan bebas asal nama kolom cocok:
- contacts: wa_number, wa_number_hash, name, first_seen, last_seen, message_count,
  handover, handover_since, handover_reason, fallback_streak
- log: wa_number_hash, timestamp, incoming_text, matched_faq_id, match_method,
  response_sent, fallback
"""
from app import config, sheets_client

_CONTACTS_COLUMNS = [
    "wa_number", "wa_number_hash", "name", "first_seen", "last_seen", "message_count",
    "handover", "handover_since", "handover_reason", "fallback_streak",
]


def _contacts_ws():
    return sheets_client.worksheet(config.GOOGLE_SHEET_CONTACTS_WORKSHEET)


def _log_ws():
    return sheets_client.worksheet(config.GOOGLE_SHEET_LOG_WORKSHEET)


def _find_contact_row(ws, wa_number_hash: str) -> tuple[int | None, dict]:
    """Return (row_number 1-based di sheet, dict record) atau (None, {}) kalau belum ada."""
    records = ws.get_all_records()
    for i, row in enumerate(records, start=2):  # baris 1 = header
        if str(row.get("wa_number_hash")) == wa_number_hash:
            return i, row
    return None, {}


def _write_contact_row(ws, row_number: int | None, values: dict) -> None:
    row = [str(values.get(col, "")) for col in _CONTACTS_COLUMNS]
    if row_number is None:
        ws.append_row(row, value_input_option="RAW")
    else:
        ws.update(f"A{row_number}:{chr(ord('A') + len(_CONTACTS_COLUMNS) - 1)}{row_number}", [row])


def append_log(
    wa_number_hash: str,
    timestamp: str,
    incoming_text: str,
    matched_faq_id: str | None,
    match_method: str,
    response_sent: str,
    fallback: bool,
) -> None:
    _log_ws().append_row(
        [wa_number_hash, timestamp, incoming_text, matched_faq_id or "", match_method, response_sent, int(fallback)],
        value_input_option="RAW",
    )


def get_contact(wa_number_hash: str) -> dict | None:
    """Return record contacts (dict of string values) atau None kalau nomor belum pernah tercatat."""
    _, row = _find_contact_row(_contacts_ws(), wa_number_hash)
    return row or None


def upsert_contact(wa_number: str, wa_number_hash: str, name: str, timestamp: str, **overrides) -> dict:
    """Buat/update baris contacts. `overrides` nimpa kolom apa pun (mis. handover=1).
    Return record lengkap setelah di-update."""
    ws = _contacts_ws()
    row_number, existing = _find_contact_row(ws, wa_number_hash)

    values = {
        "wa_number": wa_number,
        "wa_number_hash": wa_number_hash,
        "name": name or existing.get("name", ""),
        "first_seen": existing.get("first_seen") or timestamp,
        "last_seen": timestamp,
        "message_count": int(existing.get("message_count") or 0) + 1,
        "handover": existing.get("handover", 0),
        "handover_since": existing.get("handover_since", ""),
        "handover_reason": existing.get("handover_reason", ""),
        "fallback_streak": existing.get("fallback_streak", 0),
    }
    values.update(overrides)
    _write_contact_row(ws, row_number, values)
    return values


def set_contact_fields(wa_number_hash: str, **fields) -> None:
    """Update kolom tertentu tanpa nge-touch message_count/last_seen (dipakai
    buat set/reset handover di luar alur pesan masuk normal)."""
    ws = _contacts_ws()
    row_number, existing = _find_contact_row(ws, wa_number_hash)
    if row_number is None:
        return  # belum pernah tercatat, gak ada yang perlu diupdate
    values = {col: existing.get(col, "") for col in _CONTACTS_COLUMNS}
    values.update(fields)
    _write_contact_row(ws, row_number, values)
