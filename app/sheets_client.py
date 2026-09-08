"""Client gspread yang dipakai bareng oleh faq_store.py (baca FAQ) dan
sheets_store.py (baca/tulis contacts & log). Satu titik auth, biar gak dobel."""
import json
from functools import lru_cache

from app import config

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def is_configured() -> bool:
    has_creds = bool(config.GOOGLE_SERVICE_ACCOUNT_JSON or config.GOOGLE_SERVICE_ACCOUNT_FILE)
    return bool(config.GOOGLE_SHEET_ID) and has_creds


@lru_cache(maxsize=1)
def _spreadsheet():
    import gspread
    from google.oauth2.service_account import Credentials

    if config.GOOGLE_SERVICE_ACCOUNT_JSON:
        # deploy: isi JSON service account langsung di env var, gak ada file di repo
        info = json.loads(config.GOOGLE_SERVICE_ACCOUNT_JSON)
        creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
    else:
        # dev lokal: path ke file .json (di-gitignore)
        creds = Credentials.from_service_account_file(config.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=_SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(config.GOOGLE_SHEET_ID)


def worksheet(name: str):
    return _spreadsheet().worksheet(name)
