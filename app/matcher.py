"""Intent matcher: menu number -> daftar topik kategori (banyak entri per kategori
sekarang), else fuzzy match ke trigger_keywords."""
from rapidfuzz import fuzz, process

from app import config


def match_menu(text: str) -> str | None:
    """Return kategori kalau teks adalah nomor menu (1-7), else None."""
    return config.MENU_CATEGORY_BY_NUMBER.get(text.strip())


def entries_by_category(category: str, faqs: list[dict]) -> list[dict]:
    return [f for f in faqs if f["category"] == category]


def match(text: str, faqs: list[dict]) -> tuple[dict | None, str, int]:
    """Match teks bebas (bukan nomor menu) ke satu entri FAQ.

    match_method: "keyword" | "fuzzy"
    score: 100 buat exact keyword, 0-100 buat fuzzy.
    """
    lowered = text.strip().lower()

    # exact keyword substring match dulu (lebih murah & pasti)
    for faq in faqs:
        for keyword in faq.get("trigger_keywords", []):
            if keyword.lower() in lowered:
                return faq, "keyword", 100

    # fuzzy fallback: bandingkan teks masuk ke semua keyword semua FAQ
    keyword_to_faq = {
        keyword: faq for faq in faqs for keyword in faq.get("trigger_keywords", [])
    }
    if not keyword_to_faq:
        return None, "fuzzy", 0

    best = process.extractOne(lowered, keyword_to_faq.keys(), scorer=fuzz.WRatio)
    if best is None:
        return None, "fuzzy", 0

    best_keyword, score, _ = best
    if score >= config.MATCH_THRESHOLD:
        return keyword_to_faq[best_keyword], "fuzzy", int(score)
    return None, "fuzzy", int(score)
