# backend/config.py
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

env_path = Path(__file__).resolve().parent / ".env"  
load_dotenv(dotenv_path=env_path, override=True) 


class Settings(BaseSettings):
    # App configuration from environment variables

    # Basic info
    APP_NAME: str = "Menu Extractor API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # API Keys
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_DEFAULT_MODEL: str = os.getenv(
        "DEFAULT_MODEL_NAME", "google/gemini-3-flash-preview"
    )

    # Paths
    BASE_DIR: Path = Path(__file__).parent
    STORAGE_DIR: Path = BASE_DIR / "storage"
    UPLOADS_DIR: Path = STORAGE_DIR / "uploads"
    OUTPUTS_DIR: Path = STORAGE_DIR / "outputs"
    PROMPTS_DIR: Path = BASE_DIR / "core" / "prompts" / "templates"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL") or ""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set. Expected a MySQL connection string.")

    # Processing
    MAX_CONCURRENCY: int = 4
    MAX_FILE_SIZE_MB: int = 50

    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:9000",
        "http://[::1]:9000",
    ]


@lru_cache()
def get_settings() -> Settings:
    """Cache settings to avoid re-reading env file"""
    return Settings()
