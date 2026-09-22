"""Tier 2: jawab pertanyaan bebas (menu "8. Lainnya") pakai LLM, dibatasi ke
konten FAQ yang sudah ada (bukan RAG -- FAQ cuma ~20 entri, muat semua di
system prompt). Default OpenRouter (satu API key, banyak model termasuk
Claude) -- format request/response OpenAI-compatible (`/chat/completions`,
`choices[0].message.content`), dipakai juga oleh base URL OpenAI-compatible
lain kalau LLM_BASE_URL diganti.

Return None kalau LLM gak bisa/gak mau jawab (API key kosong, HTTP error,
timeout, atau model sendiri bilang ESCALATE) -- caller (handler.py) yang
mutusin fallback/eskalasi ke admin.
"""
import json

import requests

from app import config

_SYSTEM_TEMPLATE = """{persona}

Kamu jawab pertanyaan mahasiswa lewat WhatsApp. Jawab HANYA berdasarkan daftar
FAQ berikut (format JSON, field answer = jawaban resmi prodi). Ringkas,
gaya chat WA, tanpa basa-basi.

FAQ:
{faqs_json}

Kalau pertanyaan user gak ada dasarnya di FAQ di atas, jangan mengarang --
balas PERSIS satu kata: {escalate_marker}
"""


def _build_system_prompt(faqs: list[dict]) -> str:
    faqs_json = json.dumps(
        [{"category": f["category"], "answer": f["answer"]} for f in faqs],
        ensure_ascii=False,
    )
    return _SYSTEM_TEMPLATE.format(
        persona=config.BOT_PERSONA, faqs_json=faqs_json, escalate_marker=config.LLM_ESCALATE_MARKER
    )


def answer(text: str, faqs: list[dict]) -> str | None:
    """Return jawaban LLM, atau None kalau gagal/gak ada dasarnya (caller eskalasi)."""
    if not config.LLM_API_KEY:
        return None

    try:
        resp = requests.post(
            f"{config.LLM_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {config.LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.LLM_MODEL,
                "max_tokens": config.LLM_MAX_TOKENS,
                "messages": [
                    {"role": "system", "content": _build_system_prompt(faqs)},
                    {"role": "user", "content": text},
                ],
            },
            timeout=15,
        )
        resp.raise_for_status()
        body = resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:  # network/timeout/HTTP/parsing -- semua jalur gagal sama: eskalasi
        print(f"[llm] gagal manggil LLM: {e}")
        return None

    if body == config.LLM_ESCALATE_MARKER:
        return None
    return body
