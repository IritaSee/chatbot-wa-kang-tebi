# Kang Tebi — Bot WA Prodi (Fase 1: FAQ handler)

## Struktur

- `app/main.py` — FastAPI app, endpoint `POST /webhook` (dipanggil Fonnte).
- `app/handler.py` — orkestrasi alur pesan (menu/keyword/fuzzy match, fallback, handover).
- `app/matcher.py` — matching pakai `rapidfuzz` (threshold `MATCH_THRESHOLD`), tier 1.
- `app/llm.py` — tier 2, jawab bebas via LLM (menu "8. Lainnya"), dibatasi ke isi FAQ.
- `app/faq_store.py` — load FAQ dari Google Sheets (`gspread`), fallback ke `data/faq_seed.json`.
- `app/logger.py` — conversation log + handover state, full Google Sheets (`sheets_store.py`), wajib dikonfigurasi.
- `app/wa_client.py` — kirim balasan via Fonnte API.
- `app/reply.py` — format header/footer balasan bot.

## Jalanin lokal

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Tanpa `GOOGLE_SHEET_ID`/`GOOGLE_SERVICE_ACCOUNT_FILE`, FAQ dibaca dari `data/faq_seed.json`
(fallback ini cuma buat FAQ). Contacts/log/handover (`app/logger.py`) wajib Google Sheets —
tanpa itu, fungsi-fungsi di `logger.py` raise `RuntimeError` pas dipanggil.
Tanpa `FONNTE_TOKEN`, balasan cuma diprint ke stdout (gak beneran dikirim).

## Self-check

Butuh `GOOGLE_SHEET_ID` + kredensial terisi di `.env`. **Pakai spreadsheet
dev/test terpisah dari produksi** — test ini nulis data contact/log beneran
(worksheet `contacts`/`log` dibikin otomatis kalau belum ada, lihat bagian
Setup Google Sheets di bawah). Tanpa `GOOGLE_SHEET_ID`, test yang nyentuh
`logger.py` (handover dkk) otomatis di-skip (bukan gagal).

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

Contacts/log/handover full Google Sheets
## Setup Google Sheets FAQ

Kolom worksheet (header baris pertama): `id, category, trigger_keywords, question_examples, answer, media_url, active, last_updated`.
`trigger_keywords` dan `question_examples` dipisah koma dalam satu cell.

Worksheet `faq`, `contacts`, dan `log` (nama sesuai `GOOGLE_SHEET_WORKSHEET`/
`GOOGLE_SHEET_CONTACTS_WORKSHEET`/`GOOGLE_SHEET_LOG_WORKSHEET`) dibikin otomatis
+ header kalau belum ada di spreadsheet, jadi gak perlu bikin tab manual.

Kalau `GOOGLE_SHEET_ID` diisi tapi spreadsheet-nya sendiri gak ketemu (ID salah/
belum pernah dibikin/kehapus), backend otomatis bikin spreadsheet Google Sheets
baru (dicetak ID-nya di log) daripada webhook error tiap pesan masuk — tapi ID
barunya beda dari `GOOGLE_SHEET_ID` yang di-set, jadi update env var itu ke ID
baru tsb biar gak bikin spreadsheet baru lagi tiap cold start.

## 3 tier: fuzzy -> LLM -> human override

1. **Fuzzy (default)** — menu angka 1-7 / keyword / `rapidfuzz` (`app/matcher.py`).
   Dipakai duluan buat semua pesan; cepat & gratis.
2. **LLM (menu `8. Lainnya`)** — user pilih 8 -> mode nomor itu jadi `llm`, pesan
   berikutnya dijawab `app/llm.py` (dibatasi ke isi FAQ, gak boleh mengarang).
   Ketik `menu`/`0` buat balik ke fuzzy, atau idle `LLM_MODE_IDLE_MINUTES` ->
   otomatis balik. Dibatasi `LLM_DAILY_CAP` panggilan/nomor/hari — lewat cap atau
   LLM gagal/gak nemu jawaban (`ESCALATE`) -> otomatis diteruskan ke admin (tier 3).
3. **Human override** — kata `admin`/`cs`/`manusia`, atau auto-eskalasi dari tier 2.

Provider LLM: base URL Anthropic-compatible (`LLM_BASE_URL`), bisa proxy pihak
ketiga (mis. 9router, satu API key) atau `api.anthropic.com` langsung — ganti
provider = ganti env var, nol perubahan kode. Kosongin `LLM_API_KEY` buat matiin
tier 2 total.

Admin kontrol per nomor lewat worksheet `contacts` (kolom auto-dibikin kalau
belum ada di sheet lama):
- `bot_enabled=0` — matiin bot total (fuzzy + LLM) buat nomor itu, manual penuh.
- `llm_enabled=0` — matiin tier 2 doang, fuzzy tetap jalan.
- `mode`/`mode_since` — status sesi LLM, bisa direset manual dari sheet.
- `llm_count`/`llm_date` — counter kuota harian.

## Handover admin (AI berhenti balas -> manusia -> AI aktif lagi)

- User ketik salah satu `HANDOVER_KEYWORDS` (`admin`, `cs`, `manusia`) -> kolom
  `handover` nomor itu di worksheet `contacts` jadi `1`, bot berhenti balas,
  admin lanjut manual dari WA.
- Kalau admin sudah selesai bantu & mau nutup percakapan (mengaktifkan AI lagi
  buat nomor itu), edit langsung baris nomor tsb di worksheet `contacts`:
  kosongkan kolom `handover` (jadi `0`), `handover_since`, dan `handover_reason`.
  Pesan berikutnya dari user langsung dibalas AI lagi, tanpa nunggu timeout.
- Kalau admin tidak menutup manual, status handover dengan `handover_reason =
  explicit` otomatis reset sendiri setelah `HANDOVER_RESET_HOURS` (default 24
  jam) — reset manual ini berjalan di samping timeout otomatis itu, bukan
  gantiin.
