"""FastAPI app: terima webhook Fonnte, jalankan handler, kirim balasan."""
from fastapi import FastAPI, Request

from app import faq_store, handler, wa_client

app = FastAPI(title="Kang Tebi Bot")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request):
    payload = await request.json()
    # Fonnte kirim field "sender" (nomor pengirim) & "message" (isi teks)
    sender = payload.get("sender", "")
    message = payload.get("message", "")

    print(f"[webhook] terima pesan dari Fonnte -> sender={sender!r} message={message!r} raw={payload}")

    if not sender or not message:
        print("[webhook] payload gak lengkap (sender/message kosong), skip")
        return {"status": "ignored"}

    faqs = faq_store.load_faqs()
    reply_text = handler.handle_incoming_message(sender, message, faqs)

    if reply_text:
        wa_client.send_message(sender, reply_text)

    return {"status": "ok"}
