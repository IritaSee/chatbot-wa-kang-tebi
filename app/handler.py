"""Orkestrasi alur pesan masuk (bagian 2 dokumen arsitektur), dipisah dari FastAPI
biar bisa dites tanpa jalanin server."""
from app import config, logger, matcher, reply


def handle_incoming_message(wa_number: str, text: str, faqs: list[dict], name: str = "") -> str | None:
    """Return balasan yang harus dikirim, atau None kalau bot harus skip (handover aktif).
    `name` (nama kontak dari payload Fonnte) dipakai buat catatan siapa aja yang pernah chat."""
    number_hash = logger.hash_number(wa_number)

    lowered = text.strip().lower()
    if lowered in config.HANDOVER_KEYWORDS:
        logger.trigger_handover(number_hash, reason="explicit", wa_number=wa_number, name=name)
        logger.log_interaction(number_hash, text, None, "menu", "", fallback=False)
        return None  # admin yang lanjut manual, bot gak balas apa-apa

    if logger.is_handover_active(number_hash):
        return None

    category = matcher.match_menu(text)
    if category is not None:
        entries = matcher.entries_by_category(category, faqs)
        logger.register_match(number_hash, wa_number=wa_number, name=name)
        response = reply.format_menu_topics(config.CATEGORY_LABELS.get(category, category), entries)
        logger.log_interaction(number_hash, text, None, "menu", response, fallback=False)
        return response

    faq, method, score = matcher.match(text, faqs)

    if faq is not None:
        logger.register_match(number_hash, wa_number=wa_number, name=name)
        response = reply.format_answer(faq)
        logger.log_interaction(number_hash, text, faq["id"], method, response, fallback=False)
        return response

    response = reply.format_fallback()
    should_handover = logger.register_fallback(number_hash, wa_number=wa_number, name=name)
    logger.log_interaction(number_hash, text, None, method, response, fallback=True)
    if should_handover:
        logger.trigger_handover(number_hash, reason="fallback_streak", wa_number=wa_number, name=name)
    return response
