# Panduan integrasi Fonnte — bot WhatsApp prodi (fase 1)

Lanjutan dari `arsitektur-skema-fase1-bot-wa-prodi.md`, fokus ke detail teknis Fonnte biar langsung bisa dipakai coding. Sumber: [docs.fonnte.com](https://docs.fonnte.com).

## 1. Setup akun & device

1. Daftar akun di fonnte.com, tambah device baru:
   - **Device Name**: bebas (mis. "Bot Prodi TB")
   - **Device Number**: nomor WA prodi yang udah ada
   - **Chatbot**: set **ON** — wajib buat device yang dipakai bot
2. Hubungkan device: klik **Connect** di device list → scan QR code dari WA di HP nomor prodi (WhatsApp → Perangkat Tertaut → Tautkan Perangkat), persis kayak WhatsApp Web.
3. Ambil **Token**: klik tombol **Token** di baris device, otomatis ke-copy. Simpan sebagai environment variable di backend (`.env`), jangan hardcode di kode/commit ke repo — siapa pun yang pegang token ini bisa kirim pesan pakai nomor WA prodi.
4. Set **Webhook**: klik **Edit** di baris device → isi field Webhook dengan URL backend (mis. `https://bot-prodi-tb.fly.dev/webhook`, diisi setelah deploy). Biarkan **Autoread** OFF — kalau webhook aktif, fitur auto-reply bawaan Fonnte gak akan jalan bareng, jadi gak perlu diaktifin.

## 2. Format pesan masuk (payload webhook)

Fonnte POST ke webhook URL tiap ada pesan masuk, dengan field-field berikut di body:

| Field | Isi |
|---|---|
| `device` | Nomor device (bukan nomor pengirim) |
| `sender` | Nomor WA pengirim — dipakai sebagai `target` pas balas |
| `message` | Isi pesan teks — ini yang di-matching ke FAQ |
| `name` | Nama kontak pengirim (kalau ada) |
| `text` | Isi kalau pengirim klik tombol (button reply) |
| `member` | Nomor pengirim kalau pesan dari grup |
| `location` | Lokasi (kalau share location) |
| `url` / `filename` / `extension` | Info attachment kalau pengirim kirim file/gambar |
| `timestamp` | Waktu pesan diterima |
| `inboxid` | ID pesan, buat reply-to-message via API (opsional) |

Buat fase 1, yang kepake cuma `sender` dan `message`.

Contoh endpoint FastAPI:

```python
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    sender = data.get("sender")
    message = data.get("message", "")
    # ...matching & balas di sini...
    return {"status": "ok"}
```

## 3. Format kirim balasan (API send)

```
POST https://api.fonnte.com/send
Authorization: <TOKEN>      # tanpa "Bearer", token langsung
Content-Type: application/json (atau form-data)

{
  "target": "<nomor sender dari webhook>",
  "message": "<teks balasan lengkap>"
}
```

Contoh Python (pakai `httpx`):

```python
import httpx, os

FONNTE_TOKEN = os.environ["FONNTE_TOKEN"]

def send_reply(target: str, message: str) -> dict:
    resp = httpx.post(
        "https://api.fonnte.com/send",
        headers={"Authorization": FONNTE_TOKEN},
        data={"target": target, "message": message},
        timeout=10,
    )
    return resp.json()
```

**Catatan penting soal attachment**: parameter `url`/`file` (buat kirim file beneran sebagai attachment) cuma jalan di paket super/advanced/ultra. Karena kolom `media_url` di FAQ kita isinya link SharePoint/form biasa, cukup tempelin sebagai teks di `message` — Fonnte otomatis kasih preview link. Gak perlu upgrade paket cuma buat ini.

Response sukses:
```json
{
  "detail": "success! message in queue",
  "status": true,
  "id": ["80367170"],
  "target": ["6282227097005"]
}
```

Response gagal (`status: false`) punya `reason` yang berguna buat logging — beberapa yang relevan: `token invalid`, `target invalid`, `input invalid`, `insufficient quota`.

## 4. Alur lengkap backend (fase 1)

1. Fonnte POST ke `/webhook` → dapat `sender` + `message`.
2. Cek status `handover` buat nomor itu di conversation log (lihat dokumen arsitektur bagian 5). Kalau aktif → skip, jangan balas otomatis.
3. Kalau gak ada handover aktif:
   - Cek apakah `message` itu balasan menu (angka 1-4) atau teks bebas.
   - Jalankan matching (`rapidfuzz`) ke `trigger_keywords` semua entri FAQ di Google Sheets (yang `active = TRUE`).
   - Skor match ≥ 60-70% → ambil `answer` + `media_url` (kalau ada), susun jadi satu pesan berheader `*Kang Tebi (bot prodi)*`.
   - Di bawah threshold → kirim pesan fallback + menu utama, tandai fallback di log.
4. Kirim balasan lewat `POST /send`.
5. Catat interaksi ke conversation log (match/fallback, method, dst).

## 5. Checklist sebelum deploy

- [ ] Device Fonnte dibuat, Chatbot = ON, nomor WA prodi ter-scan & connected
- [ ] Token disimpan di environment variable, bukan di kode
- [ ] Endpoint `/webhook` udah bisa terima & log payload Fonnte (test dulu pakai ngrok/tunnel lokal sebelum deploy penuh)
- [ ] Endpoint kirim balasan udah ditest kirim ke nomor sendiri dulu sebelum dipakai buat mahasiswa
- [ ] Webhook URL di dashboard Fonnte diisi setelah backend live di Vercel

## Referensi

- Sending API Messages — https://docs.fonnte.com/api-send-message/
- Webhook reply message (contoh Node.js) — https://docs.fonnte.com/webhook-reply-message-with-nodejs
- Token (API key) — https://docs.fonnte.com/token-api-key/
- Device menu (setup webhook & chatbot toggle) — https://docs.fonnte.com/device/
