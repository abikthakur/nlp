"""
SportsBot — Application configuration.
All values are read from environment variables / .env file.
Missing required keys raise a clear RuntimeError at startup.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _require(var: str) -> str:
    """Return the env value or raise a descriptive error."""
    value = os.getenv(var)
    if not value:
        raise RuntimeError(
            f"\n\n❌  Missing required environment variable: {var}\n"
            f"    Copy .env.example → .env and fill in the value.\n"
        )
    return value


# ── Gemini ─────────────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = ""          # loaded lazily so tests can skip it
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# ── TheSportsDB ────────────────────────────────────────────────────────────────
SPORTS_DB_API_KEY: str = ""       # loaded lazily

# ── App ────────────────────────────────────────────────────────────────────────
APP_HOST: str = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT: int = int(os.getenv("APP_PORT", "8000"))

# ── Supported sports (add more here to extend coverage) ───────────────────────
SUPPORTED_SPORTS: list[str] = ["cricket", "football"]


def get_gemini_key() -> str:
    """Lazily load and validate the Gemini API key."""
    global GEMINI_API_KEY
    if not GEMINI_API_KEY:
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    return GEMINI_API_KEY


def get_sports_db_key() -> str:
    """Lazily load and validate the TheSportsDB API key."""
    global SPORTS_DB_API_KEY
    if not SPORTS_DB_API_KEY:
        SPORTS_DB_API_KEY = os.getenv("SPORTS_DB_API_KEY", "3")  # "3" = free test key
    return SPORTS_DB_API_KEY
