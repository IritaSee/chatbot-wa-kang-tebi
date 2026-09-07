"""Kirim balasan WhatsApp lewat Fonnte API."""
import requests

from app import config


def send_message(target: str, message: str) -> None:
    print(f"[wa_client] kirim ke Fonnte API -> target={target!r} message={message!r}")

    if not config.FONNTE_TOKEN:
        # dev lokal tanpa token: skip kirim beneran
        print("[wa_client] FONNTE_TOKEN kosong, skip kirim (dev mode)")
        return

    response = requests.post(
        config.FONNTE_SEND_URL,
        headers={"Authorization": config.FONNTE_TOKEN},
        data={"target": target, "message": message},
        timeout=10,
    )
    print(f"[wa_client] respons Fonnte API -> status={response.status_code} body={response.text}")
