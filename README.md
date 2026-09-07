# Kang Tebi — Bot WA Prodi (Fase 1: FAQ handler)

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

## Deploy ke Vercel

`service-account.json` di-gitignore, gak ikut ke-deploy lewat repo. Set project
env vars di dashboard Vercel (Settings → Environment Variables):

- `FONNTE_TOKEN`, `GOOGLE_SHEET_ID`, `GOOGLE_SHEET_WORKSHEET`
- `GOOGLE_SERVICE_ACCOUNT_JSON` — isi JSON service account langsung sebagai
  string (satu baris, isi file JSON apa adanya)

```bash
vercel deploy --prod
```

`GOOGLE_SERVICE_ACCOUNT_JSON` (isi JSON langsung) dipakai kalau ada; kalau kosong,
fallback ke `GOOGLE_SERVICE_ACCOUNT_FILE` (path file, buat dev lokal aja).

SQLite log/handover disimpan di `DB_PATH` (default `data/conversation_log.db`);
di Vercel filesystem-nya read-only kecuali `/tmp`, jadi `app/logger.py` otomatis
fallback ke `/tmp` kalau path default gak writable. Catatan: `/tmp` ephemeral,
reset tiap cold start/redeploy — diterima buat fase 1.

## Setup Google Sheets FAQ

Kolom worksheet (header baris pertama): `id, category, trigger_keywords, question_examples, answer, media_url, active, last_updated`.
`trigger_keywords` dan `question_examples` dipisah koma dalam satu cell.
