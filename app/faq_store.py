"""FAQ store: baca dari Google Sheets (gspread) kalau kredensial ada,
kalau tidak fallback ke data/faq_seed.json (dev lokal / belum ada Sheets).
FAQ di-cache di memory proses: di serverless (Vercel), container di-reuse antar
request kalau masih "warm", jadi Sheets cuma ke-hit pas cold start, bukan tiap pesan.
"""
import json

from app import config, sheets_client

_faq_cache: list[dict] | None = None

_SHEET_COLUMNS = [
    "id", "category", "trigger_keywords", "question_examples",
    "answer", "media_url", "active", "last_updated",
]


def _row_to_entry(row: dict) -> dict:
    return {
        "id": row.get("id", ""),
        "category": row.get("category", "lainnya"),
        "trigger_keywords": [
            k.strip() for k in str(row.get("trigger_keywords", "")).split(",") if k.strip()
        ],
        "question_examples": [
            q.strip() for q in str(row.get("question_examples", "")).split(",") if q.strip()
        ],
        "answer": row.get("answer", ""),
        "media_url": row.get("media_url", ""),
        "active": str(row.get("active", "true")).strip().lower() in ("true", "1", "yes"),
        "last_updated": row.get("last_updated", ""),
    }


def _load_from_sheets() -> list[dict]:
    sheet = sheets_client.worksheet(config.GOOGLE_SHEET_WORKSHEET)
    rows = sheet.get_all_records()
    return [_row_to_entry(r) for r in rows]


def _load_from_local_json() -> list[dict]:
    with open(config.FAQ_SEED_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_faqs(use_cache: bool = True) -> list[dict]:
    """Return list of active FAQ entries. Sheets kalau dikonfigurasi, else local JSON.
    Di-cache di memory proses (lihat docstring modul) buat hemat kuota Sheets API."""
    global _faq_cache
    if use_cache and _faq_cache is not None:
        return _faq_cache

    if sheets_client.is_configured():
        entries = _load_from_sheets()
    else:
        entries = _load_from_local_json()
    active = [e for e in entries if e.get("active", True)]

    if use_cache:
        _faq_cache = active
    return active
