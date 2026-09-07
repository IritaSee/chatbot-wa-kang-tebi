# Kang Tebi — Bot WA Prodi (Fase 1: FAQ handler)

Implementasi sesuai `docs/arsitektur-skema-fase1-bot-wa-prodi.md`.

## Struktur

- `app/main.py` — FastAPI app, endpoint `POST /webhook` (dipanggil Fonnte).
- `app/handler.py` — orkestrasi alur pesan (menu/keyword/fuzzy match, fallback, handover).
- `app/matcher.py` — matching pakai `rapidfuzz` (threshold `MATCH_THRESHOLD`).
- `app/faq_store.py` — load FAQ dari Google Sheets (`gspread`), fallback ke `data/faq_seed.json`.
- `app/logger.py` — conversation log + handover state di SQLite.
- `app/wa_client.py` — kirim balasan via Fonnte API.
- `app/reply.py` — format header/footer balasan bot.

## Jalanin lokal

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Tanpa `GOOGLE_SHEET_ID`/`GOOGLE_SERVICE_ACCOUNT_FILE`, FAQ dibaca dari `data/faq_seed.json`.
Tanpa `FONNTE_TOKEN`, balasan cuma diprint ke stdout (gak beneran dikirim).

## Self-check

```bash
python tests/test_handler.py
```

## Deploy ke Fly.io

```bash
fly launch --no-deploy   # pakai fly.toml yang sudah ada
fly volumes create kang_tebi_data --size 1
fly secrets set FONNTE_TOKEN=xxx GOOGLE_SHEET_ID=xxx GOOGLE_SERVICE_ACCOUNT_FILE=/app/service-account.json
fly deploy
```

## Setup Google Sheets FAQ

Kolom worksheet (header baris pertama): `id, category, trigger_keywords, question_examples, answer, media_url, active, last_updated`.
`trigger_keywords` dan `question_examples` dipisah koma dalam satu cell.
