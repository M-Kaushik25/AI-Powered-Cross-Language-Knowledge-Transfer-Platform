import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = str(DATA_DIR / "platform.db")

# API Keys (optional; if not set, platform runs in deterministic local/offline simulation mode)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Confidence Gating Threshold (tau)
# Terms or segments with confidence < CONFIDENCE_THRESHOLD are routed to the Human Review Queue
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.85"))

# Supported Languages
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi (हिंदी)",
    "ta": "Tamil (தமிழ்)",
    "de": "German (Deutsch)",
    "es": "Spanish (Español)"
}

# Domains
DEFAULT_DOMAINS = [
    "cloud_computing",
    "distributed_systems",
    "biomedical_devices",
    "machine_learning"
]

# JWT Settings
JWT_SECRET = os.getenv("JWT_SECRET", "clrag-super-secret-key-final-project-2026")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
