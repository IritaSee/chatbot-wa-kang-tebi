"""Self-check assert-based buat alur inti (matcher + handler + handover).
Jalankan: python tests/test_handler.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_log.db")

from app import config, handler, matcher  # noqa: E402

# app.config mungkin udah ke-import duluan (mis. test_faq_seed.py di-load lebih
# dulu sama pytest), jadi DB_PATH module-level attr-nya udah ke-freeze ke default
# sebelum env var di atas ke-set. Force ulang di sini biar test ini gak numpuk
# data ke data/conversation_log.db beneran.
config.DB_PATH = os.environ["DB_PATH"]

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
    number = "628111000111"
    config.FALLBACK_STREAK_FOR_HANDOVER = 2
    r1 = handler.handle_incoming_message(number, "asdasdasd", FAQS)
    assert r1 is not None, "fallback pertama harus tetap balas"
    r2 = handler.handle_incoming_message(number, "asdasdasd lagi", FAQS)
    assert r2 is not None, "fallback ke-2 (trigger handover) masih balas fallback msg-nya"
    r3 = handler.handle_incoming_message(number, "jadwal sidang ta dong", FAQS)
    assert r3 is None, "sudah handover, bot harus skip walau match FAQ"


def test_handler_explicit_admin_trigger_skips_bot():
    number = "628222000222"
    r1 = handler.handle_incoming_message(number, "admin", FAQS)
    assert r1 is None
    r2 = handler.handle_incoming_message(number, "jadwal sidang ta dong", FAQS)
    assert r2 is None, "handover eksplisit belum 24 jam, bot harus tetap skip"


if __name__ == "__main__":
    test_menu_number_match_lists_category_entries()
    test_keyword_exact_match()
    test_no_match_returns_none()
    test_handler_fallback_then_handover_after_streak()
    test_handler_explicit_admin_trigger_skips_bot()
    print("OK: semua self-check lolos")
