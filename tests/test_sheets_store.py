"""Self-check offline (no network) buat pemetaan baris contacts di sheets_store.py.
Jalankan: python tests/test_sheets_store.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import sheets_store  # noqa: E402


class _FakeWorksheet:
    def __init__(self):
        self.appended = []
        self.updated = []

    def append_row(self, row, value_input_option="RAW"):
        self.appended.append(row)

    def update(self, cell_range, values):
        self.updated.append((cell_range, values))


def test_write_contact_row_append_when_no_row_number():
    ws = _FakeWorksheet()
    values = {
        "wa_number": "6281100011122", "wa_number_hash": "abc", "name": "Budi",
        "first_seen": "t1", "last_seen": "t2", "message_count": 3,
        "handover": 0, "handover_since": "", "handover_reason": "", "fallback_streak": 0,
    }
    sheets_store._write_contact_row(ws, None, values)
    assert len(ws.appended) == 1
    assert ws.appended[0] == [
        "6281100011122", "abc", "Budi", "t1", "t2", "3", "0", "", "", "0"
    ], "urutan kolom row harus persis ikut _CONTACTS_COLUMNS"


def test_write_contact_row_update_when_row_number_given():
    ws = _FakeWorksheet()
    values = {col: "" for col in sheets_store._CONTACTS_COLUMNS}
    sheets_store._write_contact_row(ws, 5, values)
    assert len(ws.updated) == 1
    cell_range, rows = ws.updated[0]
    assert cell_range.startswith("A5:") and cell_range.endswith("5")


if __name__ == "__main__":
    test_write_contact_row_append_when_no_row_number()
    test_write_contact_row_update_when_row_number_given()
    print("OK: pemetaan row contacts sesuai skema kolom")
