"""Configuration: paths and settings, read once from the environment.

`.env` at the project root is loaded on import. Every path can be overridden
with an environment variable, so the same code runs locally and in a container.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# src/backend/mortgage_advisor/core/config.py -> project root is four levels up
PROJECT_ROOT = Path(os.getenv("MORTGAGE_PROJECT_ROOT", Path(__file__).resolve().parents[4]))
load_dotenv(PROJECT_ROOT / ".env")


def _path(env: str, default: Path) -> Path:
    value = os.getenv(env, "").strip()
    return Path(value) if value else default


# ---- paths -------------------------------------------------------------
DATA_DIR = _path("MORTGAGE_DATA_DIR", PROJECT_ROOT / "data" / "mortgage")
FRONTEND_DIR = _path("MORTGAGE_FRONTEND_DIR", PROJECT_ROOT / "src" / "frontend")
MIGRATIONS_DIR = _path("MORTGAGE_MIGRATIONS_DIR", PROJECT_ROOT / "migrations")

SEED_PATH = DATA_DIR / "mortgage.json"
RATE_SHEET_PATH = DATA_DIR / "rate_sheet.json"
SERVICING_SEED_PATH = DATA_DIR / "servicing_seed.json"
SERVICING_DB_PATH = _path("MORTGAGE_SERVICING_DB", DATA_DIR / "servicing.db")
KNOWLEDGE_DB_PATH = _path("MORTGAGE_KNOWLEDGE_DB", DATA_DIR / "passages.db")

# ---- live model ----------------------------------------------------------
LIVE_MODEL = os.getenv("LIVE_MODEL", "gemini-3.1-flash-live-preview")
VOICE = os.getenv("MORTGAGE_VOICE") or os.getenv("LIVE_VOICE", "Aoede")
GREET_ON_CONNECT = os.getenv("MORTGAGE_GREETING", "1") != "0"

APP_NAME = "mortgage-advisor"
