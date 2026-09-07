"""Self-check assert-based buat alur inti (matcher + handler + handover).
Jalankan: python tests/test_handler.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_log.db")

from app import config, handler, matcher  # noqa: E402

FAQS = [
    {"id": "faq-001", "category": "jadwal", "trigger_keywords": ["jadwal", "kapan daftar"],
     "answer": "Jadwal ada di link.", "active": True},
    {"id": "faq-003", "category": "kontak", "trigger_keywords": ["kontak", "hubungi"],
     "answer": "Kontak admin: 08xx.", "active": True},
]


def test_menu_number_match():
    faq, method, score = matcher.match("1", FAQS)
    assert faq is not None and faq["id"] == "faq-001", "menu 1 harus match kategori jadwal"
    assert method == "menu"


def test_keyword_exact_match():
    faq, method, score = matcher.match("kapan jadwal UAS?", FAQS)
    assert faq is not None and faq["id"] == "faq-001"
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
    r3 = handler.handle_incoming_message(number, "jadwal dong", FAQS)
    assert r3 is None, "sudah handover, bot harus skip walau match FAQ"


def test_handler_explicit_admin_trigger_skips_bot():
    number = "628222000222"
    r1 = handler.handle_incoming_message(number, "admin", FAQS)
    assert r1 is None
    r2 = handler.handle_incoming_message(number, "jadwal dong", FAQS)
    assert r2 is None, "handover eksplisit belum 24 jam, bot harus tetap skip"


if __name__ == "__main__":
    test_menu_number_match()
    test_keyword_exact_match()
    test_no_match_returns_none()
    test_handler_fallback_then_handover_after_streak()
    test_handler_explicit_admin_trigger_skips_bot()
    print("OK: semua self-check lolos")
