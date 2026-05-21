"""
Configuration objects for LIFE OS AI.

We expose three configurations — Development, Production and Testing — selected
through the FLASK_CONFIG environment variable. Secrets and API keys are pulled
from environment variables; sensible local defaults are provided so the project
runs out-of-the-box on a fresh clone.
"""
import os
from pathlib import Path

# Project root: /…/life_os_ai/
BASE_DIR = Path(__file__).resolve().parent


class BaseConfig:
    """Configuration shared by all environments."""

    # --- Core Flask ---------------------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY", "life-os-ai-dev-key-change-me")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 14  # two weeks

    # --- Storage ------------------------------------------------------------
    DATABASE_PATH = str(BASE_DIR / "instance" / "life_os.db")
    UPLOAD_FOLDER = str(BASE_DIR / "uploads")
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32 MB per request
    ALLOWED_UPLOAD_EXT = {"pdf", "txt", "md", "docx", "png", "jpg", "jpeg"}

    # --- AI providers -------------------------------------------------------
    # The user supplies *one* of these. If neither is present we fall back to
    # the deterministic local engine (LocalIntelligenceEngine) so the demo
    # always works without paid keys.
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    AI_MODEL_OPENAI = os.environ.get("AI_MODEL_OPENAI", "gpt-4o-mini")
    AI_MODEL_GEMINI = os.environ.get("AI_MODEL_GEMINI", "gemini-1.5-flash")

    # --- Voice --------------------------------------------------------------
    TTS_LANG = "en"


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(BaseConfig):
    TESTING = True
    DATABASE_PATH = ":memory:"
    WTF_CSRF_ENABLED = False


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config():
    """Resolve the active configuration class from the environment."""
    name = os.environ.get("FLASK_CONFIG", "development").lower()
    return CONFIG_MAP.get(name, DevelopmentConfig)
