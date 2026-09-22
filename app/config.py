"""Konfigurasi dari environment variable. Semua ada default aman buat dev lokal."""
import os

from dotenv import load_dotenv

load_dotenv()

FONNTE_TOKEN = os.environ.get("FONNTE_TOKEN", "")
FONNTE_SEND_URL = os.environ.get("FONNTE_SEND_URL", "https://api.fonnte.com/send")

MATCH_THRESHOLD = int(os.environ.get("MATCH_THRESHOLD", "65"))  # 60-70 sesuai dokumen arsitektur

GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")
GOOGLE_SHEET_WORKSHEET = os.environ.get("GOOGLE_SHEET_WORKSHEET", "faq")
GOOGLE_SHEET_CONTACTS_WORKSHEET = os.environ.get("GOOGLE_SHEET_CONTACTS_WORKSHEET", "contacts")
GOOGLE_SHEET_LOG_WORKSHEET = os.environ.get("GOOGLE_SHEET_LOG_WORKSHEET", "log")
# Dev lokal: path ke file JSON service account (di-gitignore).
GOOGLE_SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "")
# Deploy (env var Vercel): isi JSON service account langsung sebagai string env var,
# dipakai kalau file gak bisa ikut ke-deploy (gitignored). Kalau diisi, ini yang menang.
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")

FAQ_SEED_PATH = os.environ.get("FAQ_SEED_PATH", "data/faq_seed.json")

HANDOVER_KEYWORDS = {"admin", "cs", "manusia"}
HANDOVER_RESET_HOURS = 24
FALLBACK_STREAK_FOR_HANDOVER = int(os.environ.get("FALLBACK_STREAK_FOR_HANDOVER", "3"))

# Tier 2 (LLM, dipilih user lewat menu "8. Lainnya"). Base URL Anthropic-compatible
# (bisa 9router atau api.anthropic.com langsung) -- ganti provider = ganti env var.
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.anthropic.com")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "claude-haiku-4-5-20251001")
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "500"))
LLM_DAILY_CAP = int(os.environ.get("LLM_DAILY_CAP", "10"))
LLM_MODE_IDLE_MINUTES = int(os.environ.get("LLM_MODE_IDLE_MINUTES", "30"))
MENU_EXIT_KEYWORDS = {"menu", "0"}
LLM_ESCALATE_MARKER = "ESCALATE"

BOT_HEADER = "*Kang Tebi (bot prodi)*"
BOT_FOOTER = (
    '_Butuh dibantu manusia? Balas "admin". '
    'Chat ini dicatat untuk keperluan layanan Prodi Teknik Biomedis._'
)
# Deskripsi identitas bot, dipakai buat entri FAQ "kamu siapa?" & (fase 2) system prompt LLM.
BOT_PERSONA = (
    "Saya Kang Tebi, asisten otomatis Prodi Teknik Biomedis Telkom University. "
    "Saya bantu jawab pertanyaan seputar Tugas Akhir, Sempro, KP, kode etik, surat, "
    "dan info akademik. Kalau butuh dibantu manusia, balas \"admin\"."
)

MENU_CATEGORY_BY_NUMBER = {
    "1": "tugas_akhir",
    "2": "sempro",
    "3": "kerja_praktik",
    "4": "kode_etik",
    "5": "surat",
    "6": "akademik",
    "7": "kontak",
}
MENU_LLM_OPTION = "8"  # "Lainnya" -> masuk tier 2 (LLM), bukan kategori FAQ

CATEGORY_LABELS = {
    "tugas_akhir": "Tugas Akhir (jadwal sidang, SOP, panduan, EC, katalog capstone)",
    "sempro": "Seminar Proposal (SOP pra & pasca sempro)",
    "kerja_praktik": "Kerja Praktik (panduan KP)",
    "kode_etik": "Kode Etik (lapor pelanggaran, prosedur & regulasi)",
    "surat": "Pengajuan Surat Prodi",
    "akademik": "Akademik (pedoman AI, literasi)",
    "kontak": "Kontak Prodi (admin, website, sosmed)",
}

MAIN_MENU = "\n".join(
    f"{number}. {CATEGORY_LABELS[category]}" for number, category in MENU_CATEGORY_BY_NUMBER.items()
) + f"\n{MENU_LLM_OPTION}. Lainnya (tanya bebas, dijawab AI)"
