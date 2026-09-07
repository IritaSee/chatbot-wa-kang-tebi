"""FAQ store: baca dari Google Sheets (gspread) kalau kredensial ada,
kalau tidak fallback ke data/faq_seed.json (dev lokal / belum ada Sheets).
"""
import json

from app import config

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
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    if config.GOOGLE_SERVICE_ACCOUNT_JSON:
        # deploy (Fly secret): isi JSON langsung di env var, gak ada file di repo
        info = json.loads(config.GOOGLE_SERVICE_ACCOUNT_JSON)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
    else:
        # dev lokal: path ke file .json (di-gitignore)
        creds = Credentials.from_service_account_file(config.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(config.GOOGLE_SHEET_ID).worksheet(config.GOOGLE_SHEET_WORKSHEET)
    rows = sheet.get_all_records()
    return [_row_to_entry(r) for r in rows]


def _load_from_local_json() -> list[dict]:
    with open(config.FAQ_SEED_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_faqs() -> list[dict]:
    """Return list of active FAQ entries. Sheets kalau dikonfigurasi, else local JSON."""
    has_sheets_creds = config.GOOGLE_SERVICE_ACCOUNT_JSON or config.GOOGLE_SERVICE_ACCOUNT_FILE
    if config.GOOGLE_SHEET_ID and has_sheets_creds:
        entries = _load_from_sheets()
    else:
        entries = _load_from_local_json()
    return [e for e in entries if e.get("active", True)]
