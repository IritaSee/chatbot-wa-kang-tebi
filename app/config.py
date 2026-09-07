"""Konfigurasi dari environment variable. Semua ada default aman buat dev lokal."""
import os

from dotenv import load_dotenv

load_dotenv()

FONNTE_TOKEN = os.environ.get("FONNTE_TOKEN", "")
FONNTE_SEND_URL = os.environ.get("FONNTE_SEND_URL", "https://api.fonnte.com/send")

MATCH_THRESHOLD = int(os.environ.get("MATCH_THRESHOLD", "65"))  # 60-70 sesuai dokumen arsitektur

GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")
GOOGLE_SHEET_WORKSHEET = os.environ.get("GOOGLE_SHEET_WORKSHEET", "faq")
GOOGLE_SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "")

DB_PATH = os.environ.get("DB_PATH", "data/conversation_log.db")
FAQ_SEED_PATH = os.environ.get("FAQ_SEED_PATH", "data/faq_seed.json")

HANDOVER_KEYWORDS = {"admin", "cs", "manusia"}
HANDOVER_RESET_HOURS = 24
FALLBACK_STREAK_FOR_HANDOVER = int(os.environ.get("FALLBACK_STREAK_FOR_HANDOVER", "3"))

BOT_HEADER = "*Kang Tebi (bot prodi)*"
BOT_FOOTER = '_Butuh dibantu manusia? Balas "admin"_'

MAIN_MENU = (
    "1. Jadwal akademik\n"
    "2. Syarat pendaftaran\n"
    "3. Kontak admin prodi\n"
    "4. Pertanyaan lain"
)

MENU_CATEGORY_BY_NUMBER = {
    "1": "jadwal",
    "2": "syarat_pendaftaran",
    "3": "kontak",
    "4": "lainnya",
}
