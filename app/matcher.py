"""Intent matcher: menu number -> kategori langsung, else fuzzy match ke trigger_keywords."""
from rapidfuzz import fuzz, process

from app import config


def match(text: str, faqs: list[dict]) -> tuple[dict | None, str, int]:
    """Return (faq_entry_or_None, match_method, score).

    match_method: "menu" | "keyword" | "fuzzy"
    score: 100 buat menu/exact keyword, 0-100 buat fuzzy.
    """
    stripped = text.strip()

    if stripped in config.MENU_CATEGORY_BY_NUMBER:
        category = config.MENU_CATEGORY_BY_NUMBER[stripped]
        for faq in faqs:
            if faq["category"] == category:
                return faq, "menu", 100
        return None, "menu", 0

    lowered = stripped.lower()

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
