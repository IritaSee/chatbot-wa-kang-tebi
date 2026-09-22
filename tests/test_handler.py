"""Self-check assert-based buat alur inti (matcher + handler + handover).
Butuh GOOGLE_SHEET_ID + kredensial di .env (pakai spreadsheet dev/test, bukan
produksi -- logger.py gak ada fallback lokal, full Sheets). Tanpa itu, test
yang nyentuh logger (handover dkk) di-skip otomatis.
Jalankan: python tests/test_handler.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config, handler, matcher, sheets_client  # noqa: E402

_SHEETS_READY = sheets_client.is_configured()

FAQS = [
    {"id": "TA-001", "category": "tugas_akhir", "trigger_keywords": ["jadwal sidang", "sidang ta"],
     "answer": "Jadwal sidang ada di link.", "media_url": "https://contoh.ac.id/jadwal-sidang", "active": True},
    {"id": "TA-002", "category": "tugas_akhir", "trigger_keywords": ["panduan ta"],
     "answer": "Panduan TA lengkap.", "media_url": "", "active": True},
    {"id": "KTK-001", "category": "kontak", "trigger_keywords": ["kontak", "hubungi admin"],
     "answer": "Kontak admin: 08xx.", "media_url": "", "active": True},
]


def test_menu_number_match_lists_category_entries():
    category = matcher.match_menu("1")
    assert category == "tugas_akhir", "menu 1 harus map ke kategori tugas_akhir"
    entries = matcher.entries_by_category(category, FAQS)
    assert {e["id"] for e in entries} == {"TA-001", "TA-002"}


def test_keyword_exact_match():
    faq, method, score = matcher.match("kapan jadwal sidang TA?", FAQS)
    assert faq is not None and faq["id"] == "TA-001"
    assert method == "keyword"


def test_no_match_returns_none():
    faq, method, score = matcher.match("xyzxyz random gibberish", FAQS)
    assert faq is None


def test_handler_fallback_then_handover_after_streak():
    if not _SHEETS_READY:
        print("SKIP test_handler_fallback_then_handover_after_streak: Sheets belum dikonfigurasi")
        return
    number = "628111000111"
    config.FALLBACK_STREAK_FOR_HANDOVER = 2
    r1 = handler.handle_incoming_message(number, "asdasdasd", FAQS)
    assert r1 is not None, "fallback pertama harus tetap balas"
    r2 = handler.handle_incoming_message(number, "asdasdasd lagi", FAQS)
    assert r2 is not None, "fallback ke-2 (trigger handover) masih balas fallback msg-nya"
    r3 = handler.handle_incoming_message(number, "jadwal sidang ta dong", FAQS)
    assert r3 is None, "sudah handover, bot harus skip walau match FAQ"


def test_hash_number_normalizes_format_variants():
    """Bug: Fonnte kadang ngirim sender beda format ('+62...' vs '62...' vs ada
    spasi) buat nomor yang sama -> tanpa normalisasi hash beda -> handover
    admin gak kebaca lagi (kerasa kayak session reset kecepetan)."""
    from app import logger
    base = logger.hash_number("6281234567890")
    assert logger.hash_number("+62 8123-4567-890") == base
    assert logger.hash_number(" 6281234567890 ") == base


def test_handler_explicit_admin_trigger_skips_bot():
    if not _SHEETS_READY:
        print("SKIP test_handler_explicit_admin_trigger_skips_bot: Sheets belum dikonfigurasi")
        return
    number = "628222000222"
    r1 = handler.handle_incoming_message(number, "admin", FAQS)
    assert r1 is None
    r2 = handler.handle_incoming_message(number, "jadwal sidang ta dong", FAQS)
    assert r2 is None, "handover eksplisit belum 24 jam, bot harus tetap skip"


def _patch_llm_answer(fn):
    """Patch manual (bukan fixture pytest monkeypatch) biar jalan baik lewat
    `python tests/test_handler.py` (__main__) maupun pytest."""
    from app import llm

    class _Patch:
        def __enter__(self):
            self._orig = llm.answer
            llm.answer = fn
            return self

        def __exit__(self, *exc):
            llm.answer = self._orig

    return _Patch()


def test_menu_8_enters_llm_mode_and_answers():
    """Menu "8. Lainnya" -> mode llm; pesan berikutnya dijawab llm.answer (mocked,
    nol network) bukan fuzzy, walau teksnya gak match keyword FAQ manapun."""
    if not _SHEETS_READY:
        print("SKIP test_menu_8_enters_llm_mode_and_answers: Sheets belum dikonfigurasi")
        return
    number = "628444000444"
    with _patch_llm_answer(lambda text, faqs: "Jawaban dari LLM."):
        r1 = handler.handle_incoming_message(number, "8", FAQS)
        assert r1 is not None and "menu" in r1.lower()

        r2 = handler.handle_incoming_message(number, "pertanyaan bebas gak ada di faq", FAQS)
        assert r2 is not None and "Jawaban dari LLM." in r2


def test_llm_none_escalates_to_admin():
    """llm.answer return None (gagal/gak ada dasar) -> bot balas "diteruskan ke
    admin" + trigger_handover, bukan diam kayak fallback fuzzy biasa."""
    if not _SHEETS_READY:
        print("SKIP test_llm_none_escalates_to_admin: Sheets belum dikonfigurasi")
        return
    from app import logger

    number = "628555000555"
    number_hash = logger.hash_number(number)
    with _patch_llm_answer(lambda text, faqs: None):
        handler.handle_incoming_message(number, "8", FAQS)
        r2 = handler.handle_incoming_message(number, "pertanyaan susah", FAQS)
    assert r2 is not None and "admin" in r2.lower()
    assert logger.is_handover_active(number_hash)


def test_llm_daily_cap_escalates_without_calling_llm():
    """Kuota LLM_DAILY_CAP habis -> langsung eskalasi, llm.answer gak dipanggil
    sama sekali (hemat biaya)."""
    if not _SHEETS_READY:
        print("SKIP test_llm_daily_cap_escalates_without_calling_llm: Sheets belum dikonfigurasi")
        return
    calls = []
    config.LLM_DAILY_CAP = 1
    number = "628666000666"
    with _patch_llm_answer(lambda text, faqs: calls.append(1) or "harusnya gak kepanggil"):
        handler.handle_incoming_message(number, "8", FAQS)
        r2 = handler.handle_incoming_message(number, "pertanyaan 1", FAQS)
        assert r2 is not None and "Jawaban" not in r2 and calls == [1]
        r3 = handler.handle_incoming_message(number, "pertanyaan 2", FAQS)
    assert r3 is not None and "admin" in r3.lower()
    assert calls == [1], "quota habis, llm.answer gak boleh kepanggil lagi"


def test_menu_keyword_exits_llm_mode_back_to_fuzzy():
    """Ketik "menu" pas lagi mode llm -> balik ke fuzzy, llm.answer gak dipanggil."""
    if not _SHEETS_READY:
        print("SKIP test_menu_keyword_exits_llm_mode_back_to_fuzzy: Sheets belum dikonfigurasi")
        return
    from app import logger

    calls = []
    number = "628777000777"
    number_hash = logger.hash_number(number)
    with _patch_llm_answer(lambda text, faqs: calls.append(1) or "x"):
        handler.handle_incoming_message(number, "8", FAQS)
        handler.handle_incoming_message(number, "menu", FAQS)
        assert logger.get_mode(number_hash) == ""

        r = handler.handle_incoming_message(number, "kapan jadwal sidang TA?", FAQS)
    assert r is not None and "Jadwal sidang" in r
    assert calls == [], "sudah keluar mode llm, llm.answer gak boleh kepanggil"


def test_handler_manual_reset_reactivates_ai_before_timeout():
    """Admin bisa reaktivasi AI kapan aja (mis. edit cell `handover` jadi 0 di
    Google Sheets, atau panggil logger.reset_handover langsung) tanpa nunggu
    HANDOVER_RESET_HOURS -- mekanisme ini jalan di samping timeout utama."""
    if not _SHEETS_READY:
        print("SKIP test_handler_manual_reset_reactivates_ai_before_timeout: Sheets belum dikonfigurasi")
        return
    from app import logger

    number = "628333000333"
    number_hash = logger.hash_number(number)

    r1 = handler.handle_incoming_message(number, "admin", FAQS)
    assert r1 is None, "user ketik 'admin' -> bot stop balas"
    r2 = handler.handle_incoming_message(number, "jadwal sidang ta dong", FAQS)
    assert r2 is None, "masih handover, bot tetap skip walau match FAQ"

    logger.reset_handover(number_hash)  # admin nutup percakapan & reaktivasi manual

    r3 = handler.handle_incoming_message(number, "jadwal sidang ta dong", FAQS)
    assert r3 is not None, "sudah direset admin, AI harus balas lagi (gak perlu nunggu 24 jam)"


if __name__ == "__main__":
    test_menu_number_match_lists_category_entries()
    test_keyword_exact_match()
    test_no_match_returns_none()
    test_handler_fallback_then_handover_after_streak()
    test_hash_number_normalizes_format_variants()
    test_handler_explicit_admin_trigger_skips_bot()
    test_menu_8_enters_llm_mode_and_answers()
    test_llm_none_escalates_to_admin()
    test_llm_daily_cap_escalates_without_calling_llm()
    test_menu_keyword_exits_llm_mode_back_to_fuzzy()
    test_handler_manual_reset_reactivates_ai_before_timeout()
    print("OK: semua self-check lolos")
