"""Format balasan bot: header identitas + jawaban + footer handover (bagian 5 dokumen)."""
from app import config


def format_answer(faq: dict) -> str:
    body = faq["answer"]
    media_url = faq.get("media_url")
    if media_url:
        body = f"{body}\n{media_url}"
    return f"{config.BOT_HEADER}\n{body}\n\n{config.BOT_FOOTER}"


def format_fallback() -> str:
    body = (
        "Maaf, pertanyaanmu belum kami pahami. Coba pilih menu di bawah atau ketik ulang "
        "dengan kata kunci lain:\n\n" + config.MAIN_MENU
    )
    return f"{config.BOT_HEADER}\n{body}\n\n{config.BOT_FOOTER}"


def format_menu_topics(category_label: str, entries: list[dict]) -> str:
    """Balasan pas user pilih nomor menu: daftar topik dalam kategori itu,
    biar user bisa ketik kata kunci yang lebih spesifik."""
    if not entries:
        return format_fallback()
    topics = "\n".join(f"- {e['trigger_keywords'][0]}" for e in entries if e.get("trigger_keywords"))
    body = (
        f"Topik seputar {category_label}:\n{topics}\n\n"
        "Ketik salah satu kata kunci di atas buat lihat jawabannya."
    )
    return f"{config.BOT_HEADER}\n{body}\n\n{config.BOT_FOOTER}"
