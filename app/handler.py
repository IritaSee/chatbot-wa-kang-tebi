"""Orkestrasi alur pesan masuk (bagian 2 dokumen arsitektur), dipisah dari FastAPI
biar bisa dites tanpa jalanin server.

3 tier: fuzzy dicoba dulu (default, menu 1-7 & rapidfuzz) -> kalau fuzzy gak
yakin (skor < MATCH_THRESHOLD), LLM otomatis jadi default (dibatasi kuota
harian), user gak perlu pilih menu "8. Lainnya" dulu -> human override (kata
admin/cs/manusia, atau auto-eskalasi kalau LLM juga gak nemu jawaban). Menu
"8"/"lainnya" tetap ada buat mode "always AI" manual (skip fuzzy tiap pesan
sampai keluar/idle timeout). Admin kontrol tier lewat worksheet contacts kolom
bot_enabled/llm_enabled."""
from app import config, llm, logger, matcher, reply


def _escalate(number_hash: str, wa_number: str, name: str) -> str:
    logger.set_mode(number_hash, "", wa_number=wa_number, name=name)
    logger.trigger_handover(number_hash, reason="llm_escalate", wa_number=wa_number, name=name)
    return reply.format_escalated()


def _answer_or_escalate_via_llm(
    number_hash: str, wa_number: str, name: str, text: str, faqs: list[dict], method: str
) -> str | None:
    """Coba jawab pakai tier 2 (LLM). Return None kalau admin matiin llm_enabled
    buat nomor ini (caller lanjut ke jalur fuzzy/fallback klasik). Kalau enabled,
    SELALU balas sesuatu -- jawaban LLM, atau (quota habis/API gagal/gak ada
    dasar di FAQ) langsung eskalasi ke admin."""
    if not logger.is_llm_enabled(number_hash):
        return None
    within_cap = logger.consume_llm_quota(number_hash, wa_number=wa_number, name=name)
    body = llm.answer(text, faqs) if within_cap else None
    if body is not None:
        logger.register_match(number_hash, wa_number=wa_number, name=name)
        response = reply.format_llm_answer(body)
        logger.log_interaction(number_hash, text, None, method, response, fallback=False)
        return response
    response = _escalate(number_hash, wa_number, name)
    logger.log_interaction(number_hash, text, None, method, response, fallback=True)
    return response


def handle_incoming_message(wa_number: str, text: str, faqs: list[dict], name: str = "") -> str | None:
    """Return balasan yang harus dikirim, atau None kalau bot harus skip (handover aktif).
    `name` (nama kontak dari payload Fonnte) dipakai buat catatan siapa aja yang pernah chat."""
    number_hash = logger.hash_number(wa_number)

    lowered = text.strip().lower()
    if lowered in config.HANDOVER_KEYWORDS:
        logger.set_mode(number_hash, "", wa_number=wa_number, name=name)
        logger.trigger_handover(number_hash, reason="explicit", wa_number=wa_number, name=name)
        logger.log_interaction(number_hash, text, None, "menu", "", fallback=False)
        return None  # admin yang lanjut manual, bot gak balas apa-apa

    if logger.is_handover_active(number_hash):
        return None

    if not logger.is_bot_enabled(number_hash):
        return None  # admin matiin bot total buat nomor ini

    if lowered in config.MENU_EXIT_KEYWORDS:
        logger.set_mode(number_hash, "", wa_number=wa_number, name=name)
        response = reply.format_fallback()
        logger.log_interaction(number_hash, text, None, "menu", response, fallback=False)
        return response

    category = matcher.match_menu(text)
    if category is not None:
        entries = matcher.entries_by_category(category, faqs)
        logger.register_match(number_hash, wa_number=wa_number, name=name)
        response = reply.format_menu_topics(config.CATEGORY_LABELS.get(category, category), entries)
        logger.log_interaction(number_hash, text, None, "menu", response, fallback=False)
        return response

    if lowered in config.MENU_LLM_KEYWORDS:
        logger.set_mode(number_hash, "llm", wa_number=wa_number, name=name)
        response = reply.format_llm_prompt()
        logger.log_interaction(number_hash, text, None, "menu", response, fallback=False)
        return response

    if logger.get_mode(number_hash) == "llm":
        response = _answer_or_escalate_via_llm(number_hash, wa_number, name, text, faqs, "llm")
        if response is not None:
            return response
        # llm_enabled dimatiin admin sambil user masih di mode llm -> keluar
        # mode diam-diam, lanjut ke fuzzy di bawah biar tetap dapat balasan.
        logger.set_mode(number_hash, "", wa_number=wa_number, name=name)

    faq, method, score = matcher.match(text, faqs)

    if faq is not None:
        logger.register_match(number_hash, wa_number=wa_number, name=name)
        response = reply.format_answer(faq)
        logger.log_interaction(number_hash, text, faq["id"], method, response, fallback=False)
        return response

    # Fuzzy gak yakin (skor < MATCH_THRESHOLD) -> LLM otomatis jadi default,
    # user gak perlu ketik "8"/"lainnya" dulu. llm_enabled=0 (admin matiin) ->
    # None -> lanjut fallback klasik + fallback_streak di bawah, biar behavior
    # sebelum fitur ini tetap sama buat nomor yang LLM-nya dimatiin.
    response = _answer_or_escalate_via_llm(number_hash, wa_number, name, text, faqs, method)
    if response is not None:
        return response

    response = reply.format_fallback()
    should_handover = logger.register_fallback(number_hash, wa_number=wa_number, name=name)
    logger.log_interaction(number_hash, text, None, method, response, fallback=True)
    if should_handover:
        logger.trigger_handover(number_hash, reason="fallback_streak", wa_number=wa_number, name=name)
    return response
