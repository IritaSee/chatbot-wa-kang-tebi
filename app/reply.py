"""Format balasan bot: header identitas + jawaban + footer handover (bagian 5 dokumen)."""
from app import config


def format_answer(answer: str) -> str:
    return f"{config.BOT_HEADER}\n{answer}\n\n{config.BOT_FOOTER}"


def format_fallback() -> str:
    body = (
        "Maaf, pertanyaanmu belum kami pahami. Coba pilih menu di bawah atau ketik ulang "
        "dengan kata kunci lain:\n\n" + config.MAIN_MENU
    )
    return format_answer(body)
