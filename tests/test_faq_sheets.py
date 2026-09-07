"""Integration check: Google Sheet FAQ bisa diakses (auth + permission) & dibaca.
Butuh kredensial asli (GOOGLE_SHEET_ID + GOOGLE_SERVICE_ACCOUNT_FILE valid & sheet
sudah di-share ke service account) -> skip otomatis kalau belum dikonfigurasi,
biar gak numpahin CI/dev lain yang belum setup Sheets.

Jalankan: python tests/test_faq_sheets.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config, faq_store  # noqa: E402


def _sheets_configured() -> bool:
    return bool(
        config.GOOGLE_SHEET_ID
        and config.GOOGLE_SERVICE_ACCOUNT_FILE
        and os.path.exists(config.GOOGLE_SERVICE_ACCOUNT_FILE)
    )


def test_sheet_accessible_and_readable():
    if not _sheets_configured():
        print(
            "SKIP: GOOGLE_SHEET_ID/GOOGLE_SERVICE_ACCOUNT_FILE belum dikonfigurasi "
            "atau file kredensial gak ketemu -> lewati integration test Sheets."
        )
        return

    try:
        entries = faq_store._load_from_sheets()
    except Exception as exc:  # noqa: BLE001 - mau tangkap semua error auth/permission/network
        raise AssertionError(
            f"Gagal akses/baca Google Sheet (cek: sheet di-share ke service account, "
            f"GOOGLE_SHEET_ID benar, worksheet '{config.GOOGLE_SHEET_WORKSHEET}' ada). "
            f"Detail: {exc}"
        ) from exc

    assert isinstance(entries, list), "hasil baca sheet harus berupa list"
    assert len(entries) > 0, "sheet kebaca tapi kosong (cek header/isi worksheet)"

    first = entries[0]
    for field in ("id", "category", "answer", "trigger_keywords"):
        assert field in first, f"kolom '{field}' gak ketemu di hasil parsing sheet"
    assert isinstance(first["trigger_keywords"], list)


if __name__ == "__main__":
    test_sheet_accessible_and_readable()
    print("OK: Google Sheet FAQ bisa diakses & dibaca (atau di-skip kalau belum dikonfigurasi)")
