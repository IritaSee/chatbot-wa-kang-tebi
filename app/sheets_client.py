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
    try:
        return client.open_by_key(config.GOOGLE_SHEET_ID)
    except gspread.exceptions.SpreadsheetNotFound:
        # GOOGLE_SHEET_ID diisi tapi spreadsheet-nya gak ketemu (belum dibikin/salah
        # ID/kehapus) -> bikin spreadsheet baru daripada webhook crash tiap pesan.
        # ID barunya beda dari GOOGLE_SHEET_ID di env, jadi dicetak biar admin bisa
        # update env var-nya (kalau enggak, tiap cold start bikin spreadsheet baru lagi).
        spreadsheet = client.create(f"Kang Tebi Bot Data ({config.GOOGLE_SHEET_ID})")
        print(
            f"[sheets_client] GOOGLE_SHEET_ID={config.GOOGLE_SHEET_ID!r} gak ketemu, "
            f"bikin spreadsheet baru -> id={spreadsheet.id!r}. "
            "Update GOOGLE_SHEET_ID env var ke ID ini biar gak bikin baru lagi tiap cold start."
        )
        return spreadsheet


def worksheet(name: str, header: list[str] | None = None):
    """Return worksheet `name`. Kalau belum ada di spreadsheet (mis. cuma sheet
    `faq` yang dibikin manual, `contacts`/`log` belum), bikin otomatis + isi
    baris header -- daripada gspread.exceptions.WorksheetNotFound bikin
    /webhook crash tiap ada pesan (handover jadi gak pernah kesimpen)."""
    import gspread

    spreadsheet = _spreadsheet()
    try:
        return spreadsheet.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=name, rows=1000, cols=max(len(header or []), 10))
        if header:
            ws.append_row(header, value_input_option="RAW")
        return ws
