"""Orkestrasi alur pesan masuk (bagian 2 dokumen arsitektur), dipisah dari FastAPI
biar bisa dites tanpa jalanin server."""
from app import config, logger, matcher, reply


def handle_incoming_message(wa_number: str, text: str, faqs: list[dict]) -> str | None:
    """Return balasan yang harus dikirim, atau None kalau bot harus skip (handover aktif)."""
    number_hash = logger.hash_number(wa_number)

    lowered = text.strip().lower()
    if lowered in config.HANDOVER_KEYWORDS:
        logger.trigger_handover(number_hash, reason="explicit")
        logger.log_interaction(number_hash, text, None, "menu", "", fallback=False)
        return None  # admin yang lanjut manual, bot gak balas apa-apa

    if logger.is_handover_active(number_hash):
        return None

    faq, method, score = matcher.match(text, faqs)

    if faq is not None:
        logger.register_match(number_hash)
        response = reply.format_answer(faq["answer"])
        logger.log_interaction(number_hash, text, faq["id"], method, response, fallback=False)
        return response

    response = reply.format_fallback()
    should_handover = logger.register_fallback(number_hash)
    logger.log_interaction(number_hash, text, None, method, response, fallback=True)
    if should_handover:
        logger.trigger_handover(number_hash, reason="fallback_streak")
    return response
