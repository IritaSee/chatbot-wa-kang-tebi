"""Kirim balasan WhatsApp lewat Fonnte API."""
import requests

from app import config


def send_message(target: str, message: str) -> None:
    if not config.FONNTE_TOKEN:
        # dev lokal tanpa token: skip kirim, cuma log ke stdout
        print(f"[wa_client] (no token, skip send) -> {target}: {message}")
        return
    requests.post(
        config.FONNTE_SEND_URL,
        headers={"Authorization": config.FONNTE_TOKEN},
        data={"target": target, "message": message},
        timeout=10,
    )
