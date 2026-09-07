# Arsitektur & skema — bot WhatsApp prodi (fase 1: FAQ handler)

Dokumen ini jadi acuan teknis buat mulai coding fase 1: bot yang jawab pertanyaan seputar jadwal, syarat pendaftaran, dan kontak. Dirancang supaya intent router-nya bisa langsung nerima handler baru (LLM+RAG, surat generator) di fase berikutnya tanpa bongkar ulang.

## 1. Komponen backend

| Komponen | Tanggung jawab |
|---|---|
| WA gateway | Terima/kirim pesan WhatsApp (Fonnte atau Baileys) |
| Webhook receiver | Endpoint yang dipanggil gateway tiap ada pesan masuk |
| Intent matcher | Cocokkan teks masuk ke kategori FAQ (keyword/fuzzy matching) |
| FAQ store | Sumber data jawaban (jadwal, syarat, kontak) |
| Response sender | Format & kirim balasan lewat gateway |
| Logger | Catat semua interaksi + tandai yang gagal dijawab (fallback) |

## 2. Alur pesan

1. Mahasiswa kirim pesan ke nomor WA prodi.
2. Gateway terima pesan, teruskan ke webhook backend.
3. Backend cek jenis input:
   - Angka 1-4 (balasan menu) → langsung ambil FAQ kategori terkait.
   - Teks bebas → jalankan matching ke `trigger_keywords` semua entri FAQ.
4. Kalau match ditemukan di atas threshold confidence → ambil `answer`, kirim balik.
5. Kalau tidak match → kirim pesan fallback + tampilkan menu utama, catat sebagai fallback.
6. Semua interaksi (match maupun fallback) masuk ke conversation log.

Menu utama (opsional, bantu matching lebih akurat buat yang gak mau ngetik bebas):
```
1. Jadwal akademik
2. Syarat pendaftaran
3. Kontak admin prodi
4. Pertanyaan lain
```

## 3. Skema data

### FAQ entries

| Field | Tipe | Keterangan |
|---|---|---|
| id | string | ID unik entri |
| category | enum | `jadwal` \| `syarat_pendaftaran` \| `kontak` \| `lainnya` |
| trigger_keywords | array\<string\> | Kata kunci pemicu, mis. ["jadwal", "kapan daftar"] |
| question_examples | array\<string\> | Contoh pertanyaan, buat dokumentasi & testing |
| answer | text | Jawaban yang dikirim |
| media_url | string (opsional) | Kalau jawaban butuh gambar/PDF (mis. poster jadwal) |
| active | boolean | Biar bisa nonaktifin entri tanpa hapus data |
| last_updated | date | Buat tracking kapan terakhir direvisi |

### Conversation log

| Field | Tipe | Keterangan |
|---|---|---|
| id | string | ID unik log |
| wa_number_hash | string | Nomor pengirim di-hash, bukan disimpan mentah (privasi) |
| timestamp | datetime | Waktu pesan masuk |
| incoming_text | text | Isi pesan mahasiswa |
| matched_faq_id | string (nullable) | Null kalau fallback |
| match_method | enum | `menu` \| `keyword` \| `fuzzy` |
| response_sent | text | Jawaban yang dikirim |
| fallback | boolean | True kalau gak ada match |

Fallback log ini penting dijadiin bahan review berkala — dari situ kelihatan pertanyaan apa yang sering gak kejawab, jadi dasar buat nambah entri FAQ atau alasan konkret buat upgrade ke LLM+RAG di fase 2.

## 4. Stack teknis yang disarankan

- **Gateway**: Fonnte — lebih simpel karena gak perlu urus koneksi WA sendiri.
- **Bahasa/framework**: Python + FastAPI — dipilih biar orkestrasinya "beneran" dari awal, gak perlu nulis ulang pas migrasi ke fase 2 (LLM+RAG).
- **Hosting**: **Vercel** (serverless functions, Python runtime) — gratis buat skala PoC ini.
- **Matching**: `rapidfuzz` — skalanya 0-100, makin tinggi makin mirip, jadi threshold 60-70% langsung kepake tanpa perlu konversi.
- **Storage FAQ**: Google Sheets, diakses lewat Sheets API v4 (service account) — di Python bisa pakai library `gspread` biar lebih ringkas dari raw API calls.
- **Storage log**: SQLite. Filesystem Vercel read-only kecuali `/tmp`, jadi `app/logger.py` otomatis fallback ke `/tmp` kalau `DB_PATH` default gak writable. **Keputusan sadar fase 1**: `/tmp` ephemeral, reset tiap cold start/redeploy — jadi conversation log & handover state (fallback streak, status handover 24 jam) bisa ke-reset sendiri. Diterima buat PoC; kalau fase 2 butuh state beneran persisten, ganti ke DB eksternal (mis. Turso/Supabase).

## 5. Format balasan & human handover

Supaya jelas mana bot mana manusia, tiap balasan bot pakai header identitas:

```
*Kang Tebi (bot prodi)*
[jawaban]

_Butuh dibantu manusia? Balas "admin"_
```

Mekanisme handover:
- Trigger: mahasiswa ketik "admin"/"cs"/"manusia", atau bot fallback beberapa kali berturut-turut ke nomor yang sama.
- Begitu ke-trigger, tandai nomor itu `handover: true` (kolom tambahan di conversation log/sheet). Selama status ini aktif, bot skip auto-reply ke nomor itu — biar gak numpuk sama balasan admin yang mantau manual lewat nomor WA prodi yang sama.
- Reset `handover`:
  - Trigger eksplisit ("admin"/"cs"/"manusia") → reset otomatis setelah **24 jam** (matching ekspektasi umum "respons 1x24 jam"), atau direset manual lebih cepat kalau admin udah tandai selesai.
  - Trigger dari fallback berulang (bot gak diminta eksplisit, cuma gagal nebak) → gak perlu nunggu 24 jam, reset begitu ada pesan berikutnya yang berhasil match ke FAQ lain — biar bot tetap bisa bantu pertanyaan lain di hari yang sama.

## 6. Checklist sebelum mulai coding

- [x] Pilih Fonnte atau Baileys → **Fonnte**
- [x] Siapkan nomor WA khusus → nomor WA prodi yang sudah ada, gampang dipantau buat human handover
- [x] Tentukan threshold matching → **60-70%**
- [ ] Kumpulkan daftar FAQ awal dari admin prodi (jadwal, syarat, kontak) — lagi dikumpulin, disimpan di Google Sheets
- [x] Desain format balasan & fallback (header identitas + mekanisme handover) — lihat bagian 5
- [x] Finalisasi tempat hosting → **Vercel** (Python + FastAPI serverless)
- [x] Siapkan akun Vercel + deploy — SQLite log/handover pakai `DB_PATH=/tmp/...` (ephemeral, diterima buat fase 1, lihat bagian 4)
