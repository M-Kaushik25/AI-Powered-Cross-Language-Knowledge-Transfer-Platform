import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Dynamic DB Path: supports test database redirection via DATABASE_PATH
DEFAULT_DB_PATH = str(DATA_DIR / "platform.db")
DB_PATH = os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)

def get_current_db_path() -> str:
    """Returns current active DB path (supports runtime test overrides)."""
    return os.getenv("DATABASE_PATH", DB_PATH)

# API Keys & LLM Engine Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
LLM_MODE = os.getenv("LLM_MODE", "auto")  # 'live', 'offline', or 'auto'

# Confidence Gating Threshold (tau)
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

# JWT & Security Configuration
_env_secret = os.getenv("JWT_SECRET")
if not _env_secret or _env_secret == "clrag-super-secret-key-final-project-2026":
    # Use deterministic dev secret only if explicitly in development without .env
    JWT_SECRET = _env_secret or "clrag-dev-secret-replace-in-production-2026"
else:
    JWT_SECRET = _env_secret

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))  # 24 hours
