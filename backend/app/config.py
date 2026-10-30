from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str
    test_database_url: str | None = None
    groq_api_key: str = ""
    model_analysis: str = "openai/gpt-oss-120b"
    model_fast: str = "openai/gpt-oss-20b"
    model_fallback: str = "qwen/qwen3.8-27b"
    # "live" = Groq; "fixture" = offline dev fixture (no API calls, canned outputs)
    llm_mode: str = "live"
    llm_cache: bool = False
    tpm_budget: int = 7400  # per-model tokens/minute we allow ourselves (free tier = 8K)
    max_upload_mb: int = 25
    prompt_version: str = "2026-10-30.1"


settings = Settings()
