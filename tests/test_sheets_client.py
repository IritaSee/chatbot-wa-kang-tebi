"""Self-check offline (no network) buat sheets_client._spreadsheet: kalau
GOOGLE_SHEET_ID gak ketemu, harus bikin spreadsheet baru, bukan crash.
Jalankan: python tests/test_sheets_client.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gspread  # noqa: E402

from app import config, sheets_client  # noqa: E402


class _FakeSpreadsheet:
    def __init__(self, id_):
        self.id = id_


class _FakeGspreadClient:
    def __init__(self):
        self.create_calls = []

    def open_by_key(self, key):
        raise gspread.exceptions.SpreadsheetNotFound("not found")

    def create(self, title):
        self.create_calls.append(title)
        return _FakeSpreadsheet("new-id-123")


def test_spreadsheet_not_found_creates_new_one():
    config.GOOGLE_SHEET_ID = "missing-id"
    config.GOOGLE_SERVICE_ACCOUNT_JSON = '{"fake": "creds"}'
    sheets_client._spreadsheet.cache_clear()

    fake_client = _FakeGspreadClient()
    import unittest.mock as mock

    with mock.patch("gspread.authorize", return_value=fake_client), \
         mock.patch("google.oauth2.service_account.Credentials.from_service_account_info"):
        result = sheets_client._spreadsheet()

    assert isinstance(result, _FakeSpreadsheet), "harus fallback bikin spreadsheet baru, bukan raise"
    assert result.id == "new-id-123"
    assert len(fake_client.create_calls) == 1, "gspread client.create() harus dipanggil sekali"

    sheets_client._spreadsheet.cache_clear()


if __name__ == "__main__":
    test_spreadsheet_not_found_creates_new_one()
    print("OK: auto-create spreadsheet baru kalau GOOGLE_SHEET_ID gak ketemu")
